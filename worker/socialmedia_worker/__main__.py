"""CLI: ``python -m socialmedia_worker {analyze,batch,export,beispiel,evaluate}``.

Exit-Codes: 0 ok, 1 Fehler, 2 Eingabe abgelehnt, 3 keine Freigabe (Export wartet).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from socialmedia_worker.checkpoints import reporter_aus_umgebung
from socialmedia_worker.evaluate import IOU_MIN, evaluate, to_markdown
from socialmedia_worker.pipeline import analyze_asset, beispiel, export_batch, run_batch
from socialmedia_worker.validate import MediaRejectedError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="socialmedia_worker", description=__doc__)
    sub = p.add_subparsers(dest="befehl", required=True)
    a = sub.add_parser(
        "analyze", help="eine Datei analysieren (validate → Szenen → Signale → Highlights)"
    )
    a.add_argument("datei", type=Path)
    a.add_argument("--asset-id", required=True)
    a.add_argument("--out", type=Path, help="Analyse-JSON schreiben statt auf stdout")
    b = sub.add_parser(
        "batch", help="Upload → Highlights → Videoschnitt → Qualitätsprüfung → Freigabe (wartet)"
    )
    b.add_argument("eingaben", type=Path, nargs="+")
    b.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Artefakt-Ordner (im Cockpit: <ARTEFAKTE_DIR>/<auftrag>)",
    )
    b.add_argument("--auftrag", required=True, help="Auftrags-Kennung, z. B. pilot-2026-11-02")
    b.add_argument("--titel", default="Pilot-Lauf Socialmedia-Agent")
    e = sub.add_parser(
        "export", help="nach Freigabe im Cockpit die Varianten nach export/ kopieren"
    )
    e.add_argument("--out", type=Path, required=True)
    e.add_argument("--auftrag", required=True)
    s = sub.add_parser(
        "beispiel", help="synthetisches Testmaterial erzeugen (zwei Clips, ein Bild)"
    )
    s.add_argument("ziel", type=Path)
    v = sub.add_parser(
        "evaluate", help="Highlights einer Analyse gegen menschliche Labels auswerten (SIN-1375)"
    )
    v.add_argument("--labels", type=Path, required=True, help="labels.v1.json")
    v.add_argument("--analysis", type=Path, required=True, help="Ausgabe von analyze")
    v.add_argument("--iou", type=float, default=IOU_MIN, help="Treffer ab dieser Überlappung")
    v.add_argument("--markdown", action="store_true", help="Tabelle statt JSON ausgeben")
    args = p.parse_args(argv)

    if args.befehl == "analyze":
        try:
            text = analyze_asset(args.datei, args.asset_id).to_json()
        except MediaRejectedError as err:
            text = json.dumps({"reason": err.reason, "message": str(err)})
            print(text, file=sys.stderr)
            return 2
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        else:
            print(text)
        return 0
    if args.befehl == "batch":
        reporter = reporter_aus_umgebung(args.out)
        manifest = run_batch(args.eingaben, args.out, args.auftrag, reporter, args.titel)
        print(
            f"{len(manifest['varianten'])} Varianten unter {args.out}; "
            f"wartet auf Freigabe im Cockpit (/ablauf/{args.auftrag})"
        )
        return 0
    if args.befehl == "export":
        ziel = export_batch(args.out, args.auftrag, reporter_aus_umgebung(args.out))
        if ziel is None:
            print("keine Freigabe (oder abgelehnt): nichts exportiert", file=sys.stderr)
            return 3
        print(f"exportiert nach {ziel}")
        return 0
    if args.befehl == "evaluate":
        try:
            report = evaluate(
                json.loads(args.labels.read_text(encoding="utf-8")),
                json.loads(args.analysis.read_text(encoding="utf-8")),
                args.iou,
            )
        except (ValueError, KeyError) as err:  # KeyError: Pflichtfeld fehlt in der Analyse
            print(f"Eingabe abgelehnt: {err}", file=sys.stderr)
            return 2
        # ASCII-JSON: eine Windows-Konsole (cp1252) verstümmelt sonst die Umlaute
        print(to_markdown(report) if args.markdown else json.dumps(report))
        return 0
    for datei in beispiel(args.ziel):
        print(datei)
    return 0


if __name__ == "__main__":
    sys.exit(main())
