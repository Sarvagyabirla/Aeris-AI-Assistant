"""Publish staged bytes without a check-then-overwrite race."""
from __future__ import annotations

import ctypes
import os
import stat
from pathlib import Path


class _FileDispositionInfo(ctypes.Structure):
    # winbase.h declares BOOLEAN (one byte), not Win32 BOOL (four bytes).
    _fields_ = [("DeleteFile", ctypes.c_ubyte)]


def publish_exclusive(staged: Path, destination: Path, token=None) -> None:
    """Link on the destination filesystem; unsupported filesystems fail closed.

    Unlike rename/replace, a hard-link creation never overwrites an existing
    filename on any supported platform. The caller owns and removes its stage.
    """
    def effect():
        os.link(staged, destination)
    if token:
        token.commit(effect)
    else:
        effect()


class HeldSource:
    """Read a stable Windows file and optionally remove that handle's identity.

    Windows sharing rejects writers and renames while held. POSIX supports
    observed copy snapshots; identity-preserving source deletion is unavailable.
    """

    def __init__(self, path: Path, *, move: bool):
        self.path = path
        self.delete_access = move and os.name == "nt"
        if os.name == "nt":
            import msvcrt
            from ctypes import wintypes

            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            create = kernel.CreateFileW
            create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                               wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
            create.restype = wintypes.HANDLE
            handle = create(str(path), 0x80000000 | (0x10000 if move else 0),
                            0x1, None, 3, 0x00200000, None)
            if handle == wintypes.HANDLE(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY)
            except Exception:
                close = kernel.CloseHandle
                close.argtypes = [wintypes.HANDLE]
                close(handle)
                raise
            self._kernel = kernel
            self._native_handle = handle
        else:
            if move:
                raise NotImplementedError("Identity-preserving source deletion requires Windows.")
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            self.handle = os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)
            raise
        try:
            self.initial = os.fstat(self.handle.fileno())
            if not stat.S_ISREG(self.initial.st_mode):
                raise ValueError("Only regular source files can be transferred.")
        except BaseException:
            self.close()
            raise

    def delete_owned(self) -> None:
        from ctypes import wintypes

        dispose = self._kernel.SetFileInformationByHandle
        dispose.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
        dispose.restype = wintypes.BOOL
        value = _FileDispositionInfo(True)
        if not dispose(self._native_handle, 4, ctypes.byref(value), ctypes.sizeof(value)):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        self.handle.close()


def cleanup_owned_stage(path: Path, identity: tuple[int, int], held: HeldSource | None = None) -> bool:
    """Remove only the created inode; a replacement is retained for review.

    Windows deletes by the protected handle. POSIX cleanup checks identity but
    cannot exclude an outside replacement between its last check and unlink.
    """
    clean = False
    try:
        if held is not None and os.name == "nt" and not held.delete_access:
            held.close()
            held = None
        if held is None:
            held = HeldSource(path, move=os.name == "nt")
        if (held.initial.st_dev, held.initial.st_ino) != identity:
            return False
        if os.name == "nt":
            held.delete_owned()
        else:
            current = path.stat(follow_symlinks=False)
            if (current.st_dev, current.st_ino) != identity:
                return False
            path.unlink()
        clean = True
    except (OSError, ValueError):
        clean = False
    finally:
        if held is not None:
            try:
                held.close()
            except OSError:
                clean = False
    return clean
