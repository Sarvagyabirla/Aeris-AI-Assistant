"""Bounded task contracts and local metadata receipts; never replay on startup."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from .models import ActionRequest
from .schemas import AerisBaseModel

# Observations remain data and pass consumer schemas and resource/approval policy.
OUTPUT_FIELDS = {
    'files.create_folder': {'path': 'observed-path'},
    'files.write_text': {'path': 'observed-path'},
    'files.copy': {'destination': 'observed-path', 'sha256': '0' * 64},
    'files.move': {'destination': 'observed-path', 'sha256': '0' * 64},
    'downloads.download': {'path': 'observed-path'},
    'browser.advanced_navigate': {'url': 'https://example.invalid/observed'},
    'coding.create_project': {'path': 'observed-path'},
}


class TaskStep(AerisBaseModel):
    id: str = Field(pattern=r'^[a-zA-Z][a-zA-Z0-9_-]{0,39}$')
    tool: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list, max_length=12)


class TaskPlan(AerisBaseModel):
    steps: list[TaskStep] = Field(min_length=1, max_length=12)
    timeout_seconds: int = Field(default=120, ge=1, le=300)

    @model_validator(mode='after')
    def dependencies(self):
        seen = {}
        for step in self.steps:
            if step.id in seen or len(set(step.depends_on)) != len(step.depends_on):
                raise ValueError('Duplicate step or dependency')
            if any(dependency not in seen for dependency in step.depends_on):
                raise ValueError('Dependencies must precede their consumer')
            for value in step.arguments.values():
                if isinstance(value, dict):
                    if set(value) != {'$ref'} or not isinstance(value['$ref'], str):
                        raise ValueError('Only top-level output references are supported')
                    parts = value['$ref'].split('.')
                    if len(parts) != 2 or parts[0] not in step.depends_on:
                        raise ValueError('Output requires an earlier declared dependency')
                    if parts[1] not in OUTPUT_FIELDS.get(seen[parts[0]].tool, {}):
                        raise ValueError('Producer does not declare this output')
            seen[step.id] = step
        return self

    @classmethod
    def from_actions(cls, actions):
        return cls(steps=[TaskStep(id=f'step{index + 1}', tool=action.tool, arguments=action.arguments,
                     depends_on=[f'step{index}'] if index else []) for index, action in enumerate(actions)])

    def preflight(self, registry):
        by_id = {step.id: step for step in self.steps}
        for step in self.steps:
            spec = registry._tools.get(step.tool)
            if spec is None:
                raise ValueError('Unknown task tool')
            arguments = {}
            for key, value in step.arguments.items():
                if isinstance(value, dict):
                    producer, field = value['$ref'].split('.')
                    value = OUTPUT_FIELDS[by_id[producer].tool][field]
                arguments[key] = value
            if any(key not in arguments for key in spec.required_args):
                raise ValueError('Missing task arguments')
            if spec.model:
                spec.model.model_validate(arguments)
            if len(json.dumps(arguments, allow_nan=False).encode()) > 262_144:
                raise ValueError('Task arguments exceed the size budget')

    def resolve(self, step, results, source_text):
        arguments = {}
        for key, value in step.arguments.items():
            if isinstance(value, dict):
                producer, field = value['$ref'].split('.')
                result = results.get(producer)
                if result is None or not result.success or result.dry_run or field not in result.data:
                    raise ValueError('Required live output is unavailable; no value guessed')
                value = result.data[field]
                if not isinstance(value, str) or not value or len(value) > 8192:
                    raise ValueError('Observed output has an invalid type or size')
            arguments[key] = value
        return ActionRequest(step.tool, arguments, source_text)


class TaskJournal:
    """No bodies, goal text, screenshots, arguments or credentials in this ledger."""
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, started REAL, status TEXT, steps TEXT)')
            if 'owner_pid' not in {row[1] for row in db.execute('PRAGMA table_info(tasks)')}:
                db.execute('ALTER TABLE tasks ADD COLUMN owner_pid INTEGER')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2)
        try:
            with db:
                yield db
        finally:
            db.close()

    def begin(self, plan):
        task_id = uuid.uuid4().hex
        steps = [{'id': step.id, 'tool': step.tool, 'status': 'pending'} for step in plan.steps]
        with self.connect() as db:
            db.execute('INSERT INTO tasks (id,started,status,steps,owner_pid) VALUES (?,?,?,?,?)', (task_id, time.time(), 'running', json.dumps(steps), os.getpid()))
            db.execute('DELETE FROM tasks WHERE id NOT IN (SELECT id FROM tasks ORDER BY started DESC LIMIT 200)')
        return task_id, steps

    def update(self, task_id, steps, status='running'):
        with self.connect() as db:
            db.execute('UPDATE tasks SET status=?, steps=? WHERE id=?', (status, json.dumps(steps), task_id))

    def recent(self):
        with self.connect() as db:
            rows = db.execute('SELECT id,started,status,steps,owner_pid FROM tasks ORDER BY started DESC LIMIT 20').fetchall()
        records = []
        for row in rows:
            status = row[2]
            if status == 'running' and row[4] != os.getpid():
                try:
                    import psutil
                    status = 'running' if row[4] and psutil.pid_exists(row[4]) else 'interrupted'
                except ImportError:
                    status = 'review_required'
            records.append({'id': row[0], 'started': row[1], 'status': status, 'steps': json.loads(row[3])})
        return records
