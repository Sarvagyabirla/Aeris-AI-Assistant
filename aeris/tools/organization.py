"""Single reviewed document batches and conflict-safe Undo using owned transfers."""
import hashlib
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager

from ..core.file_publication import HeldSource
from ..models import ActionResult
from ..schemas import OrganizeFiles, UndoOrganization
from ..state import CancelledError
from .filesystem import _identity

GROUPS = {'.txt': 'Documents', '.md': 'Documents', '.pdf': 'Documents', '.docx': 'Documents',
          '.csv': 'Tables', '.tsv': 'Tables', '.xlsx': 'Tables', '.pptx': 'Presentations'}


class OrganizationTools:
    def __init__(self, files, ledger):
        self.files, self.ledger = files, ledger
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, data TEXT, status TEXT)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.ledger, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, batch_id, effects, status):
        import json
        with self.connect() as db:
            db.execute('INSERT INTO batches VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data,status=excluded.status',
                       (batch_id, json.dumps(effects), status))

    def load(self, batch_id):
        import json
        with self.connect() as db:
            row = db.execute('SELECT data,status FROM batches WHERE id=?', (batch_id,)).fetchone()
        if not row or row[1] not in {'completed', 'partial', 'undone'}:
            raise ValueError('Batch needs manual review or does not exist; uncertain work is never replayed.')
        return json.loads(row[0]), row[1]

    def recent(self):
        with self.connect() as db:
            return db.execute('SELECT id,status FROM batches ORDER BY rowid DESC LIMIT 20').fetchall()

    def snapshot(self, path, token=None):
        path = self.files.guard.resolve(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError('Expected an ordinary local file')
        held = HeldSource(path, move=False)
        try:
            if held.initial.st_size > 10 * 1024 * 1024:
                raise ValueError('Document exceeds 10 MiB batch limit')
            digest, deadline = hashlib.sha256(), time.monotonic() + 10
            while chunk := held.handle.read(256 * 1024):
                if token:
                    token.raise_if_cancelled()
                if time.monotonic() > deadline:
                    raise ValueError('Document hash exceeded ten seconds')
                digest.update(chunk)
            if _identity(path.stat()) != _identity(held.initial):
                raise ValueError('Document changed during review')
            return digest.hexdigest(), list(_identity(held.initial))
        finally:
            held.close()

    def prepare(self, arguments, token=None):
        if os.name != 'nt':
            return ActionResult(False, 'Safe organization uses the Windows owned-file move adapter.', error='windows_only')
        root = self.files.guard.resolve(arguments['path'])
        if not root.is_dir():
            return ActionResult(False, 'Select an existing allowed folder.', error='folder_not_found')
        entries = []
        # Do not enumerate an unlimited directory, follow links or recurse.
        with os.scandir(root) as iterator:
            for index, entry in enumerate(iterator):
                if token:
                    token.raise_if_cancelled()
                if index >= 1000:
                    return ActionResult(False, 'Folder exceeds 1,000 entries; select a smaller batch.', error='batch_limit')
                if entry.is_file(follow_symlinks=False):
                    entries.append(entry.name)
        manifest, total = [], 0
        for name in sorted(entries):
            source = root / name
            if source.suffix.lower() not in GROUPS:
                continue
            try:
                source = self.files.guard.resolve(source)
            except PermissionError:
                continue
            digest, identity = self.snapshot(source, token)
            destination = self.files.guard.resolve(root / GROUPS[source.suffix.lower()] / name)
            if destination.exists():
                return ActionResult(False, 'A destination collision exists. Review names before organizing; nothing moved.', error='already_exists')
            total += identity[2]
            if len(manifest) >= 100 or total > 50 * 1024 * 1024:
                return ActionResult(False, 'Batch limit: 100 documents and 50 MiB.', error='batch_limit')
            manifest.append({'source': str(source), 'destination': str(destination), 'expected_sha256': digest, 'expected_identity': identity})
        return {'path': str(root), 'batch_id': uuid.uuid4().hex, 'manifest': manifest}

    def validate_manifest(self, manifest, token=None):
        for item in manifest:
            destination = self.files.guard.resolve(item['destination'])
            if destination.exists():
                raise ValueError('Destination exists; Undo never overwrites a newer edit')
            digest, identity = self.snapshot(item['source'], token)
            if digest != item['expected_sha256'] or identity != item['expected_identity']:
                raise ValueError('File changed since review; request a fresh batch')

    def organize(self, arguments, token=None):
        args = OrganizeFiles.model_validate(arguments).model_dump(exclude_none=True)
        if 'manifest' not in args or 'batch_id' not in args:
            return ActionResult(False, 'A locally prepared reviewed manifest is required.', error='missing_preview')
        effects = []
        batch_id = args['batch_id']
        try:
            self.validate_manifest(args['manifest'], token)
            self.save(batch_id, effects, 'running')
            for item in args['manifest']:
                if token:
                    token.raise_if_cancelled()
                result = self.files.move_file(item, token=token)
                effect = dict(result.data, success=result.success, error=result.error)
                if effect.get('published') and effect.get('destination_verified'):
                    path = self.files.guard.resolve(item['destination'])
                    effect['destination_identity'] = list(_identity(path.stat()))
                effects.append(effect)
                self.save(batch_id, effects, 'running')
                if not result.success:
                    break
            complete = len(effects) == len(args['manifest']) and all(item['success'] for item in effects)
            self.save(batch_id, effects, 'completed' if complete else 'partial')
            if token and token.is_cancelled:
                raise CancelledError()
            return ActionResult(complete, f'Organized {sum(item.get("source_removed", False) for item in effects)} documents. Batch {batch_id}; Undo is available in Tasks & routines.',
                {'batch_id': batch_id, 'effects': effects, 'published': bool(effects)}, None if complete else 'partial_batch')
        except CancelledError:
            self.save(batch_id, effects, 'partial')
            return ActionResult(False, f'Organization stopped. Retained effects belong to batch {batch_id}; review before Undo.',
                {'batch_id': batch_id, 'effects': effects, 'published': any(item.get('published') for item in effects)}, 'cancelled')
        except (ValueError, OSError, sqlite3.Error, PermissionError):
            return ActionResult(False, f'Batch {batch_id} could not complete safely. Existing files and reported effects were retained.',
                {'batch_id': batch_id, 'effects': effects, 'uncertain': bool(effects)}, 'batch_conflict')

    def prepare_undo(self, arguments, token=None):
        effects, status = self.load(arguments['batch_id'])
        if status == 'undone':
            return {'batch_id': arguments['batch_id'], 'manifest': []}
        manifest = []
        for item in reversed(effects):
            if item.get('undone'):
                continue
            if not item.get('source_removed') or not item.get('destination_verified') or not item.get('destination_identity'):
                raise ValueError('Uncertain batch effect needs manual review; no automatic Undo')
            manifest.append({'source': item['destination'], 'destination': item['source'],
                             'expected_sha256': item['sha256'], 'expected_identity': item['destination_identity']})
        self.validate_manifest(manifest, token)
        return {'batch_id': arguments['batch_id'], 'manifest': manifest}

    def undo(self, arguments, token=None):
        args = UndoOrganization.model_validate(arguments).model_dump(exclude_none=True)
        if 'manifest' not in args:
            return ActionResult(False, 'A current reviewed Undo manifest is required.', error='missing_preview')
        effects, _ = self.load(args['batch_id'])
        completed = []
        try:
            self.validate_manifest(args.get('manifest', []), token)
            for item in args.get('manifest', []):
                result = self.files.move_file(item, token=token)
                completed.append(result.data)
                if not result.success:
                    return ActionResult(False, 'Undo stopped; completed restores are retained.', {'effects': completed, 'batch_id': args['batch_id']}, result.error)
                for effect in effects:
                    if effect['destination'] == item['source']:
                        effect['undone'] = True
                self.save(args['batch_id'], effects, 'partial')
            self.save(args['batch_id'], effects, 'undone')
            return ActionResult(True, 'Organization undone. Empty category folders were retained.', {'effects': completed, 'batch_id': args['batch_id']})
        except (CancelledError, ValueError, OSError, sqlite3.Error):
            return ActionResult(False, 'Undo stopped or conflicted; no newer file was overwritten.', {'effects': completed, 'batch_id': args['batch_id']}, 'undo_conflict')
