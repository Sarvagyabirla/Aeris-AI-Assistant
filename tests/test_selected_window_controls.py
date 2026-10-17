import os
import sys
from dataclasses import replace
from types import SimpleNamespace

from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest, ActionResult
from aeris.state import CancellationToken


def native_fixture(assistant, monkeypatch):
    state = {'minimized': False, 'maximized': False, 'calls': []}
    identity = {'window_id': 101, 'process_id': os.getpid() + 1000, 'process_created': 12.0, 'expected_title': 'Fixture Notepad', 'process_name': 'notepad.exe'}
    def show(hwnd, value):
        state['calls'].append((hwnd, value))
        state['minimized'] = value == 6
        state['maximized'] = value == 3
        return True
    monkeypatch.setattr('aeris.tools.desktop._WindowState', lambda: SimpleNamespace(show=show,
        is_minimized=lambda _: state['minimized'], is_maximized=lambda _: state['maximized']))
    monkeypatch.setitem(sys.modules, 'win32gui', SimpleNamespace(GetForegroundWindow=lambda: 101,
        ShowWindowAsync=show, IsIconic=lambda _: state['minimized'], IsZoomed=lambda _: state['maximized']))
    monkeypatch.setattr(assistant._desktop, '_require_windows', lambda: None)
    monkeypatch.setattr(assistant._desktop, '_window_identity', lambda _, expected=None: dict(identity))
    return state, identity


def test_registry_selected_minimize_has_identity_and_readback(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    state, identity = native_fixture(assistant, monkeypatch)
    try:
        result = assistant.registry.execute(ActionRequest('desktop.window_action', {'action': 'minimize_current'}))
        assert result.success and result.data['verified']
        assert state['calls'] == [(identity['window_id'], 6)]
    finally:
        assistant.close()


def test_own_or_changed_window_cannot_be_minimized(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    state, identity = native_fixture(assistant, monkeypatch)
    try:
        identity['process_id'] = os.getpid()
        result = assistant.registry.execute(ActionRequest('desktop.window_action', {'action': 'minimize_current'}))
        assert not result.success and not state['calls']
        identity['process_id'] += 1000
        prepared = assistant._desktop.prepare_window_action({'action': 'minimize_current'})
        identity['expected_title'] = 'Changed target'
        result = assistant._desktop.window_action(prepared)
        assert not result.success and not state['calls']
    finally:
        assistant.close()


def test_cancel_wins_window_dispatch_gate(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    state, _ = native_fixture(assistant, monkeypatch)
    try:
        prepared = assistant._desktop.prepare_window_action({'action': 'maximize_current'})
        token = CancellationToken()
        token.cancel()
        result = assistant._desktop.window_action(prepared, token)
        assert not result.success and not state['calls']
    finally:
        assistant.close()


def test_close_current_window_uses_exact_normal_close_not_alt_f4(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    _, identity = native_fixture(assistant, monkeypatch)
    posted = []
    sys.modules['win32gui'].PostMessage = lambda *args: posted.append(args)
    try:
        result = assistant.registry.execute(ActionRequest('desktop.close_current_window'), lambda *_: False)
        assert not result.success and not posted
        result = assistant.registry.execute(ActionRequest('desktop.close_current_window'), lambda *_: True)
        assert result.success and posted == [(identity['window_id'], 0x10, 0, 0)]
        assert not result.data['verified']  # dispatch preserves the app's save prompt
    finally:
        assistant.close()


def test_required_offline_three_step_goal_uses_selected_window(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    state, identity = native_fixture(assistant, monkeypatch)
    for tool in ('desktop.open_app', 'desktop.set_volume'):
        assistant.registry._tools[tool] = replace(assistant.registry._tools[tool],
            handler=lambda args, token=None: ActionResult(True, 'Fixture verified', {'verified': True}))
    try:
        turn = assistant.handle('Aeris, open Notepad, set volume to 35, and minimize this window')
        assert turn.success and len(turn.results) == 3
        assert all(result.data['verified'] for result in turn.results)
        assert state['calls'] == [(identity['window_id'], 6)]
    finally:
        assistant.close()


def test_native_window_exports_exist_without_invoking_a_window():
    if os.name != 'nt':
        import pytest
        pytest.skip('Win32 export presence check; no live window invocation')
    from aeris.tools.desktop import _WindowState
    adapter = _WindowState()
    assert callable(adapter.user32.ShowWindowAsync)
    assert callable(adapter.user32.IsZoomed)
    assert callable(adapter.user32.IsIconic)
