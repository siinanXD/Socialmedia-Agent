# Ende-zu-Ende-Beweis der Pilot-Pipeline (SIN-1364, 02.11.2026)

Echter Lauf auf dem Hetzner-Server `t3` (1 vCPU, 927 MB RAM, ffmpeg 8.0.1, Python 3.14), Branch `claude/sin-1364-pilot-durchlauf`, synthetisches Material (kein Creator-Video; SIN-1417 liefert das echte). Checkpoints gingen nach Supabase `leitstand.checkpoints` (Auftrag `pilot-2026-11-02`), Artefakte liegen unter `~/leitstand-artefakte/pilot-2026-11-02/` und sind im Leitstand-Cockpit unter `/ablauf/pilot-2026-11-02` anklickbar.

## Befehle

```
cd ~/repos/Socialmedia-Agent-pilot/worker
python3 -m socialmedia_worker beispiel ~/leitstand-artefakte/material-synthetisch
export SUPABASE_ACCESS_TOKEN=$(infisical secrets get SUPABASE_ACCESS_TOKEN --plain --silent --projectId=… --env=dev --path=/leitstand)
/usr/bin/time -v python3 -m socialmedia_worker batch ~/leitstand-artefakte/material-synthetisch/clip-a.mp4 \
  ~/leitstand-artefakte/material-synthetisch/clip-b.mp4 ~/leitstand-artefakte/material-synthetisch/foto.png \
  --out ~/leitstand-artefakte/pilot-2026-11-02 --auftrag pilot-2026-11-02 --titel "Pilot PXUL WRLD: synthetisches Material, 2 Varianten 9:16"
# nach Sinans Freigabe im Cockpit:
python3 -m socialmedia_worker export --out ~/leitstand-artefakte/pilot-2026-11-02 --auftrag pilot-2026-11-02
```

## Gemessen (Server, 02.11.2026 14:32 UTC)

| Wert | Ergebnis |
|---|---|
| Eingaben | clip-a.mp4 1,37 MB (12 s, 3 Szenen), clip-b.mp4 1,72 MB (8 s, 2 Szenen), foto.png 152 KB |
| Wandzeit gesamt | 24,5 s (Upload 0,2 s, Highlights 6,8 s, Videoschnitt 15,9 s, Prüfung 0,4 s) |
| Speicher | 527 MB max. RSS (`/usr/bin/time -v`) |
| Highlights | 5 Kandidaten, Heuristik Bewegung je Szene (Confidence 0,13 und 0,13 für die gewählten) |
| Varianten | variante-1.mp4 872 KB (clip-a 0,0–4,0 s), variante-2.mp4 3,08 MB (clip-b 0,0–4,0 s), je 1080×1920 H.264/AAC, Cover 49 KB und 185 KB |
| Qualitätsprüfung | beide ok: 1080x1920, 4,0 s, Cover ok (`pruefung.json`) |
| Checkpoints | Upload, Highlights, Videoschnitt, Qualitätsprüfung `fertig`; Freigabe `blockiert` (IDs 1–5 in Supabase) |
| Export | 4 Dateien unter `export/` plus `export.json`, Checkpoint 7 `fertig` (15:01 UTC); ohne Entscheidung Exit 3, gesehen am 02.11. auf dem Server |

Lokal am PC: `uv run pytest` 84 Tests grün in 39 s, davon `test_pipeline.py` 5 Tests (Determinismus der Analyse, Originale byteidentisch, Export nur nach Freigabe, Exit-Codes).

## Nicht bewiesen

Reichweite oder Qualität der Auswahl an echtem Material (Heuristik nicht kalibriert), Untertitel, Caption, Karussell, Upload über die App, Virenscan, Queue. Die Freigabe dieses Laufs kam nicht per Klick zustande: Sinans Klick scheiterte an einem Cockpit-Fehler (`Origin: null`, 403; behoben in siinanXD/leitstand-2 PR 73), der Agent trug sie nach Sinans Aussage im Chat per curl nach (Checkpoint 6). Der Knopf selbst ist danach an einem Probelauf im Browser belegt, nicht an diesem Lauf.
