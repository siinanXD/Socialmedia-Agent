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
| Export | wartet auf Freigabe (Exit 3 ohne Entscheidung, belegt im Test) |

Lokal am PC: `uv run pytest` 84 Tests grün in 39 s, davon `test_pipeline.py` 5 Tests (Determinismus der Analyse, Originale byteidentisch, Export nur nach Freigabe, Exit-Codes).

## Nicht bewiesen

Reichweite oder Qualität der Auswahl an echtem Material (Heuristik nicht kalibriert), Untertitel, Caption, Karussell, Upload über die App, Virenscan, Queue. Sinans Freigabe und der Export-Schritt stehen aus, bis er im Cockpit klickt.

## Lauf mit echtem Material (02.11.2026)
Eigene Aufnahmen von Sinan, Rechte laut Sinan ok: 2 Videos (19,5 s und 14,1 s, 720x1280) und 6 Fotos, am PC verarbeitet, Originale bleiben dort. Auftrag `pxul-post-2026-11-02-b`.

| Wert | Ergebnis |
| --- | --- |
| Laufzeit | 30 s für beide Posts |
| Posts | 2, je 27,0 s, 1080x1920, 11 Bausteine (5 Clips, 6 Fotos), rund 33 MB |
| Lautheit | -14,3 LUFS je Post |

Vorläufer im Cockpit: `pxul-echt-2026-11-02` und `-b` lieferten Einzelclips und sind vom Agenten zurückgezogen. `pxul-post-2026-11-02` scheiterte an der Prüfung (-16,2 LUFS bei einstufigem `loudnorm`), daraus entstand das Messen und Anpassen.

Nicht bewiesen: Ob der Schnitt gut wirkt, entscheidet Sinan bei der Freigabe. Die Auswahl bewertet nur Bewegung, Wackeln zählt mit. Keine Trainingsclips, kein Trend-Tempo.
