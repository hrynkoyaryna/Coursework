import os
import sqlite3
import tempfile
import unittest

import stats


def _create_table(db_path):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE,
                name TEXT,
                extension TEXT,
                size INTEGER,
                m_time REAL,
                hash TEXT,
                original_path TEXT,
                deleted INTEGER DEFAULT 0,
                deleted_at REAL
            )
        ''')
        conn.commit()


def _insert_record(db_path, path, name, extension, size, m_time, hash_value):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO files (path, name, extension, size, m_time, hash, original_path, deleted, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)',
            (path, name, extension, size, m_time, hash_value, None)
        )
        conn.commit()


class TestStats(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        _create_table('files_index.db')
        _insert_record('files_index.db', 'file1.txt', 'file1.txt', '.txt', 100, 1234567890.0, 'h1')
        _insert_record('files_index.db', 'file2.txt', 'file2.txt', '.log', 200, 1234567891.0, 'h2')
        _insert_record('files_index.db', 'file3.txt', 'file3.txt', '.txt', 300, 1234567892.0, 'h1')

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def test_get_total_stats(self):
        total_files, total_size = stats.get_total_stats()
        self.assertEqual(total_files, 3)
        self.assertGreater(total_size, 0)

    def test_get_top_extensions(self):
        top_extensions = stats.get_top_extensions()
        self.assertEqual(top_extensions[0][0], '.txt')
        self.assertEqual(top_extensions[0][1], 2)

    def test_get_duplicate_groups(self):
        duplicate_groups = stats.get_duplicate_groups()
        self.assertEqual(len(duplicate_groups), 1)
        self.assertEqual(duplicate_groups[0][0], 'h1')
        self.assertEqual(duplicate_groups[0][1], 2)
