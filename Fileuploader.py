
I need to build a Python GUI program with the following features:
- Button to upload files (supporting images, PDFs, docs, zip)
- Button to download files from an SQLite database
- Drag & drop canvas for file upload
- A widget showing all added files, with clickable symbols to add, delete, and refresh database view
- The widget must show all added files and allow manipulation accordingly

The design inspiration is "Default" style with minimal, elegant UI, light background, clear spatial separation and subtle rounded corners. I will keep typography and colors light and gentle.

For the GUI toolkit in Python, the best choice for rich modern UI and drag & drop is PyQt5 or PyQt6 or PySide6. I'll choose PyQt5 because it is widely used. It supports drag & drop, buttons, icons, and SQLite.

We will:
- Use QMainWindow with QVBoxLayout or QGridLayout
- Create buttons for upload and download
- Create a drag & drop area (custom QWidget)
- Create a QListWidget or similar to display files from the database with clickable icons for delete and refresh
- Use SQLite3 to store files in a table with id, filename, filetype, and file binary content
- Support file upload (from dialog or drag & drop) storing files in the database
- Support download of selected file from the list (writing to disk)
- Provide refresh button to reload the list from database

Implementation plan:
1. Overall window structure: top buttons, dragdrop area, file list widget on right or bottom
2. Drag & drop widget: accept defined files, on drop save file in DB and refresh list
3. File upload button: open QFileDialog, select files, save to DB, refresh list
4. File download button: select file(s) from list, prompt save location, write file content
5. File list widget: show items with filename, filetype icon, buttons for delete and refresh total list
6. SQLite integration: file table with id, filename, mimetype, binary data
7. Styling with light background, subtle rounded corners, consistent spacing

Because the user didn't require separate files, I will provide a single Python script that is self-contained and executable.

Now I will proceed with the implementation.



`file_manager_gui.py`
```py
import sys
import os
import sqlite3
import mimetypes

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QFileDialog, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QLabel, QMessageBox, QAbstractItemView, QStyle, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QMimeData, QByteArray, QSize, QBuffer, QIODevice
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap


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
        self.label = QLabel("Drag and drop files here")
        self.label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.label)
        self.setLayout(self.layout)
        self.on_files_dropped = None  # callback function

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
        self.btn_refresh.setToolTip("Refresh file list")
        self.btn_refresh.setFixedSize(32,32)
        header_layout.addWidget(QLabel("Files in Database:"))
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
        self.btn_add.setToolTip("Add files")
        self.btn_add.setFixedSize(36,36)

        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.setToolTip("Delete selected file")
        self.btn_delete.setFixedSize(36,36)

        self.btn_download = QPushButton()
        self.btn_download.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_download.setToolTip("Download selected file")
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
        self.setWindowTitle("File Manager GUI")
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
        self.btn_upload = QPushButton("Upload Files")
        self.btn_upload.setFixedHeight(48)
        self.btn_upload.setStyleSheet(self._button_style())
        self.btn_upload.setToolTip("Select files to upload")

        # Download button
        self.btn_download = QPushButton("Download Selected File")
        self.btn_download.setFixedHeight(48)
        self.btn_download.setStyleSheet(self._button_style())
        self.btn_download.setToolTip("Download selected file from database")

        # Drag and drop widget
        self.drag_drop = DragDropWidget()
        self.drag_drop.setToolTip("Drag and drop files here")
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
            "Select files to upload",
            "",
            "All Supported Files (*.png *.jpg *.jpeg *.bmp *.pdf *.doc *.docx *.zip);;Images (*.png *.jpg *.jpeg *.bmp);;PDF (*.pdf);;Documents (*.doc *.docx);;Zip archives (*.zip)",
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
            "Confirm Delete",
            "Are you sure you want to delete the selected file?",
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
            QMessageBox.information(self, "No Selection", "Please select a file to download.")
            return

        cursor = self.conn.cursor()
        cursor.execute("SELECT filename, data FROM files WHERE id = ?", (file_id,))
        result = cursor.fetchone()
        if not result:
            QMessageBox.warning(self, "Error", "Selected file not found in database.")
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


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

```
