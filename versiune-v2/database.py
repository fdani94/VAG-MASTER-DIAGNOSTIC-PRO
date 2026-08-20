from __future__ import annotations

import gzip
import hashlib
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

from localization import romanianize


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def _database_is_usable(path: Path) -> bool:
    """Verifică snapshotul înainte ca aplicația să îl folosească."""
    try:
        if not path.is_file() or path.stat().st_size < 1_000_000:
            return False
        with path.open("rb") as stream:
            if stream.read(16) != b"SQLite format 3\x00":
                return False
        connection = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        try:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            dtc_count = connection.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0]
            metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        finally:
            connection.close()
        return (
            integrity == "ok"
            and dtc_count >= 9500
            and metadata.get("language") == "ro"
            and metadata.get("synthetic_data") == "false"
        )
    except (OSError, sqlite3.Error, TypeError):
        return False


def _default_cache_directory() -> Path:
    if sys.platform == "win32":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return root / "KID-VAG-MASTER-Diagnostic-PRO"


def materialize_database_archive(archive: Path, cache_directory: Path) -> Path:
    """Extrage atomic arhiva de încredere într-un cache persistent."""
    with archive.open("rb") as stream:
        fingerprint = hashlib.file_digest(stream, "sha256").hexdigest()[:16]
    cache_directory.mkdir(parents=True, exist_ok=True)
    target = cache_directory / f"vag_master_v2-{fingerprint}.db"
    if _database_is_usable(target):
        return target

    descriptor, temporary_name = tempfile.mkstemp(
        prefix="vag_master_v2-", suffix=".building.db", dir=cache_directory
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        with gzip.open(archive, "rb") as source, temporary.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
        if not _database_is_usable(temporary):
            raise RuntimeError("Snapshotul SQLite extras nu trece verificarea de integritate.")
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def materialize_default_database(cache_directory: Path | None = None) -> Path:
    """Returnează baza inclusă sau extrage snapshotul comprimat la prima pornire."""
    database = resource_path("assets/vag_master_v2.db")
    if database.exists():
        return database

    archive = resource_path("assets/vag_master_v2.db.gz")
    if not archive.exists():
        raise RuntimeError(
            "Baza profesională lipsește. Rulați scripts/build_database.py înainte de pornire "
            "sau de reconstruirea aplicației Windows."
        )

    primary_cache = cache_directory or _default_cache_directory()
    try:
        return materialize_database_archive(archive, primary_cache)
    except OSError:
        if cache_directory is not None:
            raise
        fallback = Path(tempfile.gettempdir()) / "KID-VAG-MASTER-Diagnostic-PRO"
        return materialize_database_archive(archive, fallback)


def _value(row: sqlite3.Row | None, key: str, default=""):
    if row is None or key not in row.keys() or row[key] in (None, ""):
        return default
    return row[key]


def _split_text(value: str, fallback: tuple[str, ...] = ()) -> tuple[str, ...]:
    text = (value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"(?<!^)(?=\d+[.)]\s+)", "\n", text)
    parts = []
    for value in re.split(r"\r?\n|\s*;\s*", text):
        cleaned = re.sub(r"^\s*\d+[.)]\s*", "", value).strip(" -\t")
        if cleaned:
            parts.append(cleaned)
    return tuple(romanianize(p) for p in parts) or fallback


class KnowledgeBase:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else materialize_default_database()
        if not self.path.exists():
            raise RuntimeError(
                "Baza profesională lipsește. Rulați scripts/build_database.py înainte de pornire sau de reconstruirea aplicației Windows."
            )
        self.connection = sqlite3.connect(
            f"{self.path.resolve().as_uri()}?mode=ro", uri=True
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA query_only=ON")

    def close(self) -> None:
        self.connection.close()

    def stats(self) -> dict[str, int]:
        tables = {
            "mărci": "brands",
            "modele": "models",
            "generații": "generations",
            "motoare": "engines",
            "asocieri vehicul-motor": "vehicle_engines",
            "module": "modules",
            "proceduri": "procedure_library",
            "aplicabilități": "vehicle_procedures",
            "DTC": "dtcs",
            "surse": "sources",
        }
        result: dict[str, int] = {}
        for label, table in tables.items():
            result[label] = int(self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return result

    @staticmethod
    def normalize_code(code: str) -> str:
        raw = (code or "").strip().upper()
        match = re.search(r"\b([PBCU][0-9A-F]{4})", raw)
        if match:
            return match.group(1)
        numeric = re.search(r"\b(\d{5,6})\b", raw)
        if numeric:
            value = numeric.group(1)
            return value[1:] if len(value) == 6 and value.startswith("0") else value
        return raw

    def lookup_dtc(self, code: str) -> sqlite3.Row | None:
        normalized = self.normalize_code(code)
        if not normalized:
            return None
        return self.connection.execute(
            """SELECT d.*, s.title source_title, s.url source_url
               FROM dtcs d LEFT JOIN sources s ON s.id=d.source_id
               WHERE UPPER(d.code)=? LIMIT 1""",
            (normalized.upper(),),
        ).fetchone()

    def search_dtcs(self, query: str = "", limit: int = 300) -> list[sqlite3.Row]:
        needle = (query or "").strip()
        if needle:
            pattern = f"%{needle}%"
            return self.connection.execute(
                """SELECT d.*, s.title source_title, s.url source_url
                   FROM dtcs d LEFT JOIN sources s ON s.id=d.source_id
                   WHERE d.code LIKE ? COLLATE NOCASE OR d.title LIKE ? COLLATE NOCASE
                         OR d.title_ro LIKE ? COLLATE NOCASE OR d.description LIKE ? COLLATE NOCASE
                   ORDER BY d.verified DESC,
                            (length(coalesce(d.diagnosis,''))+length(coalesce(d.repair,''))) DESC,
                            d.code LIMIT ?""",
                (pattern, pattern, pattern, pattern, limit),
            ).fetchall()
        return self.connection.execute(
            """SELECT d.*, s.title source_title, s.url source_url
               FROM dtcs d LEFT JOIN sources s ON s.id=d.source_id
               ORDER BY d.verified DESC,
                        (length(coalesce(d.diagnosis,''))+length(coalesce(d.repair,''))) DESC,
                        d.code LIMIT ?""",
            (limit,),
        ).fetchall()

    def guided_procedures(self, kind: str) -> list:
        from data import GuidedProcedure

        rows = self.connection.execute(
            """SELECT p.*, s.title source_title, s.url source_url
               FROM procedure_library p LEFT JOIN sources s ON s.id=p.source_id
               ORDER BY p.category, p.title"""
        ).fetchall()
        key = kind.casefold()
        patterns = {
            "coding": ("coding", "codare", "activări", "long coding"),
            "adaptation": ("adapt", "basic setting", "setări de bază", "calibr", "învăț"),
            "service": ("service", "reset", "mentenan", "dpf", "bater", "epb", "frână de parcare"),
        }[key]
        result: list[GuidedProcedure] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            haystack = " ".join(
                str(_value(row, field))
                for field in ("title", "category", "purpose", "vcds_path")
            ).casefold()
            if not any(pattern in haystack for pattern in patterns):
                continue
            unique = (str(_value(row, "title")), str(_value(row, "module_address")))
            if unique in seen:
                continue
            seen.add(unique)
            result.append(
                GuidedProcedure(
                    title=romanianize(str(_value(row, "title", "Procedură VCDS"))),
                    category=romanianize(str(_value(row, "category", "Procedură"))),
                    module=romanianize(str(_value(row, "module_address", "Dependent de vehicul"))),
                    platform=romanianize(str(_value(row, "applicability_rule", "Condițional"))),
                    duration="Durată dependentă de vehicul",
                    description=romanianize(str(_value(row, "purpose", "Procedură ghidată VCDS."))),
                    prerequisites=_split_text(
                        str(_value(row, "prerequisites")),
                        ("Auto-Scan original salvat", "Tensiune stabilă", "Unitatea identificată exact"),
                    ),
                    steps=_split_text(
                        str(_value(row, "steps")),
                        (romanianize(str(_value(row, "vcds_path", "Urmați calea VCDS indicată"))),),
                    ),
                    verification=_split_text(
                        str(_value(row, "success_criteria")),
                        ("Procedura este acceptată și nu apar erori noi",),
                    ),
                    safety=romanianize(
                        str(_value(row, "warnings", "Nu aplicați valori de la alt vehicul sau alt număr de piesă."))
                    ),
                    vcds_path=romanianize(str(_value(row, "vcds_path"))),
                    source_title=romanianize(str(_value(row, "source_title"))),
                    source_url=str(_value(row, "source_url")),
                    verified=bool(_value(row, "verified", 0)),
                )
            )
        return result


_DATABASE: KnowledgeBase | None = None


def get_database() -> KnowledgeBase:
    global _DATABASE
    if _DATABASE is None:
        _DATABASE = KnowledgeBase()
    return _DATABASE
