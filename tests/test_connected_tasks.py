import json
from dataclasses import replace

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.integrations.planning import parse_plan
from aeris.models import ActionResult


def test_offline_compound_executes_all_validated_steps(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    calls = []
    for name in ('desktop.open_app', 'desktop.set_volume', 'desktop.set_brightness'):
        spec = assistant.registry._tools[name]
        assistant.registry._tools[name] = replace(spec, handler=lambda args, token=None, name=name:
            (calls.append((name, args)) or ActionResult(True, 'Fixture verified', {'verified': True})))
    try:
        turn = assistant.handle('Aeris, open Notepad, set volume to 35, and set brightness to 20')
        assert turn.success and len(turn.results) == 3
        assert [name for name, _ in calls] == ['desktop.open_app', 'desktop.set_volume', 'desktop.set_brightness']
    finally:
        assistant.close()


@pytest.mark.parametrize('text', [
    "don't set volume to 100 and open notepad",
    'set volume to -10 and open notepad',
    'open notepad and set volume to 35.5',
    'open notepad and delete everything',
    'if I open notepad then set volume to 35',
])
def test_compound_has_no_partial_effect(tmp_path, text):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    calls = []
    spec = assistant.registry._tools['desktop.open_app']
    assistant.registry._tools['desktop.open_app'] = replace(spec, handler=lambda *a, **k: calls.append(a))
    try:
        turn = assistant.handle(text)
        assert not calls and not turn.results
    finally:
        assistant.close()


def test_real_json_dependencies_consume_actual_output(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    payload = json.loads(json.dumps({'reply': '', 'steps': [
        {'id': 'create', 'tool': 'files.create_folder', 'arguments': {'path': str(tmp_path / 'fixture')}, 'depends_on': []},
        {'id': 'list', 'tool': 'files.list', 'arguments': {'path': {'$ref': 'create.path'}}, 'depends_on': ['create']},
    ]}))
    plan = parse_plan(payload, assistant.registry.names(), 'fixture')
    assistant.router.route = lambda _: plan
    try:
        turn = assistant.handle('fixture', lambda *_: True)
        assert turn.success and len(turn.results) == 2
        assert (tmp_path / 'fixture').is_dir()
        assert turn.task_id
        assert assistant.task_journal.recent()[0]['status'] == 'completed'
    finally:
        assistant.close()


def test_entire_plan_validates_before_first_effect(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    plan = parse_plan({'steps': [
        {'id': 'first', 'tool': 'files.create_folder', 'arguments': {'path': str(tmp_path / 'should-not-exist')}, 'depends_on': []},
        {'id': 'bad', 'tool': 'desktop.set_volume', 'arguments': {'level': True}, 'depends_on': ['first']},
    ]}, assistant.registry.names(), 'fixture')
    assistant.router.route = lambda _: plan
    try:
        turn = assistant.handle('fixture', lambda *_: True)
        assert not turn.success
        assert not (tmp_path / 'should-not-exist').exists()
    finally:
        assistant.close()


def test_forward_or_undeclared_reference_is_rejected():
    with pytest.raises(ValueError):
        parse_plan({'steps': [
            {'id': 'a', 'tool': 'files.list', 'arguments': {'path': {'$ref': 'b.path'}}, 'depends_on': []},
            {'id': 'b', 'tool': 'files.create_folder', 'arguments': {'path': 'x'}, 'depends_on': []},
        ]}, ['files.list', 'files.create_folder'], 'fixture')


def test_required_volume_and_brightness_goal_runs_both_exact_values(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    observed = []
    for tool in ('desktop.set_volume', 'desktop.set_brightness'):
        assistant.registry._tools[tool] = replace(assistant.registry._tools[tool],
            handler=lambda args, token=None, tool=tool: observed.append((tool, args['level'])) or ActionResult(True, 'Fixture verified', {'verified': True}))
    try:
        turn = assistant.handle('set volume to 50 and brightness to 20')
        assert turn.success and observed == [('desktop.set_volume', 50), ('desktop.set_brightness', 20)]
    finally:
        assistant.close()
