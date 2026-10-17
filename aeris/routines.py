"""Explicitly reviewed, bounded local workflows; no inferred recording or macros."""
import hashlib
import json
import re
import sqlite3
import uuid
from contextlib import contextmanager

from .tasks import TaskPlan

ROUTINE_TOOLS = {'desktop.open_app', 'desktop.set_volume', 'desktop.change_volume', 'desktop.set_brightness',
                 'desktop.change_brightness', 'desktop.media_control', 'system.health', 'system.battery',
                 'system.status', 'files.open_folder', 'files.open', 'reminder.set', 'reminder.list'}


def scope_fingerprint(config):
    scope = {'paths': sorted(str(path) for path in config.allowed_paths), 'downloads': str(config.download_dir),
             'apps': str(config.app_catalog_file), 'live': not config.dry_run, 'timezone': config.timezone_name}
    for name, path in [('catalog_hash', config.app_catalog_file), ('revocations_hash', config.data_dir / 'access-revocations.json'), ('capabilities_hash', config.data_dir / 'access-profile.json')]:
        if path.exists():
            if path.stat().st_size > 1024 * 1024:
                raise ValueError('Scope metadata exceeds the review limit')
            scope[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()


class RoutineStore:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS routines (id TEXT PRIMARY KEY, name TEXT UNIQUE, plan TEXT, scope TEXT, enabled INTEGER, last_status TEXT)')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()

    def save_reviewed(self, name, plan, scope):
        if not re.fullmatch(r'[\w -]{1,80}', name) or any(step.tool not in ROUTINE_TOOLS for step in plan.steps):
            raise ValueError('Routine name or operation is unsupported')
        # Always clone and validate; the caller cannot mutate the reviewed object.
        plan = TaskPlan.model_validate_json(plan.model_dump_json())
        name = name.strip().casefold()
        with self.connect() as db:
            db.execute('INSERT INTO routines VALUES (?,?,?,?,1,NULL) ON CONFLICT(name) DO UPDATE SET plan=excluded.plan,scope=excluded.scope,enabled=1,last_status=NULL',
                       (uuid.uuid4().hex, name, plan.model_dump_json(), scope))

    def get(self, name, scope):
        with self.connect() as db:
            row = db.execute('SELECT plan,scope,enabled FROM routines WHERE name=?', (name.strip().casefold(),)).fetchone()
        if not row or not row[2]:
            raise ValueError('This routine is absent or disabled. Review it in Tasks & routines.')
        if row[1] != scope:
            raise ValueError('Routine scope or live mode changed. Explicitly review and save it again before running.')
        plan = TaskPlan.model_validate_json(row[0])
        if any(step.tool not in ROUTINE_TOOLS for step in plan.steps):
            raise ValueError('Routine contains an unsupported operation')
        return plan

    def records(self):
        with self.connect() as db:
            return db.execute('SELECT name,enabled,last_status,plan FROM routines ORDER BY name').fetchall()

    def disable(self, name):
        with self.connect() as db:
            db.execute('UPDATE routines SET enabled=0 WHERE name=?', (name,))

    def result(self, name, status):
        with self.connect() as db:
            db.execute('UPDATE routines SET last_status=? WHERE name=?', (status, name.strip().casefold()))
