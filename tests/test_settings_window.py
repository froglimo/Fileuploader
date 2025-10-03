import os

import pytest

from Fileuploader import SettingsWindow
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QApplication


def test_is_dark_false_in_default_palette(qapp):
    # Ensure default palette is applied to avoid dark mode
    qapp.setPalette(qapp.style().standardPalette())
    assert SettingsWindow._is_dark(qapp) is False


def test_apply_dark_palette_toggles(qapp):
    # Start with a known light palette
    qapp.setPalette(qapp.style().standardPalette())
    SettingsWindow.apply_dark_palette(True)
    # Window background gets dark
    win_color = qapp.palette().color(QPalette.Window)
    assert win_color != qapp.style().standardPalette().color(QPalette.Window)

    # Toggle off back to default
    SettingsWindow.apply_dark_palette(False)
    assert qapp.palette().color(QPalette.Window) == qapp.style().standardPalette().color(QPalette.Window)
