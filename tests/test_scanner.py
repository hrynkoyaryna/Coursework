import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

import scanner


class TestScanner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        with sqlite3.connect('files_index.db') as conn:
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

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    def test_get_file_hash(self):
        file_path = Path(self.temp_dir.name) / 'hello.txt'
        file_path.write_text('hello world', encoding='utf-8')
        result = scanner.get_file_hash(file_path)
        self.assertEqual(result, '5eb63bbbe01eeed093cb22bb8f5acdc3')

    def test_scan_to_db_inserts_records(self):
        scan_root = Path(self.temp_dir.name) / 'scan_root'
        scan_root.mkdir()
        file_a = scan_root / 'a.txt'
        file_b = scan_root / 'b.txt'
        file_a.write_text('text a', encoding='utf-8')
        file_b.write_text('text b', encoding='utf-8')

        scanner.scan_to_db(str(scan_root))
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM files')
            count = cursor.fetchone()[0]
        self.assertEqual(count, 2)

    def test_scan_to_db_updates_hash_and_records(self):
        scan_root = Path(self.temp_dir.name) / 'scan_root'
        scan_root.mkdir()
        file_a = scan_root / 'a.txt'
        file_a.write_text('text a', encoding='utf-8')

        scanner.scan_to_db(str(scan_root))
        with sqlite3.connect('files_index.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT hash FROM files WHERE path = ?', (str(file_a),))
            row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], scanner.get_file_hash(file_a))
