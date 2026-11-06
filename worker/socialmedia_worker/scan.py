"""Virenscan einer Quelldatei mit ClamAV als eigenem Prozess (SIN-1366).

Fail-closed: Nur Exit-Code 0 von ``clamscan`` ergibt ``clean``. Fehlt der Scanner, ist das
Ergebnis ``unavailable``; Timeout, fehlende Datei oder jeder andere Exit-Code ergeben ``error``.
Die Datei wird nur gelesen. Die Status entsprechen ``social_media.asset_checks.status``.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ScanStatus = Literal["clean", "infected", "error", "unavailable"]


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    signature: str | None = None
    detail: str | None = None


def scan_file(path: Path, *, scanner: str = "clamscan", timeout: float = 300) -> ScanResult:
    """Scannt ``path`` mit ``clamscan`` oder ``clamdscan`` (Exit 0 sauber, 1 Fund, 2 Fehler)."""
    if not path.is_file():
        return ScanResult("error", detail="Datei fehlt")
    exe = shutil.which(scanner)
    if exe is None:
        return ScanResult("unavailable", detail=f"{scanner} nicht gefunden")
    try:
        proc = subprocess.run(
            [exe, "--no-summary", "--stdout", "--", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ScanResult("error", detail=f"Timeout nach {timeout:g} s")
    except OSError as err:
        return ScanResult("unavailable", detail=f"{scanner} nicht startbar: {err.strerror}")
    if proc.returncode == 0:
        return ScanResult("clean")
    if proc.returncode == 1:
        return ScanResult("infected", signature=_signature(proc.stdout))
    return ScanResult("error", detail=f"{scanner} Exit {proc.returncode}")


def _signature(stdout: str) -> str | None:
    # Ausgabe je Fund: "<pfad>: <Signatur> FOUND"
    for line in stdout.splitlines():
        if line.endswith(" FOUND"):
            return line.removesuffix(" FOUND").rsplit(": ", 1)[-1]
    return None
