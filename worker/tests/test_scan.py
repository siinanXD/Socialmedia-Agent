"""SIN-1366: Virenscan mit ClamAV als eigenem Prozess, fail-closed; Fake-clamscan im PATH."""

import hashlib
import os
import sys
from pathlib import Path

import pytest

from socialmedia_worker.scan import scan_file

FAKE = """
import os, sys, time
mode = os.environ["FAKE_CLAM_MODE"]
path = sys.argv[-1]
if mode == "clean":
    sys.exit(0)
if mode == "infected":
    print(f"{path}: Eicar-Test-Signature FOUND")
    sys.exit(1)
if mode == "sleep":
    time.sleep(5)
print("ERROR: Can't open file", file=sys.stderr)
sys.exit(2)
"""


@pytest.fixture
def fake_clamscan(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    script = bindir / "fake_clamscan.py"
    script.write_text(FAKE, encoding="utf-8")
    if os.name == "nt":
        (bindir / "clamscan.cmd").write_text(
            f'@"{sys.executable}" "{script}" %*\n', encoding="utf-8"
        )
    else:
        launcher = bindir / "clamscan"
        launcher.write_text(
            f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n', encoding="utf-8"
        )
        launcher.chmod(0o755)
    monkeypatch.setenv("PATH", str(bindir))
    return bindir


@pytest.fixture
def datei(tmp_path: Path) -> Path:
    path = tmp_path / "clip.mp4"
    path.write_bytes(b"\x00\x01harmlos" * 100)
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_sauber(fake_clamscan: Path, datei: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_CLAM_MODE", "clean")
    vorher = _sha(datei)
    ergebnis = scan_file(datei)
    assert (ergebnis.status, ergebnis.signature) == ("clean", None)
    assert _sha(datei) == vorher


def test_befallen_mit_signatur(
    fake_clamscan: Path, datei: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_CLAM_MODE", "infected")
    ergebnis = scan_file(datei)
    assert (ergebnis.status, ergebnis.signature) == ("infected", "Eicar-Test-Signature")


def test_fehler_des_scanners(
    fake_clamscan: Path, datei: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_CLAM_MODE", "error")
    ergebnis = scan_file(datei)
    assert ergebnis.status == "error"
    assert ergebnis.detail is not None and "2" in ergebnis.detail


def test_timeout_ist_fehler_nie_sauber(
    fake_clamscan: Path, datei: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_CLAM_MODE", "sleep")
    ergebnis = scan_file(datei, timeout=1)
    assert ergebnis.status == "error"
    assert ergebnis.detail is not None and "Timeout" in ergebnis.detail


def test_scanner_fehlt(tmp_path: Path, datei: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path / "leer"))
    ergebnis = scan_file(datei)
    assert ergebnis.status == "unavailable"


def test_datei_fehlt_ist_fehler(
    fake_clamscan: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_CLAM_MODE", "clean")
    assert scan_file(tmp_path / "gibt-es-nicht.mp4").status == "error"
