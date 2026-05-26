import os
import sqlite3
import time
import shutil
import threading

DB_PATH = 'files_index.db'
TRASH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.file_index_trash')
TRASH_RETENTION_DAYS = 15

# Блокування для безпечного доступу до БД з кількох потоків
_db_lock = threading.RLock()


def connect_db():
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def ensure_trash_dir():
    if not os.path.exists(TRASH_DIR):
        os.makedirs(TRASH_DIR, exist_ok=True)
    return TRASH_DIR


def init_db():
    with _db_lock:
        ensure_trash_dir()
        conn = connect_db()
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
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_extension ON files(extension)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_name ON files(name)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_size ON files(size)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_m_time ON files(m_time)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(deleted)')
    conn.commit()
    conn.close()
    print("База даних готова до роботи!")


def move_file_to_trash(src_path):
    with _db_lock:
        ensure_trash_dir()
        if not src_path or not os.path.exists(src_path):
            raise FileNotFoundError(f"Файл не знайдено: {src_path}")

    base_name = os.path.basename(src_path)
    destination = os.path.join(TRASH_DIR, base_name)
    name, ext = os.path.splitext(base_name)
    counter = 1
    while os.path.exists(destination):
        destination = os.path.join(TRASH_DIR, f"{name}_{counter}{ext}")
        counter += 1

    shutil.move(src_path, destination)
    deleted_at = time.time()

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT OR REPLACE INTO files (path, name, extension, size, m_time, hash, original_path, deleted, deleted_at) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)',
        (
            destination,
            os.path.basename(destination),
            os.path.splitext(destination)[1].lower(),
            os.path.getsize(destination),
            os.path.getmtime(destination),
            None,
            src_path,
            deleted_at,
        )
    )
    conn.commit()
    conn.close()
    return destination


def cleanup_trash(days=TRASH_RETENTION_DAYS):
    with _db_lock:
        ensure_trash_dir()
        cutoff = time.time() - days * 24 * 3600
        conn = connect_db()
        cursor = conn.cursor()
    cursor.execute(
        'SELECT id, path FROM files WHERE COALESCE(deleted, 0) = 1 AND COALESCE(deleted_at, 0) <= ?',
        (cutoff,)
    )
    rows = cursor.fetchall()
    removed = 0
    for row_id, path in rows:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
        cursor.execute('DELETE FROM files WHERE id = ?', (row_id,))
        removed += 1
    conn.commit()
    conn.close()
    return removed


def get_trash_items():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT path, name, extension, size, m_time, original_path, deleted_at FROM files WHERE COALESCE(deleted, 0) = 1 ORDER BY deleted_at DESC'
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def restore_file_from_trash(trash_path):
    with _db_lock:
        if not trash_path:
            raise ValueError("Шлях до файлу не вказано")
        if not os.path.exists(trash_path):
            raise FileNotFoundError(f"Файл у кошику не знайдено: {trash_path}")

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT original_path FROM files WHERE path = ? AND COALESCE(deleted, 0) = 1',
        (trash_path,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Файл не знайдено у корзині")

    original_path = row[0] or os.path.join(os.path.dirname(os.path.dirname(trash_path)), os.path.basename(trash_path))
    restore_path = original_path
    base_name = os.path.basename(original_path)
    name, ext = os.path.splitext(base_name)
    count = 1
    while os.path.exists(restore_path):
        restore_path = os.path.join(os.path.dirname(original_path), f"{name}_{count}{ext}")
        count += 1

    os.makedirs(os.path.dirname(restore_path), exist_ok=True)
    shutil.move(trash_path, restore_path)

    # Видаляємо конфліктуючий запис, якщо він існує з тим же шляхом
    cursor.execute('DELETE FROM files WHERE path = ? AND path != ?', (restore_path, trash_path))
    
    cursor.execute(
        'UPDATE files SET path = ?, name = ?, extension = ?, size = ?, m_time = ?, original_path = NULL, deleted = 0, deleted_at = NULL WHERE path = ?',
        (
            restore_path,
            os.path.basename(restore_path),
            os.path.splitext(restore_path)[1].lower(),
            os.path.getsize(restore_path),
            os.path.getmtime(restore_path),
            trash_path,
        )
    )
    conn.commit()
    conn.close()
    return restore_path


def delete_trash_item(trash_path):
    with _db_lock:
        if not trash_path:
            raise ValueError("Шлях до файлу не вказано")
        if os.path.exists(trash_path):
            os.remove(trash_path)
    conn = connect_db()
    conn.execute('DELETE FROM files WHERE path = ?', (trash_path,))
    conn.commit()
    conn.close()


def delete_all_trash():
    with _db_lock:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT path FROM files WHERE COALESCE(deleted, 0) = 1')
    rows = cursor.fetchall()
    removed = 0
    for row in rows:
        trash_path = row[0]
        try:
            if os.path.exists(trash_path):
                os.remove(trash_path)
        except OSError:
            pass
        removed += 1
    cursor.execute('DELETE FROM files WHERE COALESCE(deleted, 0) = 1')
    conn.commit()
    conn.close()
    return removed


if __name__ == '__main__':
    init_db()
