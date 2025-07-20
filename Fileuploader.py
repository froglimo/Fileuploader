import os
import sys

import sqlite3
import mimetypes
import shutil
import requests
from threading import Thread
# --------------------------------------------------------------------------- #
# Minimal Flask application (WSGI) used by the internal background server
# as well as external WSGI servers (see wsgi.py).  By defining the `app`
# object here, we no longer rely on a separate server.py file.
# --------------------------------------------------------------------------- #
from flask import Flask, request, jsonify, send_from_directory, abort
from werkzeug.utils import secure_filename
import io
import zipfile
from typing import List

app = Flask(__name__)

# Where to store uploaded files (will recreate folder structure)
UPLOAD_FOLDER_HTTP = os.path.join(os.path.dirname(__file__), "uploaded_folders")
os.makedirs(UPLOAD_FOLDER_HTTP, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER_HTTP


def sanitize_relative_path(rel_path: str) -> str:
    """
    Preserve sub-directories while sanitising each component
    to eliminate '..', empty parts, or dangerous characters.
    """
    rel_path = os.path.normpath(rel_path)
    parts: List[str] = []
    for part in rel_path.split(os.sep):
        if part in ("", ".", ".."):
            continue
        parts.append(secure_filename(part))
    return os.path.join(*parts) if parts else ""


def safe_join(base_dir: str, *paths: str) -> str:
    """
    Ensures the final absolute path is still inside base_dir.
    """
    final_path = os.path.abspath(os.path.join(base_dir, *paths))
    if not final_path.startswith(os.path.abspath(base_dir)):
        raise ValueError("Attempted path traversal attack")
    return final_path


@app.route("/upload", methods=["POST"])
def handle_single_file_upload():
    """
    Simple endpoint used by the Qt desktop client to upload a single file.
    """
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify(success=False, message="No file received"), 400

    filename = secure_filename(file.filename)
    dest_path = safe_join(app.config["UPLOAD_FOLDER"], filename)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    file.save(dest_path)

    return jsonify(success=True, file_saved=filename, upload_folder=app.config["UPLOAD_FOLDER"])

# Additional routes (optional) ------------------------------------------------
# You can add more endpoints here (e.g. /download) if needed by other clients.
# --------------------------------------------------------------------------- #
# Removed redundant import that shadowed later Qt enum import
from PyQt5.QtWidgets import QMenuBar, QApplication

# import flask  # still available if you want to spin up the server in‐process
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QLabel, QMessageBox, QAbstractItemView, QCheckBox, QSpinBox, QStyle,
    QAction
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap, QWindow
from PyQt5.QtWidgets import QStyle

import threading

def run_server():
    """
    Start the internal Flask server defined in this module.
    Running in a dedicated thread keeps the GUI responsive.
    """
    app.run(port=5001, use_reloader=False)  # use_reloader=False is important for threads

# Start the server in a background thread
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

DB_NAME = "file_manager.db"
UPLOAD_ENDPOINT = "http://localhost:5001/upload"

class _CallableEvent(QEvent):
    def __init__(self, fn):
        super().__init__(QEvent.Type.User)
        self.fn = fn
    def execute(self):
        self.fn()

    # Change to your server URL
class AutorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Autor")
        self.setMinimumSize(400, 350)
        layout = QVBoxLayout(self)
        # Add online landscape image
        image_url = "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=400&q=80"
        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        try:
            from PyQt5.QtGui import QPixmap
            response = requests.get(image_url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaledToWidth(320, Qt.TransformationMode.SmoothTransformation)
                image_label.setPixmap(pixmap)
            else:
                image_label.setText("[Bild konnte nicht geladen werden]")
        except Exception:
            image_label.setText("[Bild konnte nicht geladen werden]")
        layout.addWidget(image_label)
        label = QLabel(
            "<h2>Max Krebs</h2>"
            "<p><b>E-Mail:</b> melvis@posteo.de</p>"
            "<p>© Release 25.06.2024</p>"
            "<p>Mit Liebe gecodet durch Max Krebs</p>"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)

# --------------------------------------------------------------------------- #
# Drag-and-drop Bereich
# --------------------------------------------------------------------------- #
class DragDropWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(150)
        self.on_files_dropped = None
        self.setStyleSheet(
            """
            QFrame {
                border: 2px solid #a3a3a3;
                border-radius: 12px;
                background-color: #fafafa;
                padding:10px;
            }
            QLabel {
                color: #6b7280;
                font-size: 18px;
                font-weight: 600;
            }
        """
        )
        self._layout = QVBoxLayout(self)
        label = QLabel("Dateien für Drag & Drop hier ablegen")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(label)

    def dragEnterEvent(self, a0: QDragEnterEvent):
        md = a0.mimeData()
        if md is not None and md.hasUrls():
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dragMoveEvent(self, a0: QDragEnterEvent):
        md = a0.mimeData()
        if md is not None and md.hasUrls():
            a0.acceptProposedAction()
        else:
            a0.ignore()

    def dropEvent(self, a0: QDropEvent):
        md = a0.mimeData()
        if md is not None and md.hasUrls():
            local_files = [
                url.toLocalFile() for url in md.urls() if url.isLocalFile()
            ]
            if callable(self.on_files_dropped):
                self.on_files_dropped(local_files)
            a0.acceptProposedAction()
        else:
            a0.ignore()
# --------------------------------------------------------------------------- #
# Datei Liste Widget
# --------------------------------------------------------------------------- #
class FileListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)

        # Styled frame for settings content
        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setFrameShadow(QFrame.Raised)
        frame.setAutoFillBackground(True)
        frame_pal = frame.palette()
        frame_pal.setColor(QPalette.Window, QColor(255, 255, 255))
        frame.setPalette(frame_pal)

        # Layout inside the frame
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(20)
        main_layout.setContentsMargins(0, 0, 0, 0)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)
        self.btn_refresh = QPushButton()
        style = QApplication.style() if hasattr(QApplication, 'style') else None
        if style:
            self.btn_refresh.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.btn_refresh.setToolTip("Dateiliste aktualisieren")
        header_layout.addWidget(QLabel("Gespeicherte Dateien:"))
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(header_layout)
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_widget.setStyleSheet(
            """
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
        """
        )
        main_layout.addWidget(self.list_widget)
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton()
        if style:
            self.btn_add.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.btn_add.setToolTip("Dateien hinzufügen")
        self.btn_delete = QPushButton()
        if style:
            self.btn_delete.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.btn_delete.setToolTip("Ausgewählte Datei löschen")
        self.btn_download = QPushButton()
        if style:
            self.btn_download.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.btn_download.setToolTip("Ausgewählte Datei herunterladen")
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_download)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def clear_list(self):
        self.list_widget.clear()

    def add_file_item(self, file_id: int, filename: str, filetype: str):
        item = QListWidgetItem()
        item.setText(f"{filename} ({filetype})")
        item.setData(Qt.ItemDataRole.UserRole, file_id)
        self.list_widget.addItem(item)

    def selected_file_id(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    @staticmethod
    def _icon_for_type(mime: str) -> QIcon:
        style = QApplication.style() if hasattr(QApplication, 'style') else None
        if mime.startswith("image/"):
            return QIcon.fromTheme("image-x-generic") or (style.standardIcon(QStyle.StandardPixmap.SP_FileIcon) if style else QIcon())
        if "pdf" in mime:
            return QIcon.fromTheme("application-pdf") or (style.standardIcon(QStyle.StandardPixmap.SP_FileIcon) if style else QIcon())
        if "zip" in mime or "compressed" in mime:
            return QIcon.fromTheme("package-x-generic") or (style.standardIcon(QStyle.StandardPixmap.SP_FileIcon) if style else QIcon())
        if mime.startswith("text/") or mime in (
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            return QIcon.fromTheme("x-office-document") or (style.standardIcon(QStyle.StandardPixmap.SP_FileIcon) if style else QIcon())
        return style.standardIcon(QStyle.StandardPixmap.SP_FileIcon) if style else QIcon()
class ButtonUploadtoServer(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText("Upload to Server")
        self.setFixedHeight(48)
        self.setStyleSheet(
            """
            QPushButton {
                background-color: #1f2937;
                color: white;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                padding: 12px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
            QPushButton:pressed { background-color: #111827; }
        """
        )
# --------------------------------------------------------------------------- #
# Main window
# --------------------------------------------------------------------------- #
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fileuploader")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon1.png")))
        self.setMinimumSize(800, 600)
        # Current database path
        # Drag-and-drop handler set up in UI initialization
        self.current_db_path = DB_NAME
        self.settings_window = None
        self.server_timeout = 30

        # Menu bar
        self._create_menu()

        # DB connection
        self.conn = sqlite3.connect(self.current_db_path)
        self._init_db()

        # Main layout
        self._setup_ui()

        # Init list
        self.load_files()
    def show_settings_window(self) -> None:
        if not hasattr(self, 'settings_window') or self.settings_window is None or not self.settings_window.isVisible():
            # Create a *new* window (with this MainWindow as logical parent)
            self.settings_window = SettingsWindow(self)
            self.settings_window.show()
    
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def upload_to_server(self, files):
        """
        POST each file to a remote HTTP endpoint.
        Runs in a background thread to avoid blocking UI.
        """
        successes = 0
        for path in files:
            if not os.path.isfile(path):
                continue
            mime, _ = mimetypes.guess_type(path)
            mime = mime or "application/octet-stream"
            with open(path, "rb") as fh:
                files_payload = {
                    "file": (os.path.basename(path), fh, mime)
                }
                try:
                    resp = requests.post(UPLOAD_ENDPOINT, files=files_payload)
                    resp.raise_for_status()
                    successes += 1
                except requests.RequestException as exc:
                    # report per-file failures on the GUI thread
                    self.run_on_ui_thread(
                        lambda: QMessageBox.warning(
                            self, "Upload Failed",
                            f"Failed to upload '{path}' to server:\n{exc}"
                        )
                    )
        if successes:
            self.run_on_ui_thread(
                lambda: QMessageBox.information(
                    self, "Upload Complete",
                    f"Successfully uploaded {successes} file(s) to server."
                )
            )

    def run_on_ui_thread(self, fn):
        """
        Helper to marshal a callback back to the Qt event loop.
        """
        QApplication.instance().postEvent(self, _CallableEvent(fn))
    # -------------------------- UI construction ---------------------------- #
    def _setup_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)

        grid = QGridLayout(self.central_widget)
        grid.setContentsMargins(24, 24, 24, 24)
        grid.setSpacing(24)

        # Left column ------------------------------------------------------- #
        left_vbox = QVBoxLayout()
        self.btn_upload = QPushButton("Dateien hochladen")
        self.btn_upload.setFixedHeight(48)
        self.btn_upload.setStyleSheet(self._button_style())
        self.btn_upload.setToolTip("Dateien auswählen")

        self.btn_download_all = QPushButton("Dateien herunterladen")
        self.btn_download_all.setFixedHeight(48)
        self.btn_download_all.setStyleSheet(self._button_style())
        self.btn_download_all.setToolTip("Dateien auswählen")

        self.drag_drop = DragDropWidget()
        def on_files_dropped(files):
            self.handle_files_upload(files)
            Thread(target=self.upload_to_server, args=(files,), daemon=True).start()
        self.drag_drop.on_files_dropped = on_files_dropped
        left_vbox.addWidget(self.btn_upload)
        left_vbox.addWidget(self.btn_download_all)
        left_vbox.addWidget(self.drag_drop)
        left_vbox.addStretch()

        left_container = QWidget()
        left_container.setLayout(left_vbox)

        # Right column ------------------------------------------------------ #
        self.file_widget = FileListWidget()

        # Place widgets in grid
        grid.addWidget(left_container, 0, 0)
        grid.addWidget(self.file_widget, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)

        # Signal connections
        self.btn_upload.clicked.connect(self.open_file_dialog)
        self.btn_download_all.clicked.connect(self.download_selected_file)

        # Re-use buttons from FileListWidget
        self.file_widget.btn_add.clicked.connect(self.open_file_dialog)
        self.file_widget.btn_delete.clicked.connect(self.delete_selected_file)
        self.file_widget.btn_download.clicked.connect(self.download_selected_file)
        self.file_widget.btn_refresh.clicked.connect(self.load_files)

    # -------------------------- Menu bar ----------------------------------- #
    def _create_menu(self):
        menubar = self.menuBar()
        if menubar is None:
            menubar = QMenuBar(self)
            self.setMenuBar(menubar)

        # Datei
        file_menu = menubar.addMenu("&Datei")
        act_open = QAction("Öffnen…", self)
        act_open.setShortcut("Ctrl+O")
        file_menu.addAction(act_open)
        file_menu.addSeparator()
        act_db_location = QAction("Datenbank Speicherort ändern", self)
        act_db_location.triggered.connect(self.change_database_location)
        file_menu.addAction(act_db_location)
        act_db_export = QAction("Datenbank exportieren", self)
        act_db_export.triggered.connect(self.database_download)
        file_menu.addAction(act_db_export)
        act_db_import = QAction("Datenbank importieren", self)
        act_db_import.triggered.connect(self.database_upload)
        file_menu.addAction(act_db_import)
        file_menu.addSeparator()
        act_exit = QAction("Beenden", self)
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Bearbeiten
        edit_menu = menubar.addMenu("&Bearbeiten")
        act_undo = QAction("Rückgängig", self)
        act_undo.setShortcut("Ctrl+Z")
        edit_menu.addAction(act_undo)
        act_redo = QAction("Wiederholen", self)
        act_redo.setShortcut("Ctrl+Y")
        edit_menu.addAction(act_redo)
        act_edit_menu = QAction("Einstellungen", self)
        act_edit_menu.setShortcut("Ctrl+I")
        act_edit_menu.triggered.connect(self.show_settings_window)
        edit_menu.addAction(act_edit_menu)

        # Hilfe
        help_menu = menubar.addMenu("&Hilfe")
        act_about = QAction("Über", self)
        act_autor = QAction("Autor", self)
        act_autor.triggered.connect(self.show_autor)
        act_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(act_about)
        help_menu.addAction(act_autor)
   
    def show_autor(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Autor")
        image_url = "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=200&q=60"
        try:
            from PyQt5.QtGui import QPixmap
            response = requests.get(image_url)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                pixmap = pixmap.scaledToWidth(100, Qt.TransformationMode.SmoothTransformation)
                msg.setIconPixmap(pixmap)
        except Exception:
            pass
        msg.setText(
            "<b>Max Krebs</b><br>"
            "E-Mail: max.krebs@example.com<br>"
            "© Release 25.06.2024<br>"
            "Mit Liebe gecodet durch Max Krebs"
        )
        msg.exec_()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "Über Fileuploader",
            "Fileuploader v1.0\n\nEin einfacher Drag-&-Drop Datei-Uploader\n© Release 25.06.2024 \n\nMit Liebe gecodet durch Max Krebs\n",
        )
    # -------------------------- Styling helper ---------------------------- #
    @staticmethod
    def _button_style() -> str:
        return """
            QPushButton {
                background-color: #1f2937;
                color: white;
                border-radius: 12px;
                font-weight: 600;
                font-size: 16px;
                padding: 12px 20px;
            }
            QPushButton:hover { background-color: #4b5563; }
            QPushButton:pressed { background-color: #111827; }
        """

    # -------------------------- DB helpers -------------------------------- #
    def _init_db(self):
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS files(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filetype TEXT NOT NULL,
                data BLOB NOT NULL
            )
        """
        )
        self.conn.commit()

    # -------------------------- File operations --------------------------- #
    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Auswahl der Dateien",           # caption
            "",                              # start directory
            "Alle unterstützten Dateien (*.webp *.avif *.png *.heic *.jpg *.jpeg *.bmp *.pdf *.doc *.docx *.odt *.odp *.txt *.zip *.7z);;"
            "Bilder (*.webp *.avif *.png *.heic *.jpg *.jpeg *.bmp);;"
            "PDF (*.pdf);;"
            "Dokumente (*.doc *.docx *.odt *.odp *.txt);;"
            "Zip Archive (*.zip *.7z)"       # filter string
        )
        if files:
            self.handle_files_upload(files)
    
    def handle_files_upload(self, files):
        allowed = {".doc", ".docx", ".odt", ".odp", ".txt", ".pdf", ".zip", ".7z", ".png", ".jpg", ".jpeg", ".bmp", ".heic", ".webp", ".avif"}
        valid = [f for f in files if os.path.splitext(f)[1].lower() in allowed]

        if not valid:
            QMessageBox.warning(
                self, "Unsupported Files", "No supported file types selected."
            )
            return

        cur = self.conn.cursor()
        for path in valid:
            try:
                with open(path, "rb") as fh:
                    data = fh.read()
                filename = os.path.basename(path)
                mime, _ = mimetypes.guess_type(filename)
                if mime is None:
                    ext = os.path.splitext(filename)[1].lower()
                    mime = "application/msword" if ext in {".doc", ".docx"} else "application/octet-stream"

                cur.execute(
                    "INSERT INTO files(filename, filetype, data) VALUES(?,?,?)",
                    (filename, mime, data),
                )
            except Exception as exc:
                QMessageBox.warning(self, "Error", f"Failed to upload '{path}'.\n{exc}")

        self.conn.commit()
        self.load_files()

    def load_files(self):
        self.file_widget.clear_list()
        cur = self.conn.cursor()
        for file_id, fname, ftype in cur.execute(
            "SELECT id, filename, filetype FROM files ORDER BY id DESC"
        ):
            self.file_widget.add_file_item(file_id, fname, ftype)

    def delete_selected_file(self):
        file_id = self.file_widget.selected_file_id()
        if not file_id:
            QMessageBox.information(self, "Keine Auswahl", "Bitte Datei auswählen.")
            return
        if (
            QMessageBox.question(
                self,
                "Löschen bestätigen",
                "Wollen Sie die ausgewählte Datei wirklich löschen?",
                QMessageBox.Yes | QMessageBox.No,
            )
            == QMessageBox.Yes
        ):
            cur = self.conn.cursor()
            cur.execute("DELETE FROM files WHERE id=?", (file_id,))
            self.conn.commit()
            self.load_files()

    def download_selected_file(self):
        file_id = self.file_widget.selected_file_id()
        if not file_id:
            QMessageBox.information(self, "Keine Auswahl", "Bitte Datei auswählen.")
            return

        cur = self.conn.cursor()
        cur.execute("SELECT filename, data FROM files WHERE id=?", (file_id,))
        row = cur.fetchone()
        if not row:
            QMessageBox.warning(self, "Fehler", "Datei existiert nicht.")
            return

        filename, blob = row
        save_path, _ = QFileDialog.getSaveFileName(
            self, "Speichern unter …", filename, "All Files (*)"
        )
        if save_path:
            try:
                with open(save_path, "wb") as fh:
                    fh.write(blob)
                QMessageBox.information(self, "Erfolg", f"Datei gespeichert: {save_path}")
            except Exception as exc:
                QMessageBox.warning(self, "Error", f"Speichern fehlgeschlagen.\n{exc}")

    # -------------------------- Database operations ----------------------- #
    def change_database_location(self):
        """Change the location of the database file"""
        new_path, _ = QFileDialog.getSaveFileName(
            self,
            "Neuen Datenbank-Speicherort wählen",
            self.current_db_path,
            "SQLite Database (*.db);;All Files (*)"
        )
        
        if not new_path:
            return
            
        try:
            # Close current connection
            self.conn.close()
            
            # Copy current database to new location if it exists
            if os.path.exists(self.current_db_path):
                shutil.copy2(self.current_db_path, new_path)
            
            # Update current path and reconnect
            self.current_db_path = new_path
            self.conn = sqlite3.connect(self.current_db_path)
            self._init_db()
            
            # Refresh the file list
            self.load_files()
            
            QMessageBox.information(
                self,
                "Erfolg",
                f"Datenbank-Speicherort geändert zu:\n{new_path}"
            )
            
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Fehler beim Ändern des Datenbank-Speicherorts:\n{exc}"
            )
            # Reconnect to original database
            self.conn = sqlite3.connect(self.current_db_path)

    def database_download(self):
        """Export/download the current database to a chosen location"""
        if not os.path.exists(self.current_db_path):
            QMessageBox.warning(
                self,
                "Fehler",
                "Keine Datenbank zum Exportieren gefunden."
            )
            return
            
        export_path, _ = QFileDialog.getSaveFileName(
            self,
            "Datenbank exportieren",
            f"file_manager_backup_{os.path.basename(self.current_db_path)}",
            "SQLite Database (*.db);;All Files (*)"
        )
        
        if not export_path:
            return
            
        try:
            self.conn.commit()
            
            # Copy the database file
            shutil.copy2(self.current_db_path, export_path)
            
            QMessageBox.information(
                self,
                "Erfolg",
                f"Datenbank erfolgreich exportiert nach:\n{export_path}"
            )
            
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Fehler beim Exportieren der Datenbank:\n{exc}"
            )

    def database_upload(self):
        """Import/upload a database from a chosen location"""
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Datenbank importieren",
            "",
            "SQLite Database (*.db);;All Files (*)"
        )
        
        if not import_path:
            return
            
        # Confirm the import operation
        reply = QMessageBox.question(
            self,
            "Import bestätigen",
            "Das Importieren einer Datenbank wird die aktuelle Datenbank ersetzen.\n"
            "Möchten Sie fortfahren?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        try:
            # Validate that the file is a valid SQLite database
            test_conn = sqlite3.connect(import_path)
            test_cursor = test_conn.cursor()
            
            # Check if it has the expected table structure
            test_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='files'"
            )
            if not test_cursor.fetchone():
                test_conn.close()
                QMessageBox.warning(
                    self,
                    "Ungültige Datenbank",
                    "Die ausgewählte Datei scheint keine gültige Fileuploader-Datenbank zu sein."
                )
                return
                
            test_conn.close()
            
            # Close current connection
            self.conn.close()
            
            # Replace current database with imported one
            shutil.copy2(import_path, self.current_db_path)
            
            # Reconnect to the new database
            self.conn = sqlite3.connect(self.current_db_path)
            self._init_db()
            
            # Refresh the file list
            self.load_files()
            
            QMessageBox.information(
                self,
                "Erfolg",
                f"Datenbank erfolgreich importiert von:\n{import_path}"
            )
            
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Fehler",
                f"Fehler beim Importieren der Datenbank:\n{exc}"
            )
            # Try to reconnect to original database
            try:
                self.conn = sqlite3.connect(self.current_db_path)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Fehler",
                    f"Fehler beim Wiederherstellen der Verbindung zur Original-Datenbank:\n{e}"
                )

    def closeEvent(self, a0):
        self.conn.close()
        super().closeEvent(a0)

    def event(self, event):
        if isinstance(event, _CallableEvent):
            event.execute()
            return True
        return super().event(event)

# --------------------------------------------------------------------------- #
# Einstellungen Fenster (SettingsWindow)
# --------------------------------------------------------------------------- #
from PyQt5.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFrame, QLabel, QCheckBox, QSpinBox, QHBoxLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QFrame,
    QLabel,
    QCheckBox,
    QSpinBox,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor


class SettingsWindow(QWidget):
    """
    Stand-alone settings window that hosts user-configurable options
    (currently dark-mode + server timeout).
    """

    # -------------------------------------------------------------- #
    # Static helpers
    # -------------------------------------------------------------- #
    @staticmethod
    def _is_dark(app: QApplication) -> bool:
        """Return True when the application is currently in dark mode."""
        # “dark” here == very low lightness (HSV value) of the Window colour
        return app.palette().color(QPalette.Window).value() < 100

    @staticmethod
    def apply_dark_palette(enable: bool) -> None:
        """
        Switch the entire QApplication between light and dark palettes.
        """
        app = QApplication.instance()
        if app is None:  # safety guard (should never happen in normal runtime)
            return

        if enable:
            dark = QPalette()
            dark.setColor(QPalette.Window, QColor(53, 53, 53))
            dark.setColor(QPalette.WindowText, Qt.white)
            dark.setColor(QPalette.Base, QColor(35, 35, 35))
            dark.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            dark.setColor(QPalette.ToolTipBase, Qt.white)
            dark.setColor(QPalette.ToolTipText, Qt.white)
            dark.setColor(QPalette.Text, Qt.white)
            dark.setColor(QPalette.Button, QColor(53, 53, 53))
            dark.setColor(QPalette.ButtonText, Qt.white)
            dark.setColor(QPalette.BrightText, Qt.red)
            dark.setColor(QPalette.Link, QColor(42, 130, 218))
            dark.setColor(QPalette.Highlight, QColor(42, 130, 218))
            dark.setColor(QPalette.HighlightedText, Qt.black)
            app.setPalette(dark)
            # Optional: keep default tooltip styling in dark mode
            app.setStyleSheet(
                "QToolTip { color: #ffffff; background-color: #2a82da; border: 0px; }"
            )
        else:
            app.setPalette(app.style().standardPalette())
            app.setStyleSheet("")

    # -------------------------------------------------------------- #
    # Construction
    # -------------------------------------------------------------- #
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowCloseButtonHint
            | Qt.WindowMinimizeButtonHint
        )
        self.setWindowTitle("Einstellungen")
        self.setMinimumSize(600, 600)
        self.setMaximumSize(800, 800)

        # Slight grey background
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(245, 245, 245))
        self.setPalette(pal)

        # ------------------------------------------------------------------ #
        # Main layout
        # ------------------------------------------------------------------ #
        main_layout = QVBoxLayout(self)

        # Controls
        self.chk_darkmode = QCheckBox("Dark-Mode aktivieren")
        self.chk_darkmode.setChecked(SettingsWindow._is_dark(QApplication.instance()))

        self.spn_timeout = QSpinBox()
        self.spn_timeout.setRange(5, 300)
        self.spn_timeout.setSuffix(" s")
        self.spn_timeout.setValue(parent.server_timeout if parent else 30)

        # Frame for nice white background
        frame = QFrame(self)
        frame.setAutoFillBackground(True)
        frame_pal = frame.palette()
        frame_pal.setColor(QPalette.Window, Qt.white)
        frame.setPalette(frame_pal)

        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(20, 20, 20, 20)
        frame_layout.setSpacing(20)

        heading = QLabel(
            "<h2>Allgemeine Einstellungen</h2>"
            "<p>Hier können Sie Ihre Einstellungen anpassen.</p>"
        )
        heading.setStyleSheet(
            "QLabel { color: #374151; font-size: 20px; font-weight: 600; }"
        )

        frame_layout.addWidget(heading)
        frame_layout.addWidget(self.chk_darkmode)
        frame_layout.addWidget(QLabel("Server-Timeout:"))
        frame_layout.addWidget(self.spn_timeout)

        # -------------------------------------------------------------- #
        # Bottom button row
        # -------------------------------------------------------------- #
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        def _make_btn(text: str) -> QPushButton:
            # Avoid importing the same module (which may be __main__ when executed directly)
            # MainWindow is already defined in this module, so we can reference it directly.
            btn = QPushButton(text)
            btn.setFixedHeight(48)
            btn.setStyleSheet(MainWindow._button_style())
            return btn

        self.btn_apply = _make_btn("Anwenden")
        self.btn_reset = _make_btn("Zurücksetzen")
        self.btn_cancel = _make_btn("Abbrechen")

        self.btn_apply.clicked.connect(self.apply_settings)
        self.btn_reset.clicked.connect(self.reset_settings)
        self.btn_cancel.clicked.connect(self.close)

        btn_row.addWidget(self.btn_apply)
        btn_row.addWidget(self.btn_reset)
        btn_row.addWidget(self.btn_cancel)
        frame_layout.addLayout(btn_row)

        main_layout.addWidget(frame)

    # -------------------------------------------------------------- #
    # Public slots
    # -------------------------------------------------------------- #
    def apply_settings(self) -> None:
        """
        Apply the user-chosen settings to the main application.
        """
        main = self.parent()  # type: ignore
        if main:
            # Dark-mode
            SettingsWindow.apply_dark_palette(self.chk_darkmode.isChecked())
            # Timeout
            main.server_timeout = self.spn_timeout.value()

        QMessageBox.information(self, "Einstellungen", "Änderungen angewendet.")

    def reset_settings(self) -> None:
        """
        Restore UI controls to the values currently used by the application.
        No widgets are recreated – only states are updated.
        """
        main = self.parent()  # type: ignore
        if main:
            self.chk_darkmode.setChecked(SettingsWindow._is_dark(QApplication.instance()))
            self.spn_timeout.setValue(main.server_timeout)

    # -------------------------------------------------------------- #
    # House-keeping: tell MainWindow when we disappear
    # -------------------------------------------------------------- #
    def closeEvent(self, event):
        parent = self.parent()
        if parent and hasattr(parent, "settings_window"):
            parent.settings_window = None  # type: ignore
        super().closeEvent(event)
# --------------------------------------------------------------------------- #
# Application entry point
# --------------------------------------------------------------------------- #
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()