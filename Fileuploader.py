import sys
import os
import sqlite3
import mimetypes

from PyQt5.QtWidgets import QFileIconProvider, QApplication, QMainWindow, QPushButton, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel, QMessageBox, QAbstractItemView, QStyle, QGridLayout, QFrame
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QSize, QBuffer, QIODevice
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

DB_NAME = "file_manager.db"

class DragDropWidget(QFrame):
    """
    Custom widget that accepts drag and drop of files.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(150)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed #a3a3a3;
                border-radius: 12px;
                background-color: #fafafa;
            }
            QLabel {
                color: #6b7280;
                font-size: 18px;
                font-weight: 600;
            }
        """)
        self.layout = QVBoxLayout()
        self.label = QLabel("Dateien für Drag & Drop hier ablegen")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.on_files_dropped = None
        
    def initUI(self):
        self.setGeometry(100, 100, 600, 400)
        self.setWindowTitle("Fileuploader Drag & Drop")
        self.setWindowIcon(QIcon('icon1.png'))  # Set your own icon here

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    files.append(url.toLocalFile())
            if self.on_files_dropped:
                self.on_files_dropped(files)
            event.acceptProposedAction()
        else:
            event.ignore()


class FileListWidget(QWidget):
    """
    Widget showing all files in database with icons to delete, refresh, and download.
    """
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Header with action buttons
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10,10,10,10)

        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setToolTip("Dateiliste aktualisieren")
        self.btn_refresh.setFixedSize(32,32)
        header_layout.addWidget(QLabel("Gespeicherte Dateien:"))
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        self.layout.addLayout(header_layout)

        # List widget to show files
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: none;
                font-size: 14px;
                color: #374151;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 8px;
                margin: 2px 4px;
            }
            QListWidget::item:selected {
                background-color: #e0e7ff;
            }
        """)
        self.layout.addWidget(self.list_widget)

        # Buttons below list
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton()
        self.btn_add.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_add.setToolTip("Dateien hinzufügen")
        self.btn_add.setFixedSize(36,36)

        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.setToolTip("Ausgewählte Datei löschen")
        self.btn_delete.setFixedSize(36,36)

        self.btn_download = QPushButton()
        self.btn_download.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_download.setToolTip("Ausgewählte Datei herunterladen")
        self.btn_download.setFixedSize(36,36)

        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addStretch()
        self.layout.addLayout(btn_layout)

    def add_file_item(self, file_id, filename, filetype):
        """
        Add a single file item to the list widget with icon.
        """
        item = QListWidgetItem()
        # Set icon based on filetype
        icon = self._get_icon_for_type(filetype)
        item.setIcon(icon)
        display_text = f"{filename} ({filetype})"
        item.setText(display_text)
        item.setData(Qt.UserRole, file_id)
        self.list_widget.addItem(item)

    @staticmethod
    def _get_icon_for_type(mime_type):
        # Use standard icons for known file types
        if mime_type.startswith("image/"):
            return QIcon.fromTheme("image-x-generic") or QApplication.style().standardIcon(QStyle.SP_FileIcon)
        elif "pdf" in mime_type:
            return QIcon.fromTheme("application-pdf") or QApplication.style().standardIcon(QStyle.SP_FileIcon)
        elif "zip" in mime_type or "compressed" in mime_type:
            return QIcon.fromTheme("package-x-generic") or QApplication.style().standardIcon(QStyle.SP_FileIcon)
        elif mime_type.startswith("text/") or mime_type in ["application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            return QIcon.fromTheme("x-office-document") or QApplication.style().standardIcon(QStyle.SP_FileIcon)
        else:
            return QApplication.style().standardIcon(QStyle.SP_FileIcon)

    def clear_list(self):
        self.list_widget.clear()

    def selected_file_id(self):
        item = self.list_widget.currentItem()
        if item:
            return item.data(Qt.UserRole)
        return None

    def selected_file_name(self):
        item = self.list_widget.currentItem()
        if item:
            return item.text()
        return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fileuploader")
        self.setMinimumSize(800, 600)

        # Central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout()
        self.layout.setContentsMargins(24, 24, 24, 24)
        self.layout.setSpacing(24)
        self.central_widget.setLayout(self.layout)
        self.central_widget.setStyleSheet("background-color: #ffffff;")

        # Initialize DB
        self.conn = sqlite3.connect(DB_NAME)
        self._init_db()

        # Upload button
        self.btn_upload = QPushButton("Dateien hochladen")
        self.btn_upload.setFixedHeight(48)
        self.btn_upload.setStyleSheet(self._button_style())
        self.btn_upload.setToolTip("Dateien auswählen")

        # Download button
        self.btn_download = QPushButton("Dateien herunterladen")
        self.btn_download.setFixedHeight(48)
        self.btn_download.setStyleSheet(self._button_style())
        self.btn_download.setToolTip("Dateien auswählen")

        # Drag and drop widget
        self.drag_drop = DragDropWidget()
        self.drag_drop.setToolTip("Dateien hier hinziehen")
        self.drag_drop.on_files_dropped = self.handle_files_upload

        # File list widget (with add, delete, refresh)
        self.file_widget = FileListWidget()

        # Arrange layout: Left top buttons, drag drop below, right side file list
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.btn_upload)
        left_layout.addWidget(self.btn_download)
        left_layout.addWidget(self.drag_drop)
        left_layout.addStretch()

        left_container = QWidget()
        left_container.setLayout(left_layout)

        self.layout.addWidget(left_container, 0, 0, 1, 1)
        self.layout.addWidget(self.file_widget, 0, 1, 1, 1)

        self.layout.setColumnStretch(0, 1)
        self.layout.setColumnStretch(1, 2)

        # Event connections
        self.btn_upload.clicked.connect(self.open_file_dialog)
        self.btn_download.clicked.connect(self.download_selected_file)
        self.file_widget.btn_add.clicked.connect(self.open_file_dialog)
        self.file_widget.btn_delete.clicked.connect(self.delete_selected_file)
        self.file_widget.btn_download.clicked.connect(self.download_selected_file)
        self.file_widget.btn_refresh.clicked.connect(self.load_files)

        # Load existing files initially
        self.load_files()

    def _button_style(self):
        return """
            QPushButton {
                background-color: #1f2937;
                color: white;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                padding: 12px 20px;
                transition: background-color 0.3s ease;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            QPushButton:pressed {
                background-color: #111827;
            }
        """

    def _init_db(self):
        c = self.conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            filetype TEXT NOT NULL,
            data BLOB NOT NULL
        )
        """)
        self.conn.commit()

    def open_file_dialog(self):
        options = QFileDialog.Options()
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Auswahl der Dateien",
            "",
            "Alle unterstützten Dateien (*.png *.jpg *.jpeg *.bmp *.pdf *.doc *.docx *.zip);;Images (*.png *.jpg *.jpeg *.bmp);;PDF (*.pdf);;Documents (*.doc *.docx);;Zip archives (*.zip)",
            options=options
        )
        if files:
            self.handle_files_upload(files)

    def handle_files_upload(self, files):
        # Filter allowed file types
        allowed_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.pdf', '.doc', '.docx', '.zip']
        valid_files = []
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in allowed_extensions:
                valid_files.append(f)

        if not valid_files:
            QMessageBox.warning(self, "Unsupported Files", "No supported file types found.")
            return

        cursor = self.conn.cursor()

        for file_path in valid_files:
            try:
                with open(file_path, 'rb') as file_data:
                    data = file_data.read()
                    filename = os.path.basename(file_path)
                    mimetype, _ = mimetypes.guess_type(filename)
                    if mimetype is None:
                        # fallback for common docs
                        ext = os.path.splitext(filename)[1].lower()
                        if ext in ['.doc', '.docx']:
                            mimetype = 'application/msword'
                        else:
                            mimetype = 'application/octet-stream'
                    # Insert into DB
                    cursor.execute("""
                        INSERT INTO files (filename, filetype, data) VALUES (?, ?, ?)
                    """, (filename, mimetype, data))
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to upload {file_path}.\nError:{str(e)}")
        self.conn.commit()
        self.load_files()

    def load_files(self):
        self.file_widget.clear_list()
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, filename, filetype FROM files ORDER BY id DESC")
        rows = cursor.fetchall()
        for r in rows:
            self.file_widget.add_file_item(r[0], r[1], r[2])

    def delete_selected_file(self):
        file_id = self.file_widget.selected_file_id()
        if not file_id:
            QMessageBox.information(self, "No Selection", "Please select a file to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Löschen bestätigen",
            "Wollen Sie die ausgewählte Datei wirklich löschen?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
            self.conn.commit()
            self.load_files()

    def download_selected_file(self):
        file_id = self.file_widget.selected_file_id()
        if not file_id:
            QMessageBox.information(self, "Keine Auswahl!", "Bitte eine Datei auswählen, um sie herunterzuladen.")
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT filename, data FROM files WHERE id = ?", (file_id,))
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(self, "Fehler", "Datei existiert nicht oder wurde gelöscht.")
            return

        filename, data = result
        options = QFileDialog.Options()
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File As",
            filename,
            "All Files (*)",
            options=options
        )
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(data)
                QMessageBox.information(self, "Success", f"File saved to {save_path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to save file.\nError: {str(e)}")

    def closeEvent(self, event):
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    main()

