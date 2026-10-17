from dataclasses import replace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest, ActionResult
from aeris.routines import scope_fingerprint
from aeris.tasks import TaskPlan


def test_selected_additional_root_and_persistent_revocation(tmp_path):
    root = tmp_path / 'additional-drive-fixture'
    root.mkdir()
    config = make_config(tmp_path, dry_run=False).with_overrides(allowed_paths=(root,))
    assistant = AerisAssistant(config)
    assert assistant.handle(f'list files in {root}').success
    assistant.scope_policy.revoke(root)
    result = assistant.registry.execute(ActionRequest('files.list', {'path': str(root)}))
    assert not result.success
    assistant.close()
    restarted = AerisAssistant(config)
    try:
        result = restarted.registry.execute(ActionRequest('files.list', {'path': str(root)}))
        assert not result.success
        restarted.scope_policy.replace((root,))  # unrelated Settings save cannot regrant
        assert not restarted.registry.execute(ActionRequest('files.list', {'path': str(root)})).success
        restarted.scope_policy.allow(root)
        assert restarted.registry.execute(ActionRequest('files.list', {'path': str(root)})).success
    finally:
        restarted.close()


@pytest.mark.parametrize('path', ['.env', '.ssh/id_rsa', 'Browser/Login Data', 'credentials.json', '.git/config'])
def test_broad_scope_excludes_protected_targets(tmp_path, path):
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('fixture secret')
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    called = []
    try:
        result = assistant.registry.execute(ActionRequest('files.read', {'path': str(target)}), lambda *_: called.append(True) or True)
        assert not result.success and not result.data.get('text')
    finally:
        assistant.close()


def test_reviewed_study_routine_runs_once_and_scope_change_blocks(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    plan = TaskPlan.from_actions([ActionRequest('desktop.open_app', {'name': 'notepad'}),
                                  ActionRequest('desktop.set_volume', {'level': 35}),
                                  ActionRequest('reminder.set', {'when': 'in 25 minutes', 'message': 'Study break'})])
    calls = []
    for name in ('desktop.open_app', 'desktop.set_volume'):
        assistant.registry._tools[name] = replace(assistant.registry._tools[name],
            handler=lambda args, token=None: calls.append(args) or ActionResult(True, 'Fixture verified', {'verified': True}))
    assistant.routine_store.save_reviewed('study mode', plan, scope_fingerprint(assistant.config))
    approvals = []
    try:
        turn = assistant.handle('Aeris, run routine study mode', lambda *args: approvals.append(args) or True)
        assert turn.success and len(turn.results) == 3 and len(calls) == 2
        assert len(approvals) == 0  # reviewed local reminder; sends/installs excluded from routines
        assistant.config = assistant.config.with_overrides(allowed_paths=())
        turn = assistant.handle('run routine study mode', lambda *_: True)
        assert not turn.success and len(calls) == 2
    finally:
        assistant.close()


def test_assist_previews_low_risk_effect_and_denial_has_no_effect(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False).with_overrides(automation_mode='assist'))
    calls = []
    assistant.registry._tools['desktop.set_volume'] = replace(assistant.registry._tools['desktop.set_volume'],
        handler=lambda args, token=None: calls.append(args))
    try:
        turn = assistant.handle('set volume to 35', lambda *_: False)
        assert not turn.success and not calls
    finally:
        assistant.close()


def test_capability_revocation_prevents_preparation_and_survives_restart(tmp_path):
    config = make_config(tmp_path, dry_run=False)
    assistant = AerisAssistant(config)
    prepared = []
    assistant.registry._tools['desktop.type_text'] = replace(assistant.registry._tools['desktop.type_text'],
        prepare=lambda args, token=None: prepared.append(args) or args)
    assistant.permissions.profile.set_enabled('desktop', False)
    try:
        result = assistant.registry.execute(ActionRequest('desktop.type_text', {'text': 'fixture'}), lambda *_: True)
        assert not result.success and not prepared
    finally:
        assistant.close()
    restarted = AerisAssistant(config)
    try:
        assert not restarted.permissions.profile.allows('desktop.open_app')
        assert restarted.permissions.profile.allows('desktop.clipboard_read')
        assert len([item for item in restarted.registry.definitions() if item['name'] in {'email.send', 'email.send_email'}]) == 1
    finally:
        restarted.close()


def test_changed_app_catalog_invalidates_routine(tmp_path):
    config = make_config(tmp_path)
    config.app_catalog_file.write_text('{"notepad": ["fixture-before.exe"]}')
    assistant = AerisAssistant(config)
    plan = TaskPlan.from_actions([ActionRequest('desktop.open_app', {'name': 'notepad'})])
    assistant.routine_store.save_reviewed('study', plan, scope_fingerprint(config))
    config.app_catalog_file.write_text('{"notepad": ["fixture-after.exe"]}')
    try:
        turn = assistant.handle('run routine study', lambda *_: True)
        assert not turn.success and not turn.results
    finally:
        assistant.close()


def test_trusted_mode_requires_reviewed_workflow_context(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path).with_overrides(automation_mode='trusted'))
    plan = TaskPlan.from_actions([ActionRequest('desktop.open_app', {'name': 'notepad'})])
    assistant.routine_store.save_reviewed('study', plan, scope_fingerprint(assistant.config))
    try:
        assert not assistant.handle('open notepad', lambda *_: True).success
        assert assistant.handle('run routine study', lambda *_: True).success
        assert assistant.handle('status').success
    finally:
        assistant.close()


def test_organization_portable_adapter_rejects_without_file_effects(tmp_path, monkeypatch):
    from types import SimpleNamespace
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    monkeypatch.setattr('aeris.tools.organization.os', SimpleNamespace(name='posix'))
    try:
        result = assistant.registry.execute(ActionRequest('files.organize', {'path': str(tmp_path)}), lambda *_: True)
        assert not result.success and result.error == 'windows_only'
    finally:
        assistant.close()
