import os
import pytest

# Prevent side effects when importing the app module in tests
os.environ.setdefault("FILEUPLOADER_SKIP_BOOTSTRAP", "1")
os.environ.setdefault("FILEUPLOADER_NO_SERVER", "1")


@pytest.fixture(scope="session")
def qapp():
    """Provide a single QApplication for all GUI-related tests."""
    try:
        from PyQt5.QtWidgets import QApplication
    except Exception as e:
        pytest.skip(f"PyQt5 is required for GUI tests: {e}")
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture(autouse=True)
def no_message_boxes(monkeypatch):
    """Avoid blocking UI dialogs during tests by patching QMessageBox.* methods."""
    try:
        from PyQt5 import QtWidgets
    except Exception:
        # If PyQt5 isn't available for some reason, skip patching
        return

    def _ok(*args, **kwargs):
        return QtWidgets.QMessageBox.Ok

    def _yes(*args, **kwargs):
        return QtWidgets.QMessageBox.Yes

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", staticmethod(_ok), raising=False)
    monkeypatch.setattr(QtWidgets.QMessageBox, "warning", staticmethod(_ok), raising=False)
    monkeypatch.setattr(QtWidgets.QMessageBox, "question", staticmethod(_yes), raising=False)
