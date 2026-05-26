import sys
import sqlite3
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QFileDialog,
    QLineEdit, QMenu, QMessageBox, QProgressBar, QDateEdit, QComboBox,
    QGroupBox, QFormLayout, QHeaderView, QDialog
)
from PyQt5.QtGui import QDesktopServices, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDate, QUrl
import database
import scanner
import stats
from .styles import DARK_STYLESHEET, SUMMARY_CARD_STYLE, STATUS_LABEL_STYLE


class ScanWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, folder):
        super().__init__()
        self.folder = folder

    def run(self):
        try:
            scanner.scan_to_db(self.folder, self.progress_callback)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def progress_callback(self, processed, total, path):
        self.progress.emit(processed, total, path)


class FileAnalyzerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Indexer Pro v2.0")
        self.resize(1380, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        self.init_controls()
        self.init_status()
        self.init_table()
        database.cleanup_trash()
        self.load_all_data()

        QApplication.instance().setStyle("Fusion")
        self.setStyleSheet(DARK_STYLESHEET)

    def init_controls(self):
        filter_box = QGroupBox("🔍 Фільтри та сортування")
        filter_box.setStyleSheet("QGroupBox { font-size: 14px; font-weight: bold; }")
        filter_layout = QFormLayout()
        filter_layout.setSpacing(10)
        filter_layout.setContentsMargins(12, 12, 12, 12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Пошук за назвою або частиною назви")
        self.search_input.textChanged.connect(self.filter_data)
        filter_layout.addRow("Назва:", self.search_input)

        self.extension_combo = QComboBox()
        self.extension_combo.addItem("Усі")
        self.extension_combo.currentIndexChanged.connect(self.filter_data)
        filter_layout.addRow("Тип (розширення):", self.extension_combo)

        size_layout = QHBoxLayout()
        self.min_size_input = QLineEdit()
        self.min_size_input.setPlaceholderText("Мін (МБ)")
        self.min_size_input.textChanged.connect(self.filter_data)
        self.max_size_input = QLineEdit()
        self.max_size_input.setPlaceholderText("Макс (МБ)")
        self.max_size_input.textChanged.connect(self.filter_data)
        size_layout.addWidget(self.min_size_input)
        size_layout.addWidget(self.max_size_input)
        filter_layout.addRow("Розмір:", size_layout)

        dates_layout = QHBoxLayout()
        self.date_from = QDateEdit(calendarPopup=True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.dateChanged.connect(self.filter_data)
        self.date_to = QDateEdit(calendarPopup=True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        self.date_to.setDate(QDate.currentDate())
        self.date_to.dateChanged.connect(self.filter_data)
        dates_layout.addWidget(self.date_from)
        dates_layout.addWidget(self.date_to)
        filter_layout.addRow("Дата зміни:", dates_layout)

        sort_layout = QHBoxLayout()
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Розмір", "Дата", "Назва", "Тип"])
        self.sort_combo.currentIndexChanged.connect(self.filter_data)
        self.direction_combo = QComboBox()
        self.direction_combo.addItems(["DESC", "ASC"])
        self.direction_combo.currentIndexChanged.connect(self.filter_data)
        sort_layout.addWidget(self.sort_combo)
        sort_layout.addWidget(self.direction_combo)
        filter_layout.addRow("Сортувати за:", sort_layout)

        self.clear_button = QPushButton("Очистити фільтри")
        self.clear_button.clicked.connect(self.clear_filters)
        filter_layout.addRow("", self.clear_button)

        filter_box.setLayout(filter_layout)
        self.main_layout.addWidget(filter_box)

        tool_layout = QHBoxLayout()
        self.scan_button = QPushButton("Сканувати папку")
        self.scan_button.clicked.connect(self.start_scanning)
        self.show_all_button = QPushButton("Показати всі файли")
        self.show_all_button.clicked.connect(self.show_all_files)
        self.show_trash_button = QPushButton("Кошик")
        self.show_trash_button.clicked.connect(self.open_trash_manager)
        self.clear_trash_button = QPushButton("Очистити корзину зараз")
        self.clear_trash_button.clicked.connect(self.clear_trash_now)
        self.dup_button = QPushButton("Показати дублікати")
        self.dup_button.clicked.connect(self.show_duplicates)
        self.clean_dup_button = QPushButton("Очистити дублікати")
        self.clean_dup_button.clicked.connect(self.manage_duplicates)
        self.dup_groups_button = QPushButton("Групи дублікатів")
        self.dup_groups_button.clicked.connect(self.show_duplicate_groups)
        self.top_button = QPushButton("Топ-10 великих")
        self.top_button.clicked.connect(self.show_top_large)
        self.stats_button = QPushButton("Аналіз диску")
        self.stats_button.clicked.connect(self.show_stats)
        tool_layout.addWidget(self.scan_button)
        tool_layout.addWidget(self.show_all_button)
        tool_layout.addWidget(self.show_trash_button)
        tool_layout.addWidget(self.clear_trash_button)
        tool_layout.addWidget(self.dup_button)
        tool_layout.addWidget(self.clean_dup_button)
        tool_layout.addWidget(self.dup_groups_button)
        tool_layout.addWidget(self.top_button)
        tool_layout.addWidget(self.stats_button)
        self.main_layout.addLayout(tool_layout)

        summary_layout = QHBoxLayout()
        self.total_label = QLabel("Файлів: 0")
        self.space_label = QLabel("Зайнято: 0.00 МБ")
        self.duplicate_label = QLabel("Дублікати: 0")
        self.top_ext_label = QLabel("Топ типів: -")
        for label in (self.total_label, self.space_label, self.duplicate_label, self.top_ext_label):
            label.setStyleSheet(SUMMARY_CARD_STYLE)
            summary_layout.addWidget(label)
        self.main_layout.addLayout(summary_layout)

    def init_status(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Статус: Готовий")
        self.status_label.setStyleSheet(STATUS_LABEL_STYLE)
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.main_layout.addWidget(self.status_label)

    def init_table(self):
        self.table = QTableWidget()
        headers = ["Назва", "Тип", "Розмір (МБ)", "Дата змін", "Шлях", "Хеш"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.open_menu)
        self.table.setRowHeight(0, 32)
        self.main_layout.addWidget(self.table)

    def start_scanning(self):
        folder = QFileDialog.getExistingDirectory(self, "Оберіть папку")
        if not folder:
            return
        self.status_label.setText(f"Сканування: {folder}...")
        self.toggle_ui(False)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.worker = ScanWorker(folder)
        self.worker.progress.connect(self.on_scan_progress)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()

    def on_scan_progress(self, processed, total, path):
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(processed)
        self.status_label.setText(f"Сканування {processed}/{total}: {os.path.basename(path)}")

    def on_scan_finished(self):
        self.toggle_ui(True)
        self.status_label.setText("Сканування завершено успішно!")
        self.update_extension_list()
        self.load_all_data()

    def on_scan_error(self, message):
        self.toggle_ui(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Помилка сканування", message)
        self.status_label.setText("Помилка сканування.")

    def toggle_ui(self, enabled):
        self.scan_button.setEnabled(enabled)
        self.dup_button.setEnabled(enabled)
        self.dup_groups_button.setEnabled(enabled)
        self.top_button.setEnabled(enabled)
        self.stats_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.extension_combo.setEnabled(enabled)
        self.min_size_input.setEnabled(enabled)
        self.max_size_input.setEnabled(enabled)
        self.date_from.setEnabled(enabled)
        self.date_to.setEnabled(enabled)
        self.sort_combo.setEnabled(enabled)
        self.direction_combo.setEnabled(enabled)
        self.progress_bar.setVisible(not enabled)

    def load_all_data(self):
        self.update_extension_list()
        self.filter_data()

    def update_extension_list(self):
        current = self.extension_combo.currentText()
        self.extension_combo.blockSignals(True)
        self.extension_combo.clear()
        self.extension_combo.addItem("Усі")
        for extension in stats.get_extensions():
            self.extension_combo.addItem(extension)
        index = self.extension_combo.findText(current)
        if index >= 0:
            self.extension_combo.setCurrentIndex(index)
        self.extension_combo.blockSignals(False)

    def clear_filters(self):
        self.search_input.clear()
        self.extension_combo.setCurrentIndex(0)
        self.min_size_input.clear()
        self.max_size_input.clear()
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        self.sort_combo.setCurrentIndex(0)
        self.direction_combo.setCurrentIndex(0)
        self.filter_data()

    def filter_data(self):
        name = self.search_input.text().strip()
        extension = self.extension_combo.currentText()
        if extension == "Усі":
            extension = ""
        min_size = self.parse_size(self.min_size_input.text())
        max_size = self.parse_size(self.max_size_input.text())
        date_from = self.date_to_timestamp(self.date_from.date(), start_of_day=True)
        date_to = self.date_to_timestamp(self.date_to.date(), start_of_day=False)
        order_by = self.sort_combo.currentText()
        order_dir = self.direction_combo.currentText()

        query = "SELECT name, extension, size, m_time, path, hash FROM files WHERE COALESCE(deleted, 0) = 0"
        filters = []
        params = []

        if name:
            filters.append("name LIKE ?")
            params.append(f"%{name}%")
        if extension:
            filters.append("extension = ?")
            params.append(extension)
        if min_size is not None:
            filters.append("size >= ?")
            params.append(min_size)
        if max_size is not None:
            filters.append("size <= ?")
            params.append(max_size)
        if date_from is not None:
            filters.append("m_time >= ?")
            params.append(date_from)
        if date_to is not None:
            filters.append("m_time <= ?")
            params.append(date_to)
        if filters:
            query += " AND " + " AND ".join(filters)

        order_columns = {
            "Назва": "name",
            "Тип": "extension",
            "Розмір": "size",
            "Дата": "m_time"
        }
        query += f" ORDER BY {order_columns.get(order_by, 'size')} {order_dir}"

        self.update_table(query, params)

    def parse_size(self, text):
        if not text:
            return None
        try:
            return int(float(text) * 1024 * 1024)
        except ValueError:
            return None

    def date_to_timestamp(self, qdate, start_of_day=True):
        if not qdate:
            return None
        dt = datetime(qdate.year(), qdate.month(), qdate.day(), 0, 0, 0)
        if not start_of_day:
            dt = datetime(qdate.year(), qdate.month(), qdate.day(), 23, 59, 59)
        return dt.timestamp()

    def show_top_large(self):
        query = "SELECT name, extension, size, m_time, path, hash FROM files WHERE COALESCE(deleted, 0) = 0 ORDER BY size DESC LIMIT 10"
        self.status_label.setText("Показано 10 найбільших файлів")
        self.update_table(query)

    def show_duplicates(self):
        query = (
            "SELECT name, extension, size, m_time, path, hash FROM files "
            "WHERE COALESCE(deleted, 0) = 0 AND hash IN (SELECT hash FROM files WHERE COALESCE(deleted, 0) = 0 GROUP BY hash HAVING COUNT(*) > 1) "
            "ORDER BY hash, size DESC"
        )
        self.status_label.setText("Показано файли, що мають дублікати")
        self.update_table(query)

    def show_duplicate_groups(self):
        query = (
            "SELECT hash, COUNT(*) AS count, SUM(size) AS total_size, MIN(path) AS sample_path "
            "FROM files WHERE COALESCE(deleted, 0) = 0 AND hash != '' GROUP BY hash HAVING count > 1 "
            "ORDER BY count DESC, total_size DESC LIMIT 100"
        )
        rows = self.execute_query(query)
        headers = ["Хеш", "Кількість", "Всього МБ", "Приклад шляху"]
        formatted = [
            [row[0], row[1], f"{row[2] / (1024 * 1024):.2f}", row[3]]
            for row in rows
        ]
        self.populate_table(headers, formatted)
        self.status_label.setText(f"Показано {len(rows)} груп дублікатів")

    def show_stats(self):
        count, size_mb = stats.get_total_stats()
        duplicates = stats.get_duplicate_count()
        trash_count = stats.get_trash_count()
        top_dirs = stats.get_top_directories(limit=5)
        top_ext = stats.get_top_extensions(limit=5)

        dirs_text = "\n".join([
            f"{i+1}. {os.path.basename(path) or path}: {round(size / (1024*1024), 2)} МБ"
            for i, (path, size) in enumerate(top_dirs)
        ])
        ext_text = "\n".join([
            f"{i+1}. {extension}: {cnt} файлів, {round(total_size / (1024*1024), 2)} МБ"
            for i, (extension, cnt, total_size) in enumerate(top_ext)
        ])
        if not dirs_text:
            dirs_text = "Немає даних для аналізу."
        if not ext_text:
            ext_text = "Немає даних по типам файлів."

        message = (
            f"Файлів в індексі: {count}\n"
            f"Зайнято: {size_mb:.2f} МБ\n"
            f"Файлів з дублікати: {duplicates}\n"
            f"Файлів у кошику: {trash_count}\n\n"
            f"Топ тек за обсягом:\n{dirs_text}\n\n"
            f"Топ типів файлів:\n{ext_text}"
        )
        QMessageBox.information(self, "Аналіз диску", message)

    def show_all_files(self):
        self.search_input.clear()
        self.extension_combo.setCurrentIndex(0)
        self.min_size_input.clear()
        self.max_size_input.clear()
        self.date_from.setDate(QDate(1970, 1, 1))
        self.date_to.setDate(QDate.currentDate())
        self.sort_combo.setCurrentIndex(0)
        self.direction_combo.setCurrentIndex(0)
        self.update_table("SELECT name, extension, size, m_time, path, hash FROM files WHERE COALESCE(deleted, 0) = 0 ORDER BY name ASC")
        self.status_label.setText("Показано усі активні файли")

    def show_trash(self):
        dialog = TrashManagerDialog(self)
        dialog.exec_()

    def clear_trash_now(self):
        removed = database.cleanup_trash(days=0)
        QMessageBox.information(self, "Очистка корзини", f"Автоматично видалено {removed} файлів із корзини.")
        self.status_label.setText(f"Очищено корзину: {removed} файлів")

    def open_trash_manager(self):
        dialog = TrashManagerDialog(self)
        dialog.exec_()

    def manage_duplicates(self):
        dialog = DuplicateCleanupDialog(self)
        dialog.exec_()

    def execute_query(self, query, params=()):
        try:
            conn = sqlite3.connect('files_index.db')
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception as e:
            self.status_label.setText(f"Помилка БД: {e}")
            return []

    def update_table(self, query, params=(), headers=None, transform=None):
        rows = self.execute_query(query, params)
        if transform:
            rows = [transform(row) for row in rows]
        elif headers is None:
            headers = ["Назва", "Тип", "Розмір (МБ)", "Дата змін", "Шлях", "Хеш"]
            rows = [
                [
                    row[0],
                    row[1],
                    f"{row[2] / (1024 * 1024):.2f}",
                    datetime.fromtimestamp(row[3]).strftime("%Y-%m-%d %H:%M:%S") if row[3] else "",
                    row[4],
                    row[5],
                ]
                for row in rows
            ]
        self.populate_table(headers or ["Назва", "Тип", "Розмір (МБ)", "Дата змін", "Шлях", "Хеш"], rows)
        self.status_label.setText(f"Показано результатів: {len(rows)}")
        self.update_summary()

    def update_summary(self):
        count, size_mb = stats.get_total_stats()
        duplicates = stats.get_duplicate_count()
        top_ext = stats.get_top_extensions(limit=3)
        top_ext_str = ", ".join([f"{row[0]} ({row[1]})" for row in top_ext]) if top_ext else "-"
        self.total_label.setText(f"Файлів: {count}")
        self.space_label.setText(f"Зайнято: {size_mb:.2f} МБ")
        self.duplicate_label.setText(f"Дублікати: {duplicates}")
        self.top_ext_label.setText(f"Топ типів: {top_ext_str}")

    def populate_table(self, headers, rows):
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                self.table.setItem(i, j, QTableWidgetItem(str(value)))

    def open_menu(self, position):
        if self.table.rowCount() == 0:
            return
        menu = QMenu()
        open_act = menu.addAction("📂 Відкрити файл")
        open_folder_act = menu.addAction("📁 Відкрити папку")
        trash_act = menu.addAction("🗑 Перемістити в корзину")
        del_act = menu.addAction("🗑 Видалити файл назавжди")
        action = menu.exec_(self.table.viewport().mapToGlobal(position))
        if action == open_act:
            self.open_selected_file()
        elif action == open_folder_act:
            self.open_selected_folder()
        elif action == trash_act:
            self.confirm_move_to_trash()
        elif action == del_act:
            self.confirm_delete()

    def find_path_column(self):
        for index in range(self.table.columnCount()):
            if self.table.horizontalHeaderItem(index) and self.table.horizontalHeaderItem(index).text() == "Шлях":
                return index
        return None

    def open_selected_file(self):
        row = self.table.currentRow()
        if row < 0:
            return
        path_col = self.find_path_column()
        if path_col is None:
            return
        path = self.table.item(row, path_col).text()
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_selected_folder(self):
        row = self.table.currentRow()
        if row < 0:
            return
        path_col = self.find_path_column()
        if path_col is None:
            return
        path = self.table.item(row, path_col).text()
        if path:
            folder = os.path.dirname(path)
            if folder:
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def confirm_move_to_trash(self):
        row = self.table.currentRow()
        if row < 0:
            return
        f_name = self.table.item(row, 0).text()
        f_path = self.table.item(row, self.table.columnCount() - 2).text()

        box = QMessageBox(self)
        box.setWindowTitle("Перемістити в корзину")
        box.setText(f"Перемістити {f_name} в корзину?")
        yes_btn = box.addButton("Так", QMessageBox.YesRole)
        box.addButton("Ні", QMessageBox.NoRole)
        box.exec_()
        
        if box.clickedButton() == yes_btn:
            self.move_file_to_trash(f_path)

    def confirm_delete(self):
        row = self.table.currentRow()
        if row < 0:
            return
        f_name = self.table.item(row, 0).text()
        f_path = self.table.item(row, self.table.columnCount() - 2).text()

        box = QMessageBox(self)
        box.setWindowTitle("Видалення")
        box.setText(f"Видалити {f_name} з диску?")
        yes_btn = box.addButton("Так", QMessageBox.YesRole)
        box.addButton("Ні", QMessageBox.NoRole)
        box.exec_()
        
        if box.clickedButton() == yes_btn:
            self.delete_path(f_path, permanent=True)
            self.table.removeRow(row)
            self.status_label.setText("Файл назавжди видалено.")

    def move_file_to_trash(self, path):
        try:
            database.move_file_to_trash(path)
            self.status_label.setText("Файл переміщено в корзину.")
            self.load_all_data()
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))

    def delete_path(self, path, permanent=False):
        try:
            if permanent:
                if os.path.exists(path):
                    os.remove(path)
                conn = sqlite3.connect('files_index.db')
                conn.execute("DELETE FROM files WHERE path=?", (path,))
                conn.commit()
                conn.close()
            else:
                database.move_file_to_trash(path)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))
            return False


class DuplicateCleanupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Очистка дублікатів")
        self.resize(1100, 520)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        headers = ["Видалити", "Назва", "Тип", "Розмір (МБ)", "Дата змін", "Шлях", "Хеш"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        remove_button = QPushButton("Видалити вибрані")
        remove_button.clicked.connect(self.on_remove_selected)
        remove_all_button = QPushButton("Видалити ВСІ дублікати")
        remove_all_button.clicked.connect(self.on_remove_all_duplicates)
        close_button = QPushButton("Закрити")
        close_button.clicked.connect(self.close)
        buttons.addWidget(remove_button)
        buttons.addWidget(remove_all_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.load_duplicate_rows()

    def load_duplicate_rows(self):
        query = (
            "SELECT name, extension, size, m_time, path, hash FROM files "
            "WHERE COALESCE(deleted, 0) = 0 AND hash IN (SELECT hash FROM files WHERE COALESCE(deleted, 0) = 0 GROUP BY hash HAVING COUNT(*) > 1) "
            "ORDER BY hash, size DESC"
        )
        conn = sqlite3.connect('files_index.db')
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.table.setItem(i, 0, checkbox_item)
            self.table.setItem(i, 1, QTableWidgetItem(str(row[0])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row[1])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{row[2] / (1024 * 1024):.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(datetime.fromtimestamp(row[3]).strftime("%Y-%m-%d %H:%M:%S") if row[3] else ""))
            self.table.setItem(i, 5, QTableWidgetItem(str(row[4])))
            self.table.setItem(i, 6, QTableWidgetItem(str(row[5])))

    def get_selected_paths(self):
        paths = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.Checked:
                paths.append(self.table.item(i, 5).text())
        return paths

    def on_remove_selected(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Очистка дублікатів", "Оберіть хоча б один файл для видалення.")
            return

        box = QMessageBox(self)
        box.setWindowTitle("Видалення дублікатів")
        box.setText(f"Видалити {len(paths)} обраних файлів?")
        box.setInformativeText("Виберіть, куди перемістити файли.")
        yes = box.addButton("Назавжди", QMessageBox.YesRole)
        no = box.addButton("В корзину", QMessageBox.NoRole)
        box.addButton("Скасувати", QMessageBox.RejectRole)
        box.exec_()

        if box.clickedButton() == yes:
            permanent = True
        elif box.clickedButton() == no:
            permanent = False
        else:
            return

        for path in paths:
            try:
                if permanent:
                    if os.path.exists(path):
                        os.remove(path)
                    conn = sqlite3.connect('files_index.db')
                    conn.execute("DELETE FROM files WHERE path=?", (path,))
                    conn.commit()
                    conn.close()
                else:
                    database.move_file_to_trash(path)
            except Exception as e:
                QMessageBox.critical(self, "Помилка", str(e))
                return

        QMessageBox.information(self, "Очистка дублікатів", "Обрані дублікати видалено.")
        self.load_duplicate_rows()

    def on_remove_all_duplicates(self):
        box = QMessageBox(self)
        box.setWindowTitle("Видалення ВСІХ дублікатів")
        box.setText("Видалити ВСІ дублікати, залишаючи тільки найстарший файл?\n\n"
                    "Всі дублікати будуть видалені НАЗАВЖДИ!")
        yes_btn = box.addButton("Так", QMessageBox.YesRole)
        box.addButton("Ні", QMessageBox.NoRole)
        box.exec_()
        
        if box.clickedButton() != yes_btn:
            return

        try:
            removed_count, freed_space = stats.clean_all_duplicates()
            freed_mb = freed_space / (1024 * 1024)
            QMessageBox.information(
                self, 
                "Успіх", 
                f"Видалено {removed_count} дублікатів.\n"
                f"Звільнено {freed_mb:.2f} МБ дискового простору."
            )
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))
            return
        
        self.load_duplicate_rows()


class TrashManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управління корзиною")
        self.resize(1200, 560)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        headers = ["Вибрати", "Назва", "Тип", "Розмір (МБ)", "Оригінальний шлях", "Шлях у кошику", "Видалено"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        restore_button = QPushButton("Відновити вибрані")
        restore_button.clicked.connect(self.on_restore_selected)
        delete_button = QPushButton("Видалити назавжди")
        delete_button.clicked.connect(self.on_delete_selected)
        delete_all_button = QPushButton("Видалити все")
        delete_all_button.clicked.connect(self.on_delete_all)
        refresh_button = QPushButton("Оновити")
        refresh_button.clicked.connect(self.load_trash_rows)
        close_button = QPushButton("Закрити")
        close_button.clicked.connect(self.close)
        buttons.addWidget(restore_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(delete_all_button)
        buttons.addWidget(refresh_button)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

        self.load_trash_rows()

    def load_trash_rows(self):
        rows = database.get_trash_items()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.table.setItem(i, 0, checkbox_item)
            self.table.setItem(i, 1, QTableWidgetItem(str(row[1])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row[2])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{row[3] / (1024 * 1024):.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(str(row[5] or "")))
            self.table.setItem(i, 5, QTableWidgetItem(str(row[0])))
            self.table.setItem(i, 6, QTableWidgetItem(datetime.fromtimestamp(row[6]).strftime("%Y-%m-%d %H:%M:%S") if row[6] else ""))

    def get_selected_paths(self):
        paths = []
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item and item.checkState() == Qt.Checked:
                paths.append(self.table.item(i, 5).text())
        return paths

    def on_restore_selected(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Управління корзиною", "Оберіть хоча б один файл для відновлення.")
            return
        for path in paths:
            try:
                database.restore_file_from_trash(path)
            except Exception as e:
                QMessageBox.critical(self, "Помилка", str(e))
                return
        QMessageBox.information(self, "Управління корзиною", "Вибрані файли відновлено.")
        self.load_trash_rows()

    def on_delete_selected(self):
        paths = self.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Управління корзиною", "Оберіть хоча б один файл для видалення.")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Видалення з корзини")
        box.setText(f"Видалити назавжди {len(paths)} файлів?")
        yes_btn = box.addButton("Так", QMessageBox.YesRole)
        box.addButton("Ні", QMessageBox.NoRole)
        box.exec_()
        
        if box.clickedButton() != yes_btn:
            return
        for path in paths:
            try:
                database.delete_trash_item(path)
            except Exception as e:
                QMessageBox.critical(self, "Помилка", str(e))
                return
        QMessageBox.information(self, "Управління корзиною", "Вибрані файли видалено назавжди.")
        self.load_trash_rows()

    def on_delete_all(self):
        box = QMessageBox(self)
        box.setWindowTitle("Видалення всієї корзини")
        box.setText("Видалити назавжди ВСІ файли із корзини? Цю операцію неможливо скасувати.")
        yes_btn = box.addButton("Так", QMessageBox.YesRole)
        box.addButton("Ні", QMessageBox.NoRole)
        box.exec_()
        
        if box.clickedButton() != yes_btn:
            return
        try:
            removed = database.delete_all_trash()
            QMessageBox.information(self, "Управління корзиною", f"Видалено {removed} файлів із корзини.")
        except Exception as e:
            QMessageBox.critical(self, "Помилка", str(e))
            return
        self.load_trash_rows()


def run_gui():
    app = QApplication(sys.argv)
    window = FileAnalyzerApp()
    window.show()
    sys.exit(app.exec_())
