import ctypes
import os
import uuid
from ctypes import wintypes

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication
from test_desktop_lifecycle import pump

from aeris.ui.hotkeys import GlobalHotkeys
from aeris.ui.single_instance import InstanceServer


class NativeFunction:
    def __init__(self, callback):
        self.callback = callback

    def __call__(self, *args):
        return self.callback(*args)


def test_hotkeys_only_dispatch_registered_messages_and_unregister():
    app = QApplication.instance() or QApplication([])
    called, released = [], []
    class Native:
        RegisterHotKey = NativeFunction(lambda _, identifier, modifiers, key: identifier != 0x4103)
        UnregisterHotKey = NativeFunction(lambda _, identifier: released.append(identifier) or True)
    keys = GlobalHotkeys(app, lambda: called.append('restore'), lambda: called.append('stop'), lambda: called.append('talk'), backend=Native())
    try:
        assert keys.can_restore
        event = wintypes.MSG(message=0x312, wParam=0x4102)
        assert keys.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(event))[0]
        assert called == ['stop']
        event.wParam = 0x4103
        assert not keys.nativeEventFilter(b'windows_generic_MSG', ctypes.addressof(event))[0]
        assert called == ['stop']
    finally:
        keys.close()
    assert set(released) == {0x4101, 0x4102}


def test_same_user_local_restore_channel_accepts_no_task_data(monkeypatch):
    app = QApplication.instance() or QApplication([])
    name = 'aeris-fixture-' + uuid.uuid4().hex
    monkeypatch.setattr('aeris.ui.single_instance.server_name', lambda: name)
    restored = []
    server = InstanceServer(lambda: restored.append(True))
    socket = QLocalSocket()
    try:
        socket.connectToServer(name)
        pump(app, lambda: bool(restored))
        assert restored == [True]
    finally:
        socket.abort()
        server.close()
