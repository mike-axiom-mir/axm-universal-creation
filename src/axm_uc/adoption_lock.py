from __future__ import annotations

import errno
import hashlib
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class CandidateAdoptionLockError(RuntimeError):
    """Candidate-adoption coordination could not be established safely."""


class CandidateAdoptionBusy(CandidateAdoptionLockError):
    """Another cooperating process currently owns candidate adoption."""


def _lock_path(root: Path) -> Path:
    resolved = Path(root).resolve()
    identity = hashlib.sha256(os.fsencode(str(resolved))).hexdigest()
    return Path(tempfile.gettempdir()) / "axm-universal-creation-locks" / f"{identity}.candidate-adoption.lock"


def _open_lock(path: Path) -> int:
    parent = path.parent
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        parent_stat = parent.lstat()
    except OSError as exc:
        raise CandidateAdoptionLockError(f"candidate-adoption lock directory is unavailable: {exc}") from exc
    if stat.S_ISLNK(parent_stat.st_mode) or not stat.S_ISDIR(parent_stat.st_mode):
        raise CandidateAdoptionLockError("candidate-adoption lock directory is not a real directory")

    prior = None
    try:
        prior = path.lstat()
    except FileNotFoundError:
        pass
    except OSError as exc:
        raise CandidateAdoptionLockError(f"candidate-adoption lock path is unavailable: {exc}") from exc
    if prior is not None and (stat.S_ISLNK(prior.st_mode) or not stat.S_ISREG(prior.st_mode)):
        raise CandidateAdoptionLockError("candidate-adoption lock path is not a regular file")

    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except OSError as exc:
        raise CandidateAdoptionLockError(f"candidate-adoption lock file could not be opened safely: {exc}") from exc

    try:
        current = os.fstat(fd)
        if not stat.S_ISREG(current.st_mode):
            raise CandidateAdoptionLockError("candidate-adoption lock handle is not a regular file")
        if prior is not None and hasattr(prior, "st_ino") and hasattr(current, "st_ino"):
            if (prior.st_dev, prior.st_ino) != (current.st_dev, current.st_ino):
                raise CandidateAdoptionLockError("candidate-adoption lock path changed while it was opened")
        if current.st_size < 1:
            os.lseek(fd, 0, os.SEEK_SET)
            os.write(fd, b"\0")
            os.fsync(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        return fd
    except Exception:
        os.close(fd)
        raise


def _acquire(fd: int) -> None:
    if os.name == "posix":
        import fcntl

        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise CandidateAdoptionBusy("another candidate adoption already owns the host-local lock") from exc
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise CandidateAdoptionBusy("another candidate adoption already owns the host-local lock") from exc
            raise CandidateAdoptionLockError(f"candidate-adoption POSIX lock failed: {exc}") from exc
        return

    if os.name == "nt":
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise CandidateAdoptionBusy("another candidate adoption already owns the host-local lock") from exc
            raise CandidateAdoptionLockError(f"candidate-adoption Windows lock failed: {exc}") from exc
        return

    raise CandidateAdoptionLockError(f"candidate-adoption locking is unsupported on os.name={os.name!r}")


def _release(fd: int) -> None:
    if os.name == "posix":
        import fcntl

        fcntl.flock(fd, fcntl.LOCK_UN)
        return
    if os.name == "nt":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


@contextmanager
def candidate_adoption_lock(root: Path) -> Iterator[dict[str, str]]:
    """Own one host-local candidate-adoption mutation lane.

    The lock is OS-managed and non-blocking. A crashed process releases the OS
    lock when its descriptor closes; the inert lock file may remain in the
    system temporary directory and carries no machine-state authority.
    """

    path = _lock_path(root)
    fd = _open_lock(path)
    acquired = False
    try:
        _acquire(fd)
        acquired = True
        yield {
            "scope": "host-local-cooperating-processes",
            "lock_identity": path.name.split(".", 1)[0],
        }
    finally:
        if acquired:
            try:
                _release(fd)
            finally:
                os.close(fd)
        else:
            os.close(fd)
