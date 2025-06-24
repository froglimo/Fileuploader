import sys
import os
import sqlite3
import mimetypes
import shutil
import requests
from threading import Thread

import flask  # still available if you want to spin up the server in‐process
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFrame, QPushButton, QFileDialog, QListWidget,
    QListWidgetItem, QLabel, QMessageBox, QAbstractItemView, QStyle,
    QAction,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PyQt5.QtGui import QIcon

DB_NAME = "file_manager.db"
UPLOAD_ENDPOINT = "http://localhost:5001/upload"

from PyQt5.QtCore import QEvent
class _CallableEvent(QEvent):
    def __init__(self, fn):
        super().__init__(QEvent.User)
        self.fn = fn
    def execute(self):
        self.fn()

    # Change to your server URL
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
                border: 2px dashed #a3a3a3;
                border-radius: 12px;
                background-color: #fafafa;
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
        label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(label)

    # Qt drag / drop Event manager ------------------------------------------------ #
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
            local_files = [
                url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()
            ]
            if self.on_files_dropped:
                self.on_files_dropped(local_files)
            event.acceptProposedAction()
        else:
            event.ignore()

class Settings_Window(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.setMinimumSize(600, 500)
class FileListWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 10, 10, 10)

        self.btn_refresh = QPushButton()
        self.btn_refresh.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.btn_refresh.setFixedSize(32, 32)
        self.btn_refresh.setToolTip("Dateiliste aktualisieren")

        header_layout.addWidget(QLabel("Gespeicherte Dateien:"))
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        main_layout.addLayout(header_layout)

        # List
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
        self.btn_add.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.btn_add.setFixedSize(36, 36)
        self.btn_add.setToolTip("Dateien hinzufügen")

        self.btn_delete = QPushButton()
        self.btn_delete.setIcon(self.style().standardIcon(QStyle.SP_TrashIcon))
        self.btn_delete.setFixedSize(36, 36)
        self.btn_delete.setToolTip("Ausgewählte Datei löschen")

        self.btn_download = QPushButton()
        self.btn_download.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        self.btn_download.setFixedSize(36, 36)
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
        item.setData(Qt.UserRole, file_id)
        item.setIcon(self._icon_for_type(filetype))
        self.list_widget.addItem(item)

    def selected_file_id(self):
        item = self.list_widget.currentItem()
        return item.data(Qt.UserRole) if item else None

    # Internal helpers ------------------------------------------------------- #
    @staticmethod
    def _icon_for_type(mime: str) -> QIcon:
        style = QApplication.style()
        if mime.startswith("image/"):
            return QIcon.fromTheme("image-x-generic") or style.standardIcon(
                QStyle.SP_FileIcon
            )
        if "pdf" in mime:
            return QIcon.fromTheme("application-pdf") or style.standardIcon(
                QStyle.SP_FileIcon
            )
        if "zip" in mime or "compressed" in mime:
            return QIcon.fromTheme("package-x-generic") or style.standardIcon(
                QStyle.SP_FileIcon
            )
        if mime.startswith("text/") or mime in (
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ):
            return QIcon.fromTheme("x-office-document") or style.standardIcon(
                QStyle.SP_FileIcon
            )
        return style.standardIcon(QStyle.SP_FileIcon)

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fileuploader")
        self.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon1.png")))
        self.setMinimumSize(800, 600)
        # Current database path
        # Drag-and-drop handler set up in UI initialization
        self.current_db_path = DB_NAME

        # Menu bar
        self._create_menu()

        # DB connection
        self.conn = sqlite3.connect(self.current_db_path)
        self._init_db()

        # Main layout
        self._setup_ui()

        # Init list
        self.load_files()
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
                            f"Failed to upload '{path}' to server:\n{exec}"
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
        self.drag_drop.on_files_dropped = lambda files: (
            self.handle_files_upload(files),
            Thread(target=self.upload_to_server, args=(files,), daemon=True).start()
        )

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

        # Datei
        file_menu = menubar.addMenu("&Datei")
        act_open = QAction("Öffnen…", self, shortcut="Ctrl+O")
        act_open.triggered.connect(self.open_file_dialog)
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
        act_exit = QAction("Beenden", self, shortcut="Ctrl+Q")
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Bearbeiten
        edit_menu = menubar.addMenu("&Bearbeiten")
        edit_menu.addAction(QAction("Rückgängig", self, shortcut="Ctrl+Z"))
        edit_menu.addAction(QAction("Wiederholen", self, shortcut="Ctrl+Y"))
        act_edit_menu = QAction("Einstellungen", self, shortcut="Ctrl+I")
        act_edit_menu.triggered.connect(self.show_settings_window)
        edit_menu.addAction(act_edit_menu)

        # Hilfe
        help_menu = menubar.addMenu("&Hilfe")
        act_about = QAction("Über", self)
        act_about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(act_about)

    def show_settings_window(self):
        if self.show_settings_window is None or not self.show_settings_window.isVisible():
            self.show_settings_window = Settings_Window(self)
        self.show_settings_window.show()
        self.show_settings_window.raise_()
        self.show_settings_window.activateWindow()

    def show_about_dialog(self):
        QMessageBox.about(
            self,
            "Über Fileuploader",
            "Fileuploader v1.0\n\nEin einfacher Drag-&-Drop Datei-Uploader\n© 2024",
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
        allowed = {".doc", ".docx", ".odt", ".odp", ".txt", ".pdf", ".zip", ".7z", ".png", ".jpg", ".jpeg", ".bmp", ".heic", ".webp", "*.avif"}
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
            # Ensure all changes are committed before copying
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
                f"Fehler beim Importieren der Datenbank:\n{exec}"
            )
            # Try to reconnect to original database
            try:
                self.conn = sqlite3.connect(self.current_db_path)
                self._init_db()
                self.load_files()
            except:
                pass

    # -------------------------- Lifecycle --------------------------------- #
    def closeEvent(self, event):
        self.conn.close()
        super().closeEvent(event)

    def event(self, e):
        if isinstance(e, _CallableEvent):
            e.execute()
            return True
        return super().event(e)


# --------------------------------------------------------------------------- #
# Application entry point
# --------------------------------------------------------------------------- #
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(os.path.join(os.path.dirname(__file__), "icon1.png")))  # <-- Add this line
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()