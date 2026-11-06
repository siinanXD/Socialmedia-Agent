"""Strukturierte JSON-Logs ohne Secrets und personenbezogene Daten (SIN-1484).

Eine Zeile je Eintrag mit den festen Feldern ``ts``, ``level``, ``event``, ``job_id`` und
``creator_id``; weitere Felder kommen über ``extra``. Geschwärzt wird nach Schlüsselnamen und
festen Mustern, nicht per Werterkennung beliebiger Strings: deterministisch testbar, und lieber
zu viel als zu wenig.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from typing import Any, TextIO

REDACTED = "[REDACTED]"
FIXED = ("ts", "level", "event", "job_id", "creator_id")

_SECRET_KEY = re.compile(
    r"token|secret|passw|authorization|api_?key|(^|[_-])key$|cookie|credential", re.I
)
_BEARER = re.compile(r"\bBearer\s+[^\s\"',;]+", re.I)
_JWT = re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+")
_KEY_VALUE = re.compile(
    r"\b(token|secret|password|passwort|api_?key|authorization)(\s*[=:]\s*)[^\s\"',;&]+", re.I
)
_EMAIL = re.compile(r"\b([\w.+-])[\w.+-]*@[\w-]+(?:\.[\w-]+)+\b")
# Attribute, die jeder LogRecord hat; alles andere kam über ``extra``.
_RECORD_ATTRS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "taskName"}


def scrub(text: str) -> str:
    """Schwärzt Bearer-Tokens, JWTs, ``password=…``-Paare und maskiert E-Mail-Adressen."""
    text = _BEARER.sub(f"Bearer {REDACTED}", text)
    text = _JWT.sub(REDACTED, text)
    text = _KEY_VALUE.sub(rf"\1\2{REDACTED}", text)
    return _EMAIL.sub(r"\1***@***", text)


def redact(value: Any, key: str | None = None) -> Any:
    """Gibt ``value`` ohne Secrets zurück; Felder wie ``token`` werden ganz geschwärzt."""
    if key is not None and _SECRET_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [redact(v) for v in value]
    if value is None or isinstance(value, bool | int | float):
        return value
    return scrub(str(value))


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname.lower(),
            "event": scrub(record.getMessage()),
            "job_id": _id(getattr(record, "job_id", None)),
            "creator_id": _id(getattr(record, "creator_id", None)),
        }
        for name, value in vars(record).items():
            if name not in _RECORD_ATTRS and name not in FIXED:
                entry[name] = redact(value, name)
        if record.exc_info:
            entry["error"] = scrub(self.formatException(record.exc_info))
        return json.dumps(entry, ensure_ascii=False)


def _id(value: object) -> str | None:
    return None if value is None else scrub(str(value))


def get_logger(name: str = "socialmedia_worker", stream: TextIO | None = None) -> logging.Logger:
    """JSON-Logger auf ``stream`` (Standard: stderr); nur der erste Aufruf richtet ihn ein."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(stream or sys.stderr)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
