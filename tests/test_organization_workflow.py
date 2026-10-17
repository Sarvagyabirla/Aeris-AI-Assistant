import os

import pytest
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest
from aeris.state import CancellationToken

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Organization uses Windows owned-file moves; portable rejection is tested separately')


def test_single_reviewed_batch_and_undo_without_overwrite(tmp_path):
    source = tmp_path / 'fixture-downloads'
    source.mkdir()
    (source / 'a.txt').write_text('alpha')
    (source / 'b.csv').write_text('b,2')
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    approvals = []
    try:
        turn = assistant.handle(f'organize documents in {source}', lambda request, *_: approvals.append(request) or True)
        assert turn.success and len(approvals) == 1
        assert (source / 'Documents/a.txt').read_text() == 'alpha'
        assert (source / 'Tables/b.csv').read_text() == 'b,2'
        batch_id = turn.results[0].data['batch_id']
        (source / 'a.txt').write_text('newer edit')
        result = assistant.registry.execute(ActionRequest('files.undo_organization', {'batch_id': batch_id}), lambda *_: True)
        assert not result.success and (source / 'a.txt').read_text() == 'newer edit'
        assert (source / 'Documents/a.txt').read_text() == 'alpha'
        (source / 'a.txt').unlink()
        result = assistant.registry.execute(ActionRequest('files.undo_organization', {'batch_id': batch_id}), lambda *_: True)
        assert result.success and (source / 'a.txt').read_text() == 'alpha'
    finally:
        assistant.close()


def test_changed_batch_bytes_or_denial_prevents_all_moves(tmp_path):
    source = tmp_path / 'fixture'
    source.mkdir()
    path = source / 'a.txt'
    path.write_text('original')
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    try:
        def mutate(*_):
            path.write_text('changed')
            return True
        turn = assistant.handle(f'organize documents in {source}', mutate)
        assert not turn.success and path.read_text() == 'changed'
        assert not (source / 'Documents/a.txt').exists()
        turn = assistant.handle(f'organize documents in {source}', lambda *_: False)
        assert not turn.success and path.read_text() == 'changed'
    finally:
        assistant.close()


def test_stop_during_batch_retains_effect_manifest(tmp_path):
    source = tmp_path / 'fixture'
    source.mkdir()
    (source / 'a.txt').write_text('alpha')
    (source / 'b.txt').write_text('beta')
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    token = CancellationToken()
    original = assistant._files.move_file
    def move(args, token=None):
        result = original(args, token=token)
        token.cancel()
        return result
    assistant._files.move_file = move
    try:
        turn = assistant.handle(f'organize documents in {source}', lambda *_: True, token)
        assert turn.status == 'cancelled'
        assert turn.results[0].data['effects'][0]['published']
        assert (source / 'b.txt').exists()
        assert turn.results[0].data['batch_id']
    finally:
        assistant.close()
