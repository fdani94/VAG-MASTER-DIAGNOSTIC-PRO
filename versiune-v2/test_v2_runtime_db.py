from __future__ import annotations

import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import v2_runtime_db as runtime


class V2RuntimeDatabaseTests(unittest.TestCase):
    def test_locked_seed_rolls_back_before_retry(self):
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT)")
        calls = {"count": 0}

        def flaky_seed(connection):
            calls["count"] += 1
            # Plain INSERT intentionally catches a missing rollback: the second
            # attempt would fail UNIQUE if the first partial transaction survived.
            connection.execute(
                "INSERT INTO settings(key,value) VALUES('partial_seed_probe','ok')"
            )
            if calls["count"] == 1:
                raise sqlite3.OperationalError("database is locked")

        with patch.object(runtime.appdb, "seed", side_effect=flaky_seed):
            runtime._retry_locked(
                lambda: runtime._initialize_seed_transaction(con),
                timeout=2.0,
                on_retry=lambda: runtime._rollback_quietly(con),
            )

        self.assertEqual(calls["count"], 2)
        self.assertEqual(
            con.execute(
                "SELECT COUNT(*) FROM settings WHERE key='partial_seed_probe'"
            ).fetchone()[0],
            1,
        )
        self.assertEqual(
            con.execute(
                "SELECT value FROM settings WHERE key=?",
                (runtime.V2_BASE_SEED_KEY,),
            ).fetchone()[0],
            "1",
        )
        con.close()

    def test_setting_only_swallows_missing_table(self):
        con = sqlite3.connect(":memory:")
        self.assertEqual(runtime._setting(con, "x"), "")
        con.close()

        class LockedConnection:
            def execute(self, *_args, **_kwargs):
                raise sqlite3.OperationalError("database is locked")

        with self.assertRaises(sqlite3.OperationalError):
            runtime._setting(LockedConnection(), "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
