from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import appdb

V2_DB_REVISION = "2026-08-23-v2.1.1"
V2_BASE_SEED_KEY = "kid_v2_base_seed"
V2_EXPANSION_KEY = "kid_v2_expansion_revision"


def _v2_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        path = Path(base) / "KID Diagnostic V2"
    else:
        path = Path.home() / ".kid_diagnostic_v2"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_connect() -> sqlite3.Connection:
    path = Path(appdb.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=60.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA foreign_keys=ON")
    try:
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError:
        # A concurrent reader may momentarily prevent changing journal mode.
        # busy_timeout still protects normal reads/writes.
        pass
    try:
        con.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass
    return con


def _retry_locked(fn, *, timeout: float = 60.0, on_retry=None):
    deadline = time.monotonic() + timeout
    last_exc = None
    while time.monotonic() < deadline:
        try:
            return fn()
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
            last_exc = exc
            if on_retry is not None:
                on_retry()
            time.sleep(0.25)
    if last_exc:
        raise last_exc
    raise TimeoutError("Operația SQLite nu s-a putut finaliza în intervalul permis.")


def _setting(con: sqlite3.Connection, key: str) -> str:
    try:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return str(row[0]) if row else ""
    except sqlite3.OperationalError as exc:
        # Before SCHEMA is created the settings table can legitimately be absent.
        # Lock/busy errors must propagate so the retry layer can actually retry;
        # swallowing them could incorrectly trigger a second seed pass.
        if "no such table" in str(exc).lower():
            return ""
        raise


def _set_setting(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def _rollback_quietly(con: sqlite3.Connection) -> None:
    try:
        con.rollback()
    except sqlite3.Error:
        pass


def _initialize_seed_transaction(con: sqlite3.Connection) -> None:
    """Run the base seed atomically from the caller's point of view.

    If SQLite reports a transient lock after some seed statements already ran,
    rollback before retrying. Without that rollback a retry could observe its own
    partial transaction (for example COUNT(*) > 0) and accidentally commit an
    incomplete catalog.
    """
    try:
        appdb.seed(con)
        _set_setting(con, V2_BASE_SEED_KEY, "1")
        con.commit()
    except Exception:
        _rollback_quietly(con)
        raise


def configure_database_runtime() -> Path:
    """Give KID Diagnostic V2 its own DB and make appdb.connect_db lock-safe."""
    data_dir = _v2_data_dir()
    appdb.APP_DATA = data_dir
    appdb.DB_PATH = data_dir / "kid_diagnostic_v2.db"
    appdb.LOGO_PATH = data_dir / "custom_logo.png"

    if getattr(appdb, "_kid_v2_connect_patched", False):
        return appdb.DB_PATH

    def connect_db():
        con = _safe_connect()

        def initialize_schema():
            try:
                con.executescript(appdb.SCHEMA)
                con.commit()
            except Exception:
                _rollback_quietly(con)
                raise

        _retry_locked(initialize_schema, on_retry=lambda: _rollback_quietly(con))

        base_seed = _retry_locked(
            lambda: _setting(con, V2_BASE_SEED_KEY),
            on_retry=lambda: _rollback_quietly(con),
        )
        if base_seed != "1":
            _retry_locked(
                lambda: _initialize_seed_transaction(con),
                on_retry=lambda: _rollback_quietly(con),
            )
        return con

    appdb.connect_db = connect_db
    appdb._kid_v2_connect_patched = True
    return appdb.DB_PATH


@contextmanager
def database_init_guard(timeout: float = 90.0):
    """Cross-process initialization guard for the V2 expansion database."""
    lock_path = _v2_data_dir() / "database-init.lock"
    handle = open(lock_path, "a+b")
    acquired = False
    deadline = time.monotonic() + timeout
    try:
        if os.name == "nt":
            import msvcrt

            if lock_path.stat().st_size == 0:
                handle.write(b"0")
                handle.flush()
            while time.monotonic() < deadline:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    acquired = True
                    break
                except OSError:
                    time.sleep(0.25)
        else:
            import fcntl

            while time.monotonic() < deadline:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except OSError:
                    time.sleep(0.25)

        if not acquired:
            raise RuntimeError(
                "Baza KID Diagnostic V2 este inițializată de o altă instanță. "
                "Închide cealaltă instanță și pornește din nou aplicația."
            )
        yield
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def expansion_is_current(con: sqlite3.Connection) -> bool:
    return _retry_locked(
        lambda: _setting(con, V2_EXPANSION_KEY),
        on_retry=lambda: _rollback_quietly(con),
    ) == V2_DB_REVISION


def mark_expansion_current(con: sqlite3.Connection) -> None:
    try:
        _set_setting(con, V2_EXPANSION_KEY, V2_DB_REVISION)
        con.commit()
    except Exception:
        _rollback_quietly(con)
        raise
