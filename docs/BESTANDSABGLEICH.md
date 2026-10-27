# Bestandsabgleich (Phase 0a, SIN-1137)

Stand: 27.10.2026. Nur Doku. Jede Aussage nennt Quelle; "belegt" heisst: Datei oder Link gelesen, nicht nur ein Keyword-Treffer. Ein Fund im Code ist kein Nachweis, dass es live laeuft.

## Methode und Grenzen
- Repos: `gh repo list siinanXD`, `git grep` in lokalen Klonen (Content-Agent-Lernapp `origin/main` 847cdb9 frisch geholt; stromlauf-ai, Lifestyle-APP, leitstand-2, Leitstand, SJCODE-website, Mail-agent, AI-Workspace 2799873, gedaechtnis 7bb2d70 ohne Fetch) und `gh search code` (Begriffe ffmpeg, ffprobe, whisper, subtitle, srt, scenedetect, video, reel, tiktok, instagram; danach GitHub-Rate-Limit, `youtube` und `social_media` nur lokal geprueft).
- Nicht geprueft: archivierte private Repos (z. B. `linkedin-agent`, `vision`, `my-automation`), Code ausserhalb von `siinanXD`. Nicht ausgefuehrt: kein Code gestartet, kein Lauf wiederholt.
- Supabase `Content-Agent-Lernapp` (`zxielkiwgcgxyudqemjb`): Schema `social_media` enthaelt keine Tabellen (MCP `list_tables`, 27.10.2026). Nichts angelegt.

## 1. Linear
| Issue | Stand | Gilt fuer dieses Projekt? |
| --- | --- | --- |
| [SIN-834](https://linear.app/sinan-kahraman/issue/SIN-834) | Canceled (21.10.2026) | Nur das Prinzip: erst Bestand pruefen, "gemergt" ist nicht "live". Die Leitstand-Befunde (SIN-827, 615, 638) betreffen das archivierte Repo `siinanXD/Leitstand`, nicht diesen Agenten. |
| [SIN-857](https://linear.app/sinan-kahraman/issue/SIN-857), [858](https://linear.app/sinan-kahraman/issue/SIN-858), [859](https://linear.app/sinan-kahraman/issue/SIN-859), [860](https://linear.app/sinan-kahraman/issue/SIN-860) | alle Canceled (27.10.2026, 12:01) | Nein. Sie bauten einen automatischen Planer-Abgleich im alten Leitstand (`Leitstand` ist archiviert). Ersetzt durch `leitstand-2` und die Pflicht-Vorarbeit in `AGENTS.md`. Der Abgleich passiert hier von Hand, dieses Dokument. |
| [SIN-1127](https://linear.app/sinan-kahraman/issue/SIN-1127) | Todo | Ja, offen: `claude.yml` fuer Cloud-Laeufe bei PC aus. Aenderung unter `.github/`, Sinan merged von Hand. Blockiert diese Phase nicht. |
| [SIN-1077](https://linear.app/sinan-kahraman/issue/SIN-1077) | Backlog (Parent) | Freigabe 27.10.2026 liegt als Kommentar vor; Stack steht in `AGENTS.md`. |
| [SIN-1138](https://linear.app/sinan-kahraman/issue/SIN-1138), [SIN-1139](https://linear.app/sinan-kahraman/issue/SIN-1139) | Todo | Folgearbeit: Upstream-Audit (0b), Worker-Geruest (1a). |
| [SIN-483](https://linear.app/sinan-kahraman/issue/SIN-483), [SIN-485](https://linear.app/sinan-kahraman/issue/SIN-485) | Duplicate (Arbeit in SIN-988/989, 518, 520, 522 Done) | Quelle des vorhandenen Video-Codes, siehe 2. |

Weitere SIN-Issues mit "video" (SIN-906 PR-Crawler, 561 Designer, 550 Marketing-Agent) betreffen Screenshots/Texte der Lern-App, kein Social-Media-Material (Linear-Suche "video", 27.10.2026).

## 2. Code in `siinanXD/*`
Einziger Treffer fuer Video: `siinanXD/Content-Agent-Lernapp` (`origin/main` 847cdb9, Video-Dateien zuletzt geaendert 13.10.2026). Es ist ein Tutorial-Generator fuer die Lern-App (Playwright-Aufnahme, Revideo-Schnitt), kein Schnitt von Rohmaterial. In keinem anderen Repo gibt es FFmpeg, Whisper, Szenenerkennung, Untertitel (SRT/VTT), Upload, Trend- oder Publishing-Code (git grep, siehe Methode). `AI-Workspace` fuehrt Whisper nur als Modellklasse in `AGENT-SYSTEM/model-routing/local-models.yaml:32` und `shared-rules/research-policy.md:108`, ohne Code.

| Fund | Repo / Pfad | Stand | Wiederverwendbar |
| --- | --- | --- | --- |
| FFmpeg-Aufrufe (webm zu mp4 `libx264 yuv420p 30 fps`, `ffprobe` Dauer) | Content-Agent-Lernapp `.github/workflows/video.yml` Zeilen 63, 86, 97 | gemergt ([#295](https://github.com/siinanXD/Content-Agent-Lernapp/pull/295)), laeuft nur im Workflow | Nur als Vorlage fuer die FFmpeg-Probe im Worker (SIN-1139). Einzeiler, kein Modul. |
| Dauerpruefung, Tageslimit, Storage-Pfad, Freigabe-Zeile | `scripts/autonomy/video.mjs` (`pruefeDauer`, `heuteSchonGelaufen`, `storagePfad`, `registrieren`), Tests `src/lib/autonomy/video.test.ts` | gemergt #295 | Muster ja, Code nein: Node-Skript, kein `creator_id`, andere Stack-Seite. |
| Tabelle `werbemittel` + privater Bucket (Status `wartet_auf_freigabe`, RLS ohne Policy) | `supabase/migrations/20261018010000_sin483_werbemittel.sql`, `20261019010000_sin485_werbeclips.sql` | gemergt, im selben Supabase-Projekt | Muster ja (Freigabe-Status, privater Bucket), Tabelle nein: keine Mandantentrennung, gehoert der Lern-App. Eigene Tabellen in `social_media`. |
| Revideo-Schnitt (Overlay-Szene, ffmpeg-Export) | `video/schnitt/` (`render.mjs`, `szene.tsx`, `package.json` `^0.10.4`) | gemergt #326, #327; Typ-Ausschluss #363 | Nein fuer MVP. Rendert programmierte Grafik-Szenen, kein Highlight-Schnitt; braucht Node und Chromium. Lizenz und Pflege laut [SIN-483](https://github.com/siinanXD/Content-Agent-Lernapp/blob/main/docs/decisions/SIN-483-video-agent.md) "nicht geprueft". Entscheidung in SIN-1138. |
| Kosten-Deckel pro Lauf | `docs/decisions/SIN-485-werbeclips-higgsfield.md` (`assertWithinProductCap`, 5 EUR) | gemergt [#320](https://github.com/siinanXD/Content-Agent-Lernapp/pull/320) | Idee ja (Vorpruefung gegen `budget_cap`), Code nein. |
| KI-Werbeclips ueber Higgsfield-API | `scripts/autonomy/werbeclip.mjs`, `.github/workflows/werbeclip.yml`, `docs/autonomy/higgsfield.json` | gemergt [#325](https://github.com/siinanXD/Content-Agent-Lernapp/pull/325); echter Lauf laut Decision-Doc ungeprueft | Nein. Text-zu-Video, bezahlter Dienst; `AGENTS.md` verbietet Kosten ohne Freigabe. |
| Lehren zu Revideo/Handy-Format | `docs/autonomy/LEHREN.md` Zeilen 127-130, `docs/decisions/SIN-522-video-handyformat.md` | Doku | Nur lesen, falls Revideo spaeter geprueft wird. |
| Gedaechtnis-Notiz | `gedaechtnis/Projekte/PXUL-Studio.md` (24.10.2026) | "geplant, nicht implementiert" | Kontext. Nennt noch FastAPI und Repo-Namen `social-media-agent`; ueberholt durch `AGENTS.md` (Stack, 27.10.2026). |

## 3. Pull Requests
- Offen: keiner mit Bezug zu Video oder Social Media (`gh pr list --state open` in Socialmedia-Agent, Content-Agent-Lernapp, stromlauf-ai, Lifestyle-APP, leitstand-2; offen ist nur Lifestyle-APP #3, Datenbank).
- Gemergt, Video: Content-Agent-Lernapp #295, #320, #321, #323, #324, #325, #326, #327, #363 (12.-14.10.2026), Details oben.
- Gemergt, dieses Repo: [#1](https://github.com/siinanXD/Socialmedia-Agent/pull/1) Projektgrundlage, [#3](https://github.com/siinanXD/Socialmedia-Agent/pull/3) CI und Gate (SIN-1150); [#2](https://github.com/siinanXD/Socialmedia-Agent/pull/2) war eine geschlossene Probe.

## Wiederverwendbar
1. FFmpeg-Aufrufe aus `video.yml` als Startpunkt der FFmpeg-Probe (SIN-1139); lizenzfrei, eigener Code.
2. Muster "privater Bucket + Status `wartet_auf_freigabe` + RLS" aus den `werbemittel`-Migrationen, neu gebaut in `social_media` mit `creator_id`.
3. Muster "Kosten-Vorpruefung vor bezahltem Schritt" aus SIN-485 fuer `budget_cap`.
4. Gleiches Supabase-Projekt `zxielkiwgcgxyudqemjb` (Entscheidung SIN-1077); Gate, `build.yml`, Labels aus SIN-1150.
5. Lehren aus `LEHREN.md`, falls Revideo oder Chromium-Rendering ueberhaupt in Frage kommt.

## Fehlt, muss neu gebaut werden
Kein Treffer in `siinanXD/*` (Methode oben), also neu oder aus Upstream (Entscheidung in SIN-1138):
- Mehrfach-Upload, MIME/Groesse, Quota, Dedup, Virenscan, Loeschung (Phase 1).
- Szenenerkennung, Sprach-/ASR-Analyse, Highlight-Auswahl mit Zeitstempel und Begruendung.
- 9:16-Rendering von Rohmaterial, Untertitel-Dateien, Cover, Caption.
- Job-Zustandsmaschine mit Queue, Retry, Abbruch, Idempotenz (`worker/`, Supabase-Queue).
- Mandantenfaehiges Schema `social_media` mit RLS und pgTAP-Tests.
- Trend-/Konkurrenz-Adapter, Audio-Lizenzpruefung, Publishing, Insights (Phasen 2-3).
- Leitstand-Vertrag (signierte Edge Function), Phase 4.
- Upstream-Kandidaten (OpenShorts, Postiz, OpenNolan, ShortGPT, PhotoCraft/FigCraft, Voicebox): ungeprueft, siehe `docs/UPSTREAM_AUDIT.md` und SIN-1138.

## Offene Punkte
- Lokale Klone ausser Content-Agent-Lernapp nicht frisch geholt; GitHub-Codesuche vorzeitig am Limit. Ein Wiederholungslauf nach SIN-1138 ist sinnvoll, falls Upstream-Funde neue Suchbegriffe liefern.
- Die Tabellen `werbemittel` liegen im selben Projekt: Kompatibilitaetspruefung vor Migrationen in `social_media` (`AGENTS.md`, Architektur).
