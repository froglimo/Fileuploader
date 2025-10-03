import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QListWidgetItem

from Fileuploader import FileListWidget


def test_add_and_select_item(qapp):
    w = FileListWidget()
    w.add_file_item(42, "report.pdf", "application/pdf")
    assert w.list_widget.count() == 1
    item: QListWidgetItem = w.list_widget.item(0)
    assert "report.pdf" in item.text()

    w.list_widget.setCurrentRow(0)
    assert w.selected_file_id() == 42


def test_clear_list(qapp):
    w = FileListWidget()
    for i in range(3):
        w.add_file_item(i, f"f{i}.txt", "text/plain")
    assert w.list_widget.count() == 3
    w.clear_list()
    assert w.list_widget.count() == 0
