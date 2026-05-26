import os
import sqlite3
import hashlib
from pathlib import Path

import database

EMPTY_HASH = "d41d8cd98f00b204e9800998ecf8427e"

def get_file_hash(file_path):
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return None

def path_in_trash(file_path):
    if not file_path:
        return False
    try:
        trash_root = os.path.abspath(database.TRASH_DIR)
        file_path = os.path.abspath(file_path)
        return os.path.commonpath([trash_root, file_path]) == trash_root
    except Exception:
        return False


def scan_to_db(folder_path, progress_callback=None):
    with database._db_lock:
        conn = sqlite3.connect(database.DB_PATH, timeout=10.0)
        conn.execute("PRAGMA journal_mode=WAL")
        cursor = conn.cursor()
    cursor.execute("BEGIN")
    cursor.execute("CREATE TEMP TABLE IF NOT EXISTS scan_paths (path TEXT PRIMARY KEY)")
    cursor.execute("DELETE FROM scan_paths")

    total_files = 0
    for _, _, files in os.walk(folder_path):
        total_files += len(files)

    processed = 0
    for root, dirs, files in os.walk(folder_path):
        for name in files:
            full_path = os.path.join(root, name)
            if path_in_trash(full_path):
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_files, full_path)
                continue
            try:
                stats = os.stat(full_path)
                size = stats.st_size
                file_hash = get_file_hash(full_path) if size > 0 else EMPTY_HASH
                cursor.execute(
                    "INSERT OR REPLACE INTO files (path, name, extension, size, m_time, hash, original_path, deleted, deleted_at) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, NULL)",
                    (full_path, name, Path(name).suffix.lower(), size, stats.st_mtime, file_hash)
                )
                cursor.execute(
                    "INSERT OR REPLACE INTO scan_paths (path) VALUES (?)",
                    (full_path,)
                )
            except Exception:
                pass
            finally:
                processed += 1
                if progress_callback:
                    progress_callback(processed, total_files, full_path)

    cursor.execute(
        "DELETE FROM files WHERE COALESCE(deleted, 0) = 0 AND path NOT IN (SELECT path FROM scan_paths)"
    )
    cursor.execute("DROP TABLE IF EXISTS scan_paths")
    conn.commit()
    conn.close()
