import os
import sqlite3
from collections import Counter

DB_PATH = 'files_index.db'

def connect_db():
    return sqlite3.connect(DB_PATH)


def get_total_stats():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), SUM(size) FROM files WHERE COALESCE(deleted, 0) = 0")
    count, total_size = cursor.fetchone()
    conn.close()
    size_mb = (total_size / (1024 * 1024)) if total_size else 0
    return count or 0, size_mb


def get_duplicate_count():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT SUM(cnt) FROM (SELECT COUNT(*) AS cnt FROM files WHERE COALESCE(deleted, 0) = 0 AND hash != '' GROUP BY hash HAVING COUNT(*) > 1)"
    )
    result = cursor.fetchone()[0] or 0
    conn.close()
    return result


def get_trash_count():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM files WHERE COALESCE(deleted, 0) = 1")
    count = cursor.fetchone()[0] or 0
    conn.close()
    return count


def get_duplicate_groups(limit=10):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT hash, COUNT(*) AS count, SUM(size) AS total_size, MIN(path) AS sample_path "
        "FROM files WHERE COALESCE(deleted, 0) = 0 AND hash != '' GROUP BY hash HAVING count > 1 "
        "ORDER BY count DESC, total_size DESC LIMIT ?",
        (limit,)
    )
    groups = cursor.fetchall()
    conn.close()
    return groups


def get_top_extensions(limit=10):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT extension, COUNT(*) AS count, SUM(size) AS total_size "
        "FROM files WHERE COALESCE(deleted, 0) = 0 AND extension != '' GROUP BY extension "
        "ORDER BY total_size DESC LIMIT ?",
        (limit,)
    )
    extensions = cursor.fetchall()
    conn.close()
    return extensions


def get_top_directories(limit=5):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT path, size FROM files WHERE COALESCE(deleted, 0) = 0")
    rows = cursor.fetchall()
    conn.close()

    sizes = Counter()
    for path, size in rows:
        directory = os.path.dirname(path) or path
        sizes[directory] += size

    return sizes.most_common(limit)


def get_extensions():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT extension FROM files WHERE COALESCE(deleted, 0) = 0 AND extension != '' ORDER BY extension")
    extensions = [row[0] for row in cursor.fetchall()]
    conn.close()
    return extensions


def clean_all_duplicates():
    """
    Видаляє всі дублікати файлів, залишаючи один оригінальний файл.
    Повертає кількість видалених файлів та звільнену память в байтах.
    """
    conn = connect_db()
    cursor = conn.cursor()
    
    # Знаходимо групи дублікатів
    cursor.execute(
        "SELECT hash, COUNT(*) AS count, SUM(size) AS total_size "
        "FROM files WHERE COALESCE(deleted, 0) = 0 AND hash != '' GROUP BY hash HAVING count > 1"
    )
    duplicate_groups = cursor.fetchall()
    
    removed_count = 0
    freed_space = 0
    
    # Для кожної групи дублікатів
    for file_hash, count, total_size in duplicate_groups:
        # Отримуємо всі файли з цим хешем, сортуючи за датою (найстарший залишається)
        cursor.execute(
            "SELECT id, path, size FROM files WHERE hash = ? AND COALESCE(deleted, 0) = 0 ORDER BY m_time ASC",
            (file_hash,)
        )
        files = cursor.fetchall()
        
        # Перший файл - оригінал, решту видаляємо
        for file_id, file_path, size in files[1:]:
            try:
                # Видаляємо з диска, якщо існує
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Видаляємо з БД
                cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
                removed_count += 1
                freed_space += size
            except Exception:
                pass
    
    conn.commit()
    conn.close()
    
    return removed_count, freed_space
