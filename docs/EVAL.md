# Auswertung: automatische Highlights gegen menschliche Markierungen (SIN-1375)

Stand 09.11.2026: Das Werkzeug ist gebaut und an erfundenen Zahlen getestet. **Eine Messung an echtem Material gibt es noch nicht**; dieses Dokument enthält deshalb keine Messwerte. Reale Labels liefert Sinan mit SIN-1417.

## Vorgehen

1. Datei analysieren: `uv run python -m socialmedia_worker analyze clip.mp4 --asset-id clip-1 --out analysis.json`
2. Ein Mensch markiert im selben Video die Stellen, die er als Highlight nehmen würde, und schreibt sie nach `labels.json` (Format unten). Wichtig: zuerst markieren, dann erst die automatischen Highlights ansehen, sonst färbt das Ergebnis ab.
3. Auswerten: `uv run python -m socialmedia_worker evaluate --labels labels.json --analysis analysis.json` gibt den Bericht als JSON aus, mit `--markdown` als Tabelle. `--iou 0.5` stellt die Trefferschwelle ein. Exit 2 bei abgelehnter Eingabe.

## Format `labels.v1.json`

Schema: `worker/schemas/labels.v1.json`. Beispiel mit erfundenen Zeiten: `worker/tests/data/labels.beispiel.json`.

```json
{
  "version": 1,
  "asset_id": "clip-1",
  "labels": [
    { "start": 12.0, "end": 19.5, "note": "optional: warum" }
  ]
}
```

Zeiten sind Sekunden ab Dateianfang. `asset_id` muss dieselbe sein wie bei `analyze`. Eine Datei je Video.

## Kennzahlen

| Feld | Bedeutung |
| --- | --- |
| `hits` | Highlights, die ein Label mit IoU ≥ `iou_min` treffen (Standard 0,5). IoU = Überlappung geteilt durch Vereinigung der beiden Zeitbereiche. Jedes Label zählt höchstens einmal; Highlights werden nach `confidence` zugeordnet. |
| `false_positives` | Highlights ohne passendes Label (Fehltreffer). |
| `missed` | Labels ohne passendes Highlight. |
| `precision` | `hits / highlights`; `null`, wenn es keine Highlights gibt. |
| `recall` | `hits / labels`; `null`, wenn es keine Labels gibt. |
| `raw_seconds`, `review_seconds`, `saved_seconds` | Dauer des Rohmaterials, Dauer der Highlights, die ein Mensch noch ansehen muss, und die Differenz. |
| `warning` | `"zu klein für Aussagen"` bei weniger als 10 Labels. |

## Grenzen

- `saved_seconds` sagt nur, wie viel weniger Material anzusehen ist. Ob die richtigen Stellen dabei sind, sagt `recall`.
- Ein Bericht gilt für eine Datei und eine Pipeline-Version (`pipeline_version` steht im Bericht). Mehrere Dateien werden nicht zusammengezählt.
- Ein Label ist die Meinung eines Menschen. Mit weniger als 10 Labels, oder Labels von nur einer Person, trägt das Ergebnis keine Aussage über die Qualität der Auswahl.
- Reichweite oder Wirkung misst das nicht.
