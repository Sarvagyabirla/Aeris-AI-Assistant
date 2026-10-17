"""Windows RegisterHotKey only; never hooks or records general keyboard input."""
import ctypes
import os
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter


class GlobalHotkeys(QAbstractNativeEventFilter):
    def __init__(self, app, restore, stop, push_to_talk, backend=None):
        super().__init__()
        self.app = app
        self.backend = backend if backend is not None else (ctypes.WinDLL('user32', use_last_error=True) if os.name == 'nt' else None)
        self.callbacks = {0x4101: restore, 0x4102: stop, 0x4103: push_to_talk}
        self.registered = set()
        if self.backend is not None:
            self.backend.RegisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT)
            self.backend.RegisterHotKey.restype = wintypes.BOOL
            self.backend.UnregisterHotKey.argtypes = (wintypes.HWND, ctypes.c_int)
            self.backend.UnregisterHotKey.restype = wintypes.BOOL
            for identifier, key in ((0x4101, ord('A')), (0x4102, ord('S')), (0x4103, 0x20)):
                if self.backend.RegisterHotKey(None, identifier, 0x4000 | 0x0001 | 0x0002, key):
                    self.registered.add(identifier)
            app.installNativeEventFilter(self)

    @property
    def can_restore(self):
        return 0x4101 in self.registered

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b'windows_generic_MSG', b'windows_dispatcher_MSG'):
            event = wintypes.MSG.from_address(int(message))
            if event.message == 0x0312 and event.wParam in self.registered:
                self.callbacks[event.wParam]()
                return True, 0
        return False, 0

    def close(self):
        self.app.removeNativeEventFilter(self)
        if self.backend is not None:
            for identifier in self.registered:
                self.backend.UnregisterHotKey(None, identifier)
        self.registered.clear()
