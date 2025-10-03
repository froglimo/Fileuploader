import os
import pytest

from Fileuploader import sanitize_relative_path, safe_join


def test_sanitize_relative_path_basic():
    assert sanitize_relative_path("foo.txt") == os.path.join("foo.txt")


def test_sanitize_relative_path_nested():
    p = sanitize_relative_path("a/b/c.txt")
    assert p.endswith(os.path.join("a", "b", "c.txt"))
    assert ".." not in p


def test_sanitize_relative_path_dots_and_empty():
    assert sanitize_relative_path("./../a/./b//c.txt").endswith(os.path.join("a", "b", "c.txt"))


def test_safe_join_inside(tmp_path):
    base = tmp_path
    target = safe_join(str(base), "sub", "file.txt")
    assert target.startswith(str(base))


def test_safe_join_outside_raises(tmp_path):
    base = tmp_path
    with pytest.raises(ValueError):
        safe_join(str(base), "..", "outside.txt")
