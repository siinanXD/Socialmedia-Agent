"""SIN-1484: JSON-Logs ohne Secrets und personenbezogene Daten."""

from __future__ import annotations

import io
import json
import logging
import uuid

from socialmedia_worker.logs import get_logger

# Offensichtlich falsche Werte; das JWT wird zusammengesetzt, damit Secret-Scanner nicht anschlagen.
FAKE_TOKEN = "fake-token-123"
FAKE_JWT = ".".join(["eyJ" + "hbGciOiJub25lIn0", "eyJzdWIiOiJ0ZXN0In0", "ZmFrZS1zaWc"])
FAKE_PASSWORT = "nicht-echt-42"
MAIL = "max.mustermann@example.test"


def _logger() -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    return get_logger(f"test-{uuid.uuid4()}", stream), stream


def _lines(stream: io.StringIO) -> list[dict[str, object]]:
    return [json.loads(line) for line in stream.getvalue().splitlines()]


def test_jede_zeile_ist_json_mit_festen_feldern() -> None:
    log, stream = _logger()
    log.info("job_claimed", extra={"job_id": "j1", "creator_id": "c1", "versuch": 2})
    log.warning("ohne_ids")
    erste, zweite = _lines(stream)
    assert set(erste) >= {"ts", "level", "event", "job_id", "creator_id"}
    assert (erste["event"], erste["level"], erste["job_id"], erste["creator_id"]) == (
        "job_claimed",
        "info",
        "j1",
        "c1",
    )
    assert erste["versuch"] == 2
    assert (zweite["job_id"], zweite["creator_id"], zweite["level"]) == (None, None, "warning")


def test_secrets_in_feldern_und_verschachtelt_werden_geschwaerzt() -> None:
    log, stream = _logger()
    log.info(
        "upload",
        extra={
            "token": FAKE_TOKEN,
            "anfrage": {
                "headers": {"Authorization": f"Bearer {FAKE_TOKEN}"},
                "body": {"password": FAKE_PASSWORT, "api_key": FAKE_TOKEN},
            },
            "liste": [{"secret": FAKE_TOKEN}, f"jwt {FAKE_JWT}"],
            "pfad": "/tmp/auftrag/clip.mp4",
        },
    )
    text = stream.getvalue()
    for geheim in (FAKE_TOKEN, FAKE_JWT, FAKE_PASSWORT):
        assert geheim not in text
    zeile = _lines(stream)[0]
    assert zeile["token"] == "[REDACTED]"
    assert zeile["pfad"] == "/tmp/auftrag/clip.mp4"


def test_freitext_jwt_bearer_passwort_und_mail() -> None:
    log, stream = _logger()
    log.error(
        "Anfrage mit Authorization: Bearer %s und %s, password=%s von %s",
        FAKE_TOKEN,
        FAKE_JWT,
        FAKE_PASSWORT,
        MAIL,
    )
    log.info("kontakt", extra={"nutzer": {"email": MAIL}})
    text = stream.getvalue()
    for geheim in (FAKE_TOKEN, FAKE_JWT, FAKE_PASSWORT, MAIL, "mustermann"):
        assert geheim not in text
    assert "m***@***" in text


def test_traceback_ohne_secrets() -> None:
    log, stream = _logger()
    try:
        raise RuntimeError(f"Upload scheiterte: Bearer {FAKE_TOKEN} token={FAKE_TOKEN}")
    except RuntimeError:
        log.exception("upload_fehlgeschlagen", extra={"password": FAKE_PASSWORT})
    zeile = _lines(stream)[0]
    assert "RuntimeError" in str(zeile["error"])
    assert FAKE_TOKEN not in stream.getvalue()
    assert FAKE_PASSWORT not in stream.getvalue()
