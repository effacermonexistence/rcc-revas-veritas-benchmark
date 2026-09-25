"""Durable at-most-one attempt reservation, including across process restarts.

A reservation is never deleted or retried automatically. Crashes require native
reconciliation, not a second call. SQLite guards local concurrent workers only;
use a transactionally equivalent native store for distributed runners.
"""
from pathlib import Path
import sqlite3
from contextlib import closing
from rveval.guardrails import require

class OperationLedger:
    def __init__(self, path):
        require(not Path(path).is_symlink(), 'OPERATION_LEDGER_SYMLINK')
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('PRAGMA synchronous=FULL')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (operation_id TEXT PRIMARY KEY, state TEXT NOT NULL)')
    def reserve(self, operation_id):
        require(type(operation_id) is str and bool(operation_id), 'OPERATION_ID_REQUIRED')
        try:
            with closing(sqlite3.connect(self.path, timeout=5)) as db, db:
                db.execute('PRAGMA synchronous=FULL')
                db.execute('INSERT INTO attempts VALUES (?, ?)', (operation_id, 'RESERVED_DO_NOT_AUTORETRY'))
        except sqlite3.IntegrityError:
            require(False, 'OPERATION_ALREADY_RESERVED_IN_LEDGER')
