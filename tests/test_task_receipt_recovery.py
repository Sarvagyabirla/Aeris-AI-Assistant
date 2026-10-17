import os

from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest
from aeris.tasks import TaskJournal, TaskPlan


def test_journal_failure_does_not_hide_published_file(tmp_path, monkeypatch):
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    monkeypatch.setattr(assistant.task_journal, 'update', lambda *a, **k: (_ for _ in ()).throw(OSError('fixture storage unavailable')))
    try:
        turn = assistant.handle('create note receipt.txt saying retained bytes', lambda *_: True)
        assert turn.results[0].success and turn.results[0].data['path']
        assert 'history could not' in turn.reply
        assert (tmp_path / 'receipt.txt').exists()
    finally:
        assistant.close()


def test_restart_retains_interrupted_receipts_without_replaying(tmp_path):
    path = tmp_path / 'tasks.db'
    journal = TaskJournal(path)
    plan = TaskPlan.from_actions([ActionRequest('files.write_text', {'path': 'fixture.txt', 'text': 'never persist this body'})])
    task_id, steps = journal.begin(plan)
    steps[0].update(status='executing', published=True, receipt={'path': 'fixture.txt'})
    journal.update(task_id, steps)
    with journal.connect() as db:
        db.execute('UPDATE tasks SET owner_pid=?', (99999999,))
    restarted = TaskJournal(path)
    record = restarted.recent()[0]
    assert record['status'] in {'interrupted', 'review_required'}
    assert record['steps'][0]['receipt']['path'] == 'fixture.txt'
    assert not (tmp_path / 'fixture.txt').exists()
    assert b'never persist this body' not in path.read_bytes()
    # New connections are explicitly closed, including while objects stay alive.
    if os.name == 'nt':
        path.rename(tmp_path / 'closed-handles.db')
