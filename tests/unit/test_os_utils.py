"""Unit tests for os_utils."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from tactus.os_utils import (
    Search,
    ping,
    strip_off_mount_path,
    tactusmakedirs,
)


class TestSearch:
    """Test the Search class."""

    def test_find_files_return_type(self):
        """Test that the return type of find_files is a list."""
        files = Search.find_files(
            directory="/",
            prefix="",
            postfix="",
            recursive=False,
            onlyfiles=True,
            fullpath=True,
            olderthan=None,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory="/",
            prefix="",
            postfix="",
            pattern="(.*)",
            recursive=False,
            onlyfiles=True,
            fullpath=True,
            olderthan=None,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory="/",
            prefix="",
            postfix="",
            recursive=False,
            onlyfiles=True,
            fullpath=False,
            olderthan=None,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory="/",
            prefix="",
            postfix="",
            recursive=False,
            onlyfiles=False,
            fullpath=True,
            olderthan=None,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory="/",
            prefix="",
            postfix="",
            recursive=False,
            onlyfiles=False,
            fullpath=False,
            olderthan=400.0,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory=".",
            prefix="",
            postfix="",
            recursive=True,
            onlyfiles=False,
            fullpath=False,
            olderthan=None,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory=".",
            prefix="",
            postfix=".py",
            recursive=True,
            onlyfiles=True,
            fullpath=False,
            olderthan=None,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory="/",
            prefix="",
            postfix="",
            recursive=False,
            onlyfiles=False,
            fullpath=True,
            olderthan=0,
            inorder=False,
        )
        assert isinstance(files, list)

        files = Search.find_files(
            directory=".",
            prefix="",
            postfix="",
            recursive=False,
            onlyfiles=False,
            fullpath=True,
            olderthan=0,
            inorder=True,
        )
        assert isinstance(files, list)

    def test_search_constructor_return_type(self):
        """Test that the return type of the Search constructor is a Search object."""
        search = Search()
        assert isinstance(search, Search)


def test_tactusmakedirs():
    """Test that creation of directories and change of unix_group works."""
    path = tempfile.mkdtemp()
    if os.path.exists(path):
        shutil.rmtree(path)
    grpids = os.getgroups()
    if len(grpids) > 1:
        newgrp = grpids[1]
        tactusmakedirs(f"{path}/wrkdir", unixgroup=newgrp)
        assert os.stat(path).st_gid == newgrp

    path = tempfile.mkdtemp()
    if os.path.exists(path):
        shutil.rmtree(path)
    tactusmakedirs(f"{path}/wrkdir")
    assert os.stat(path).st_gid in grpids


def test_lockfile_basic():
    """Test the FileLock class."""
    from tactus.os_utils import FileLock

    path = tempfile.mkdtemp()
    filepath = f"{path}/testfile"
    lockfile_path = f"{filepath}.lock"

    lockfile = Path(lockfile_path)
    lockfile.touch(exist_ok=True)

    assert os.path.exists(lockfile_path)
    with (
        pytest.raises(TimeoutError),
        FileLock(filepath, timeout=0.1, check_interval=0.1, delete_existing=False),
    ):
        assert os.path.exists(lockfile_path)
    assert os.path.exists(lockfile_path)
    with FileLock(filepath, delete_existing=True):
        assert os.path.exists(lockfile_path)
    assert not os.path.exists(lockfile_path)


def test_lockfile_timeout():
    """Test the FileLock class."""
    from tactus.os_utils import FileLock

    path = tempfile.mkdtemp()
    filepath = f"{path}/testfile"
    lockfile_path = f"{filepath}.lock"

    lockfile = Path(lockfile_path)
    lockfile.touch(exist_ok=True)

    assert os.path.exists(lockfile_path)
    with (
        pytest.raises(TimeoutError),
        FileLock(filepath, timeout=0.1, check_interval=0.1, delete_existing=False),
    ):
        assert os.path.exists(lockfile_path)
    assert os.path.exists(lockfile_path)


def test_lockfile_thread():
    """Test the FileLock class."""
    from threading import Thread
    from time import sleep

    from tactus.os_utils import FileLock

    def get_lock(filepath):
        with FileLock(filepath):
            sleep(0.5)

    path = tempfile.mkdtemp()
    filepath = f"{path}/testfile"
    thread = Thread(target=get_lock, args=(filepath,))
    thread2 = Thread(target=get_lock, args=(filepath,))
    thread.start()
    thread2.start()
    thread.join()


def _lockfile_stress_worker(args):
    """Worker used by ``test_lockfile_stress`` (must be module-level to pickle).

    Performs a read-modify-write on a shared counter file under the FileLock.
    If the lock is racy, either a ``FileExistsError`` will be raised or
    concurrent workers will overwrite each other's updates and the final
    counter value will be less than expected.
    """
    from time import sleep

    from tactus.os_utils import FileLock

    filepath, counter_path, n_iters = args
    for _ in range(n_iters):
        with FileLock(filepath, timeout=30, check_interval=0.01):
            with open(counter_path, "r") as f:
                n = int(f.read().strip())
            # Widen the critical section to make any race easy to observe.
            sleep(0.001)
            with open(counter_path, "w") as f:
                f.write(str(n + 1))


def test_lockfile_stress():
    """Stress test FileLock under concurrent processes.

    Regression test for a race condition where the previous
    ``check_exists -> create`` sequence in ``FileLock.__enter__`` allowed two
    processes to both believe they held the lock when starting in parallel
    (e.g. running the test suite with ``pytest-xdist``).
    """
    import multiprocessing as mp

    n_workers = 8
    n_iters = 15
    path = tempfile.mkdtemp()
    filepath = f"{path}/protected"
    counter_path = f"{path}/counter"
    with open(counter_path, "w") as f:
        f.write("0")

    # "spawn" avoids inheriting pytest/coverage state and matches the
    # behaviour of parallel test runners on all platforms.
    ctx = mp.get_context("spawn")
    with ctx.Pool(n_workers) as pool:
        pool.map(
            _lockfile_stress_worker,
            [(filepath, counter_path, n_iters) for _ in range(n_workers)],
        )

    with open(counter_path) as f:
        final = int(f.read().strip())
    assert final == n_workers * n_iters, (
        f"Lost updates under contention: got {final}, "
        f"expected {n_workers * n_iters}. FileLock has a race condition."
    )
    # Lock should have been released cleanly by every worker.
    assert not os.path.exists(f"{filepath}.lock")


def test_ping():
    """Test the ping function."""
    hostname = "localhost"

    assert ping(hostname) is True
    assert ping("foo") is False


def with_mock_user(func):
    """Decorator to set the USER environment variable to a mock user."""
    mock_user = "testuser1234"

    def wrapper(self, *args, **kwargs):
        with mock.patch.dict(os.environ, {"USER": mock_user}):
            return func(self, mock_user, *args, **kwargs)

    return wrapper


def with_no_user_var(func):
    """Decorator to unset the USER environment variable."""

    def wrapper(self, *args, **kwargs):
        original_user = os.environ.get("USER")
        # Only unset the USER environment variable if it is set
        if original_user:
            os.environ.pop("USER")

        func(self, *args, **kwargs)
        # Restore the original USER environment variable
        if original_user:
            os.environ["USER"] = original_user

    return wrapper


class TestStripOffMountPath:
    """Test the strip_off_mount_path function."""

    @with_no_user_var
    def test_no_user_in_path(self):
        """Test that the function returns input path, when no user in path."""
        test_path = Path("/foo/bar")
        assert strip_off_mount_path(test_path) == test_path

    @with_mock_user
    def test_user_in_path(self, mock_user):
        """Test the function when user in path, but nothing to strip."""
        test_path = Path(f"/home/{mock_user}/foo/bar")
        assert strip_off_mount_path(test_path) == test_path

    @with_mock_user
    def test_user_in_path_with_mount(self, mock_user):
        """Test the function when user in path and mount path to strip."""
        test_path = Path(f"/etc/ecmwf/nfs/dh1_home_b/{mock_user}/foo/bar")
        expected_result = Path(f"/home/{mock_user}/foo/bar")

        assert strip_off_mount_path(test_path) == expected_result

    @with_mock_user
    def test_user_in_path_with_mount_double_underscore(self, mock_user):
        """Test the function when user in path and double underscore mount path to strip."""
        test_path = Path(f"/etc/ecmwf/nfs/dh1_10_perm_b/{mock_user}/foo/bar")
        expected_result = Path(f"/perm/{mock_user}/foo/bar")

        assert strip_off_mount_path(test_path) == expected_result
