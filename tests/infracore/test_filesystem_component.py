"""Tests for FilesystemComponent — §4.3."""

import threading
import time
from pathlib import Path

import pytest
from infracore.bootstrap_components.filesystem_component.filesystem import (
    FilesystemComponent,
)
from infracore.bootstrap_components.signal_component.signal import SignalComponent


class TestComponentVersion:
    """§4.1 — __component_version__ declared."""

    def test_component_version_declared(self):
        """§4.1: FilesystemComponent module exposes __component_version__ as semver."""
        import infracore.bootstrap_components.filesystem_component.filesystem as mod
        assert hasattr(mod, "__component_version__")
        v = mod.__component_version__
        parts = v.split(".")
        assert len(parts) == 3 and all(p.isdigit() for p in parts)


class TestReadWrite:
    """§4.3 — basic read/write/exists/delete/make_dir/list_dir."""

    def test_write_and_read_roundtrip(self, tmp_path):
        """§4.3: write_file followed by read_file returns the same bytes."""
        component = FilesystemComponent()
        p = tmp_path / "test.bin"
        data = b"hello world"
        component.write_file(p, data)
        assert component.read_file(p) == data

    def test_exists_true_after_write(self, tmp_path):
        """§4.3: exists returns True for a path that has been written."""
        component = FilesystemComponent()
        p = tmp_path / "x.txt"
        component.write_file(p, b"data")
        assert component.exists(p) is True

    def test_exists_false_for_missing(self, tmp_path):
        """§4.3: exists returns False for a path that has never been written."""
        component = FilesystemComponent()
        assert component.exists(tmp_path / "ghost.txt") is False

    def test_delete_removes_file(self, tmp_path):
        """§4.3: delete removes the file; subsequent exists returns False."""
        component = FilesystemComponent()
        p = tmp_path / "del.txt"
        component.write_file(p, b"bye")
        component.delete(p)
        assert component.exists(p) is False

    def test_make_dir_creates_directory(self, tmp_path):
        """§4.3: make_dir creates nested directories."""
        component = FilesystemComponent()
        d = tmp_path / "a" / "b" / "c"
        component.make_dir(d, parents=True)
        assert d.is_dir()

    def test_list_dir_returns_paths(self, tmp_path):
        """§4.3: list_dir returns a list of Path objects in the directory."""
        component = FilesystemComponent()
        (tmp_path / "f1.txt").write_bytes(b"1")
        (tmp_path / "f2.txt").write_bytes(b"2")
        result = component.list_dir(tmp_path)
        names = {p.name for p in result}
        assert "f1.txt" in names and "f2.txt" in names


class TestPerPathSerialization:
    """§4.3 — writes to the same path are serialized; writes to different paths are independent."""

    def test_same_path_writes_are_ordered(self, tmp_path):
        """§4.3: concurrent writes to the same path do not interleave — last writer wins."""
        component = FilesystemComponent()
        p = tmp_path / "shared.bin"
        results = []
        barrier = threading.Barrier(2)

        def writer(value: bytes):
            barrier.wait()
            component.write_file(p, value)
            results.append(value)

        t1 = threading.Thread(target=writer, args=(b"aaa",))
        t2 = threading.Thread(target=writer, args=(b"bbb",))
        t1.start(); t2.start()
        t1.join(); t2.join()

        final = component.read_file(p)
        assert final in (b"aaa", b"bbb")
        assert len(results) == 2

    def test_different_path_writes_proceed_independently(self, tmp_path):
        """§4.3: writes to different paths are not serialized against each other."""
        component = FilesystemComponent()
        p1 = tmp_path / "a.bin"
        p2 = tmp_path / "b.bin"
        barrier = threading.Barrier(2)
        done = []

        def writer(p, v):
            barrier.wait()
            component.write_file(p, v)
            done.append(p)

        t1 = threading.Thread(target=writer, args=(p1, b"x"))
        t2 = threading.Thread(target=writer, args=(p2, b"y"))
        t1.start(); t2.start()
        t1.join(); t2.join()
        assert len(done) == 2


class TestWatch:
    """§4.3 — watch/unwatch with FilesystemEvent."""

    def test_watch_returns_subscription_handle(self, tmp_path):
        """§4.3: watch returns a SubscriptionHandle."""
        signal_comp = SignalComponent()
        component = FilesystemComponent(signal_component=signal_comp)
        from infracore.bootstrap_components.signal_component.handle import SubscriptionHandle
        handle = component.watch(tmp_path, lambda e: None)
        assert isinstance(handle, SubscriptionHandle.__supertype__)

    def test_unwatch_does_not_raise(self, tmp_path):
        """§4.3: unwatch with a valid handle does not raise."""
        signal_comp = SignalComponent()
        component = FilesystemComponent(signal_component=signal_comp)
        handle = component.watch(tmp_path, lambda e: None)
        component.unwatch(handle)


class TestRenameMoveCopy:
    """service-extender Sprint 1 — rename/move/copy (FilesystemService v1.1.0)."""

    def test_rename_renames_file(self, tmp_path):
        """rename(src, dst) moves file; src gone, dst has original bytes."""
        component = FilesystemComponent()
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_bytes(b"data")
        component.rename(src, dst)
        assert not src.exists()
        assert dst.read_bytes() == b"data"

    def test_move_moves_file_to_different_dir(self, tmp_path):
        """move(src, dst) relocates file across directories; src gone, dst has bytes."""
        component = FilesystemComponent()
        src = tmp_path / "a.txt"
        sub = tmp_path / "sub"
        sub.mkdir()
        src.write_bytes(b"data")
        dst = sub / "a.txt"
        component.move(src, dst)
        assert not src.exists()
        assert dst.read_bytes() == b"data"

    def test_copy_duplicates_file(self, tmp_path):
        """copy(src, dst) duplicates file; src still exists, dst has same bytes."""
        component = FilesystemComponent()
        src = tmp_path / "a.txt"
        dst = tmp_path / "b.txt"
        src.write_bytes(b"data")
        component.copy(src, dst)
        assert src.exists()
        assert dst.read_bytes() == b"data"
