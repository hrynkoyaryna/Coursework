import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

import database


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        database.init_db()

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def _insert_record(self, path, name, extension, size, m_time, hash_value):
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT OR REPLACE INTO files (path, name, extension, size, m_time, hash, original_path, deleted, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)',
                (path, name, extension, size, m_time, hash_value, None)
            )
            conn.commit()

    def _fetch_all_records(self):
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT path, name, extension, size, m_time, hash FROM files')
            return cursor.fetchall()

    def test_init_db_creates_file_and_table(self):
        self.assertTrue(os.path.exists('files_index.db'))
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='files'")
            row = cursor.fetchone()
        self.assertIsNotNone(row)

    def test_insert_and_fetch_record(self):
        path = str(Path(self.temp_dir.name) / 'file.txt')
        self._insert_record(path, 'file.txt', '.txt', 1024, 1234567890.0, 'abc123')
        rows = self._fetch_all_records()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], path)
        self.assertEqual(rows[0][5], 'abc123')

    def test_delete_file_record(self):
        path = str(Path(self.temp_dir.name) / 'file.txt')
        self._insert_record(path, 'file.txt', '.txt', 1024, 1234567890.0, 'abc123')
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM files WHERE path = ?', (path,))
            conn.commit()
        rows = self._fetch_all_records()
        self.assertEqual(len(rows), 0)

    def test_fetch_duplicate_groups(self):
        self._insert_record(str(Path(self.temp_dir.name) / 'file1.txt'), 'file1.txt', '.txt', 1024, 1234567890.0, 'samehash')
        self._insert_record(str(Path(self.temp_dir.name) / 'file2.txt'), 'file2.txt', '.txt', 2048, 1234567891.0, 'samehash')
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT hash, COUNT(*) AS count FROM files WHERE hash IS NOT NULL GROUP BY hash HAVING count > 1"
            )
            duplicates = cursor.fetchall()
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0][0], 'samehash')
        self.assertEqual(duplicates[0][1], 2)
