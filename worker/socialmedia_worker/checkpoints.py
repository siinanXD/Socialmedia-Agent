"""Checkpoints je Pipeline-Schritt für das Leitstand-Cockpit (SIN-1077, SIN-1440).

Jeder Schritt schreibt eine Zeile: lokal als JSONL neben den Artefakten (immer) und, wenn
``SUPABASE_ACCESS_TOKEN`` gesetzt ist, in ``leitstand.checkpoints`` des gemeinsamen
Supabase-Projekts über die Management-API (dieselbe Tabelle liest das Cockpit, dort klickt
Sinan die Freigabe). Nur Standardbibliothek; kein Service-Role-Schlüssel, kein PostgREST.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

Status = Literal["wartet", "aktiv", "blockiert", "fertig", "fehlgeschlagen"]
SCHRITTE = ["Upload", "Highlights", "Videoschnitt", "Qualitätsprüfung", "Freigabe", "Export"]
PROJEKT = "Socialmedia Agent"


ArtefaktArt = Literal["datei", "vorschau", "log", "test"]


@dataclass(frozen=True)
class Artefakt:
    art: ArtefaktArt
    name: str
    url: str


@dataclass(frozen=True)
class Checkpoint:
    auftrag_id: str
    schritt: str
    status: Status
    agent: str
    maschine: str
    werkzeuge: list[str]
    eingabe: str | None = None
    ergebnis: str | None = None
    artefakte: list[Artefakt] = field(default_factory=list)
    fehler: str | None = None
    versuch: int = 1
    entscheidung: str | None = None
    modell: str | None = None  # deterministische Schritte haben kein Modell; nie ein erfundenes

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["zeit"] = datetime.now(UTC).isoformat(timespec="seconds")
        return d


class Reporter(Protocol):
    def auftrag(self, auftrag_id: str, titel: str) -> None: ...
    def checkpoint(self, cp: Checkpoint) -> None: ...
    def freigabe(self, auftrag_id: str) -> str | None:
        """'freigegeben', 'abgelehnt' oder None, wenn noch niemand entschieden hat."""
        ...


class JsonlReporter:
    """Eine Zeile je Checkpoint in ``checkpoints.jsonl``; die Freigabe liest dieselbe Datei."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def auftrag(self, auftrag_id: str, titel: str) -> None:
        self._write({"auftrag": auftrag_id, "titel": titel, "schritte": SCHRITTE})

    def checkpoint(self, cp: Checkpoint) -> None:
        self._write(cp.to_dict())

    def freigabe(self, auftrag_id: str) -> str | None:
        if not self.path.exists():
            return None
        antwort: str | None = None
        for line in self.path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row.get("auftrag_id") == auftrag_id and row.get("schritt") == "Freigabe":
                if row.get("status") == "fertig":
                    antwort = "freigegeben"
                elif row.get("status") == "fehlgeschlagen":
                    antwort = "abgelehnt"
                elif row.get("status") == "blockiert":
                    antwort = None
        return antwort

    def _write(self, row: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _lit(s: str | None) -> str:
    if s is None:
        return "null"
    if "\0" in s:
        raise ValueError("NUL im Text")
    return "'" + s.replace("'", "''") + "'"


def _text_array(xs: list[str]) -> str:
    return "array[" + ",".join(_lit(x) for x in xs) + "]::text[]" if xs else "'{}'::text[]"


def insert_sql(cp: Checkpoint) -> str:
    """Eine Insert-Anweisung; die Management-API kennt keine Parameter, deshalb Literale."""
    werte = [
        _lit(cp.auftrag_id), _lit(cp.schritt), _lit(cp.status), _lit(cp.agent), _lit(cp.modell),
        _lit(cp.maschine), _text_array(cp.werkzeuge), _lit(cp.eingabe), _lit(cp.ergebnis),
        _lit(json.dumps([asdict(a) for a in cp.artefakte], ensure_ascii=False)) + "::jsonb",
        _lit(cp.fehler), str(max(1, cp.versuch)), _lit(cp.entscheidung),
    ]  # fmt: skip
    return (
        "insert into leitstand.checkpoints (auftrag_id, schritt, status, agent, modell, maschine,"
        " werkzeuge, eingabe, ergebnis, artefakte, fehler, versuch, entscheidung) values ("
        + ", ".join(werte)
        + ")"
    )


def auftrag_sql(auftrag_id: str, titel: str) -> str:
    return (
        "insert into leitstand.auftraege (id, titel, art, projekt, schritte) values ("
        f"{_lit(auftrag_id)}, {_lit(titel[:200])}, 'produkt', {_lit(PROJEKT)}, "
        f"{_text_array(SCHRITTE)})"
        " on conflict (id) do nothing"
    )


class SupabaseReporter:
    """Schreibt nach ``leitstand.*`` über ``POST /v1/projects/<ref>/database/query``."""

    def __init__(self, token: str, ref: str, timeout: float = 20.0) -> None:
        self.url = f"https://api.supabase.com/v1/projects/{ref}/database/query"
        self.token = token
        self.timeout = timeout

    def sql(self, query: str) -> list[dict[str, object]]:
        req = urllib.request.Request(
            self.url,
            data=json.dumps({"query": query}).encode(),
            headers={"authorization": f"Bearer {self.token}", "content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310
                body = json.loads(r.read().decode() or "[]")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Supabase: HTTP {e.code} {e.read()[:200]!r}") from e
        return body if isinstance(body, list) else []

    def auftrag(self, auftrag_id: str, titel: str) -> None:
        self.sql(auftrag_sql(auftrag_id, titel))

    def checkpoint(self, cp: Checkpoint) -> None:
        self.sql(insert_sql(cp))

    def freigabe(self, auftrag_id: str) -> str | None:
        rows = self.sql(
            "select status from leitstand.checkpoints where auftrag_id = "
            f"{_lit(auftrag_id)} and schritt = 'Freigabe' order by zeit desc, id desc limit 1"
        )
        if not rows:
            return None
        status = rows[0].get("status")
        return {"fertig": "freigegeben", "fehlgeschlagen": "abgelehnt"}.get(str(status))


class MultiReporter:
    """JSONL immer, Supabase zusätzlich; die Freigabe gilt aus Supabase, sonst aus der Datei."""

    def __init__(self, reporters: list[Reporter]) -> None:
        self.reporters = reporters

    def auftrag(self, auftrag_id: str, titel: str) -> None:
        for r in self.reporters:
            r.auftrag(auftrag_id, titel)

    def checkpoint(self, cp: Checkpoint) -> None:
        for r in self.reporters:
            r.checkpoint(cp)

    def freigabe(self, auftrag_id: str) -> str | None:
        for r in reversed(self.reporters):
            antwort = r.freigabe(auftrag_id)
            if antwort is not None:
                return antwort
        return None


def reporter_aus_umgebung(out: Path, env: dict[str, str] | None = None) -> MultiReporter:
    """JSONL neben den Artefakten; Supabase nur mit ``SUPABASE_ACCESS_TOKEN`` (Infisical)."""
    env = dict(os.environ if env is None else env)
    reporters: list[Reporter] = [JsonlReporter(out / "checkpoints.jsonl")]
    token = env.get("SUPABASE_ACCESS_TOKEN")
    if token:
        reporters.append(
            SupabaseReporter(token, env.get("SUPABASE_PROJECT_REF", "zxielkiwgcgxyudqemjb"))
        )
    return MultiReporter(reporters)
