import json
import os
import io

import pytest

from PyQt5.QtWidgets import QFileDialog

from Fileuploader import MainWindow, FILES_ENDPOINT, DELETE_ENDPOINT_TEMPLATE, DOWNLOAD_ENDPOINT_TEMPLATE


class DummyResp:
    def __init__(self, status=200, json_data=None, content=b"", stream=False):
        self.status_code = status
        self._json = json_data or {}
        self._content = content
        self._iter = [content] if content else []
        self._stream = stream

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"status {self.status_code}")

    def json(self):
        return self._json

    def iter_content(self, chunk_size=8192):
        for chunk in self._iter:
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def mw(qapp):
    w = MainWindow()
    # make window not show to avoid GUI popups
    return w


def test_load_files_success(monkeypatch, mw):
    files = {"files": [
        {"id": 1, "original_filename": "a.txt", "content_type": "text/plain"},
        {"id": 2, "original_filename": "b.pdf", "content_type": "application/pdf"},
    ]}

    def fake_get(url, *args, **kwargs):
        if url == FILES_ENDPOINT:
            return DummyResp(json_data=files)
        raise AssertionError("Unexpected GET url")

    monkeypatch.setattr("Fileuploader.requests.get", fake_get)

    mw.load_files()
    assert mw.file_widget.list_widget.count() == 2


def test_delete_selected_file_flow(monkeypatch, mw):
    # Prepare list
    mw.file_widget.add_file_item(10, "x.txt", "text/plain")
    mw.file_widget.list_widget.setCurrentRow(0)

    posted = {}

    def fake_post(url, *args, **kwargs):
        posted["url"] = url
        return DummyResp()

    monkeypatch.setattr("Fileuploader.requests.post", fake_post)
    mw.delete_selected_file()
    assert posted["url"] == DELETE_ENDPOINT_TEMPLATE.format(id=10)


def test_open_file_dialog_filters_and_triggers_upload(monkeypatch, mw, tmp_path):
    # Create temp files
    good = tmp_path / "x.pdf"
    bad = tmp_path / "x.exe"
    good.write_bytes(b"ok")
    bad.write_bytes(b"no")

    selected = [str(good), str(bad)]
    called = {"upload": False, "files": None}

    def fake_getOpenFileNames(*args, **kwargs):
        return selected, ""

    def fake_upload(files):
        called["upload"] = True
        called["files"] = files

    monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(fake_getOpenFileNames))
    monkeypatch.setattr(mw, "upload_to_server", fake_upload)

    mw.open_file_dialog()

    # Only the good file should pass the filter and trigger upload
    assert called["upload"] is True
    assert called["files"] == [str(good)]


def test_download_selected_file_flow(monkeypatch, mw, tmp_path):
    # Prepare list with selected item
    mw.file_widget.add_file_item(5, "readme.txt", "text/plain")
    mw.file_widget.list_widget.setCurrentRow(0)

    # Fake list & download endpoints
    files = {"files": [{"id": 5, "original_filename": "readme.txt", "content_type": "text/plain"}]}

    def fake_get(url, *args, **kwargs):
        if url == FILES_ENDPOINT:
            return DummyResp(json_data=files)
        if url == DOWNLOAD_ENDPOINT_TEMPLATE.format(id=5):
            return DummyResp(json_data={}, content=b"hello", stream=True)
        raise AssertionError(f"Unexpected GET: {url}")

    def fake_getSaveFileName(*args, **kwargs):
        return str(tmp_path / "out.txt"), ""

    monkeypatch.setattr("Fileuploader.requests.get", fake_get)
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(fake_getSaveFileName))

    mw.download_selected_file()

    # Verify file written
    out = tmp_path / "out.txt"
    assert out.exists() and out.read_bytes() == b"hello"
