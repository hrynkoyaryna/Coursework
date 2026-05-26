"""
Modern light theme for File Indexer Pro
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #f5f7fa;
}

QWidget {
    color: #1a1a1a;
}

QLineEdit, QDateEdit, QComboBox {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 2px solid #e0e6ed;
    border-radius: 6px;
    padding: 8px;
    font-size: 12px;
}

QLineEdit:focus, QDateEdit:focus, QComboBox:focus {
    border: 2px solid #0d7377;
    background-color: #ffffff;
}

QPushButton {
    background-color: #0d7377;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #14919b;
}

QPushButton:pressed {
    background-color: #0a5662;
}

QPushButton:disabled {
    background-color: #e0e6ed;
    color: #999999;
}

QGroupBox {
    color: #1a1a1a;
    border: 2px solid #e0e6ed;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}

QLabel {
    color: #1a1a1a;
}

QTableWidget {
    background-color: #ffffff;
    gridline-color: #f0f0f0;
    border: 1px solid #e0e6ed;
}

QTableWidget::item {
    padding: 6px;
    border: none;
}

QTableWidget::item:selected {
    background-color: #d4f1f5;
    color: #0d7377;
}

QTableWidget::item:alternate {
    background-color: #fafbfc;
}

QHeaderView::section {
    background-color: #f5f7fa;
    color: #1a1a1a;
    padding: 8px;
    border: none;
    border-right: 1px solid #e0e6ed;
    font-weight: bold;
}

QProgressBar {
    background-color: #e8eef5;
    color: #0d7377;
    border: 2px solid #e0e6ed;
    border-radius: 6px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0d7377;
    border-radius: 4px;
}

QMenu {
    background-color: #ffffff;
    color: #1a1a1a;
    border: 1px solid #e0e6ed;
}

QMenu::item:selected {
    background-color: #e8f4f7;
    color: #0d7377;
}

QMessageBox {
    background-color: #f5f7fa;
}

QMessageBox QLabel {
    color: #1a1a1a;
}

QMessageBox QPushButton {
    min-width: 60px;
}

QFileDialog {
    background-color: #f5f7fa;
}

QScrollBar:vertical {
    background-color: #f5f7fa;
    width: 12px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}
"""

SUMMARY_CARD_STYLE = "font-size: 13px; padding: 12px 16px; background: #ffffff; border: 2px solid #e0e6ed; border-radius: 8px; color: #0d7377; font-weight: bold;"

STATUS_LABEL_STYLE = "font-weight: bold; color: #0d7377; padding: 8px; font-size: 12px;"
