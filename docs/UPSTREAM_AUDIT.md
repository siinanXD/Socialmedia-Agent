# Upstream-Audit (Phase 0b, SIN-1138)

Stand: 27.10.2026. Nur Doku und Recherche: keine Abhaengigkeit eingebaut, nichts installiert, kein Upstream-Code ausgefuehrt, keine Kosten. Keine Rechtsberatung (`license-policy.md`). "Ungeprueft" heisst: nicht gelesen oder nicht ausgefuehrt; es ist kein Produktversprechen (`AGENTS.md`).

## Methode
- Metadaten per `gh api repos/<owner>/<repo>` (Lizenz, `pushed_at`, Sterne, offene Issues, Fork-Status), `.../releases/latest`, `.../commits?per_page=1`, `.../security-advisories`, `.../contributors`, abgerufen am 27.10.2026. LICENSE, NOTICE, README und SECURITY.md der Repos gelesen.
- FFmpeg: <https://ffmpeg.org/download.html> und <https://ffmpeg.org/legal.html>. Remotion: <https://raw.githubusercontent.com/remotion-dev/remotion/main/LICENSE.md>. Postiz-API: <https://docs.postiz.com/public-api/introduction>. AGPL: <https://www.gnu.org/licenses/agpl-3.0.en.html>.
- Sterne sind kein Qualitaetsbeleg (`reuse-before-build.md`). Auffaellig: PhotoCraft hat 73.886 Sterne bei Erstellung am 30.09.2026; Ursache ungeprueft.
- Nicht gemacht: kein "runnable proof" (nichts gestartet, siehe Umfang der Issue); GPU-/Kostenangaben stammen aus READMEs, nicht aus Messungen.

## 1. Befund je Kandidat
| Kandidat | Lizenz (Copyleft) | Letzter Commit / Release | API / CLI / MCP | OS | GPU | Kosten | Sicherheitslage | Quelle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OpenShorts | MIT; Ordner `cloud/` unter eigener Commercial License (kein SaaS-Weiterverkauf). Kein Copyleft | Fork `Rind-AI`: 10.09.2026, 1 Stern. Upstream `mutonby`: 27.10.2026, 7.194 Sterne. Keine Releases (rollendes `main`) | REST, MCP (`/mcp`, `mcp_stdio.py`), Webhooks. README-Doku, kein Versionsvertrag | Docker (Windows: Docker Desktop + WSL2) | Optional (NVENC/CUDA); CPU 5-8 min je 8-min-Video | Self-Host 0 EUR, aber Gemini-Key fuer die KI-Funktionen (lokales LLM per `LLM_BASE_URL` moeglich); fal.ai, ElevenLabs, Upload-Post optional bezahlt | 0 Advisories, kein `SECURITY.md` im Root; 8 Contributors; 101 Eintraege in `tests/` (Upstream) | <https://github.com/mutonby/openshorts>, <https://github.com/Rind-AI/openshorts> |
| Postiz | AGPL-3.0 (starkes Copyleft, auch bei Netzbetrieb) | v2.25.3, 24.10.2026; Commit 24.10.2026 | Public API (`/public/v1/posts`, `/upload`, `/integrations`), Node-SDK `@postiz/node`, n8n-Node; MCP im Code (`start.mcp.ts`), in der API-Doku nicht beschrieben | Docker (9 Container, siehe 2.2) | Nein | Self-Host: eigene Server fuer Postgres, Redis, Temporal, Elasticsearch; Cloud-Plaene ungeprueft | **19 veroeffentlichte Advisories**, davon 5 critical, 8 high (2025-07 bis 2026-09, u. a. SSRF, Dateilesen, Auth-Umgehung); 70 Contributors | <https://github.com/gitroomhq/postiz-app>, <https://docs.postiz.com/public-api/introduction> |
| OpenNolan | AGPL-3.0 (Fork von OpenMontage, ebenfalls AGPL-3.0) | v1.0.1, 09.08.2026; Commit 19.08.2026 (v1.0.2 Desktop) | Web-App (FastAPI :8000 + React :5173), Agent-Chat ueber Claude Agent SDK; keine dokumentierte stabile API | Python 3.10+, Node 18+, FFmpeg | Optional (`requirements-gpu.txt`, lokale Videomodelle) | Kostenlos mit Stock-Footage und lokaler TTS; Kling/Veo/Premium-Stimmen bezahlt. Remotion: Company License ab >3 Mitarbeitern | 0 Advisories, kein `SECURITY.md` im Root; 3 Contributors, 13 Sterne | <https://github.com/het8802/OpenNolan> |
| ShortGPT | MIT | v0.3.0 und letzter Commit 10.02.2025 (~20 Monate alt); `stable`-Branch | Gradio-Web-UI, Python-Bibliothek; kein REST, kein MCP | Docker (Port 31415) oder Colab | Nein (torch fuer whisper-timestamped) | OpenAI-Key Pflicht, ElevenLabs optional (bezahlt), EdgeTTS und Pexels kostenlos | 0 Advisories, kein `SECURITY.md` im Root; Abhaengigkeiten fest gepinnt (`openai==1.37.0`, `protobuf==3.20.3`, `gradio==5.12.0`); 85 offene Issues; Repo-Beschreibung nennt es "Experimental" | <https://github.com/RayVentura/ShortGPT> |
| PhotoCraft | MIT oder Apache-2.0 (nach Wahl); Marke/Logo ArtCraft ausgenommen. Kein Copyleft | v0.16.0, 25.10.2026; Commit 27.10.2026 | `photocraft-cli` (run, batch), MCP (`photocraft-cli mcp`), loopback Steuerkanal | Windows, Linux, macOS, FreeBSD (Release-Artefakte) | Ungeprueft | 0 EUR | 0 Advisories, `SECURITY.md` vorhanden; 3.307 offene Issues; README: "early alpha"; 100+ Contributors | <https://github.com/storytold/photocraft> |
| FigCraft | MIT oder Apache-2.0 (nach Wahl); Marke ArtCraft ausgenommen. Kein Copyleft | v0.11.2, 25.10.2026; Commit 27.10.2026 | `figcraft-cli` (render, export, run), MCP (`figcraft-cli mcp`) | Windows, Linux, macOS, FreeBSD | Nein (ungeprueft) | 0 EUR | 0 Advisories, kein `SECURITY.md` im Root; 278 offene Issues; README: "early alpha"; Repo seit 09.10.2026 | <https://github.com/storytold/figcraft> |
| Voicebox | MIT. Kein Copyleft. Lizenzen der einzelnen TTS-/Whisper-Modelle ungeprueft | v0.5.0, 25.04.2026; Commit 07.10.2026 | REST (`POST /speak`, `/transcribe`), MCP (`voicebox_speak`) | Windows (MSI, CUDA/DirectML), macOS; Linux nur aus Quellen | Optional (CUDA, ROCm, MLX, Arc); CPU laeuft langsamer | 0 EUR, lokal | 0 Advisories; `SECURITY.md` nennt nur 0.3.x als unterstuetzt (Release ist 0.5.0, veraltet); `RESPONSIBLE_USE.md` (Stimmklon braucht Einwilligung); 523 offene Issues; 96 Contributors | <https://github.com/jamiepine/voicebox> |

Anmerkungen:
- OpenShorts: `AGENTS.md` verlinkt den Fork `Rind-AI/openshorts`. Der Fork steht seit 10.09.2026; aktiv ist das Original `mutonby/openshorts` (GitHub-API `parent`). Die `cloud/`-Ausnahme habe ich nur im Fork gelesen; ob das Original sie ebenfalls fuehrt (dort `LICENSE` ohne Ausnahme, Ordner `cloud/` vorhanden), ist ungeprueft.
- Postiz und OpenNolan sind beide AGPL-3.0. Rot laut `license-policy.md`: "nicht nebenbei", Entscheidung muss dokumentiert sein (Abschnitt 2).
- Datenschutz, rechtliche Bedingungen der Plattform-APIs (TikTok, Instagram, YouTube) und Daten-Abfluss an Gemini/OpenAI/ElevenLabs: ungeprueft, jeweils erst im Phasen-Issue zu klaeren.

## 2. Entscheidung je Kandidat
| Kandidat | Entscheidung | Begruendung (ein Satz) |
| --- | --- | --- |
| OpenShorts | **Ablehnen** als Abhaengigkeit; MIT-Code (`scene_detection.py`, `reframe_v2.py`, `subtitles.py`) bleibt als Lese-Referenz | Eigener FastAPI-/DB-/Auth-Stack mit Gemini-Key (oder eigenem LLM-Server) umgeht Supabase-RLS, Langfuse-Tracing und Infisical (`AGENTS.md`), und die Pflege liegt bei 8 Contributors ohne Releases. |
| Postiz | **Ablehnen** (jetzt); bei Phase 3 neu bewerten, nur als separater, unveraenderter Dienst | AGPL ist rot, 19 Advisories (5 critical) plus 9 Container Eigenbetrieb passen nicht zu "Manual approval, keine Kosten ohne Freigabe". |
| OpenNolan | **Ablehnen** | AGPL-3.0, 3 Contributors, erzeugt generative Videos aus Stock-Material statt Highlights aus Creator-Material, und Remotion braucht ab 3 Mitarbeitern eine Company License. |
| ShortGPT | **Ablehnen** | Letzter Commit Februar 2025, fest gepinnte veraltete Abhaengigkeiten und OpenAI-Pflicht fuer ein "faceless Shorts"-Konzept, das unser Produkt nicht ist. |
| PhotoCraft | **Ablehnen** (Phase 1); fuer Karussell-Designs spaeter pruefen | "Early alpha" ist keine stabile API (`AGENTS.md`), 3.307 offene Issues; Cover und Karussell lassen sich zuerst mit FFmpeg/Pillow loesen. |
| FigCraft | **Ablehnen** | Ein UI-Design-Werkzeug (Figma-Ersatz) loest keine Aufgabe der Medien-Pipeline, "early alpha". |
| Voicebox | **Wrapper**, erst Phase 2 und optional; jetzt nichts einbauen | MIT, lokal, REST plus MCP, aber Stimmklon verlangt Einwilligung je Stimme und Modelllizenzen sind ungeprueft, also nur hinter Adapter mit Rechtepruefung. |

### 2.1 FFmpeg direkt als Basis
Siehe Abschnitt 3: **uebernehmen** (als Subprozess, nie eingelinkt).

### 2.2 Postiz: AGPL-Pflichten ausdruecklich
- Pflicht (AGPL-3.0 §13): Wer eine **geaenderte** Version betreibt und Nutzern ueber das Netz Zugriff gibt, muss diesen den passenden Quelltext anbieten (<https://www.gnu.org/licenses/agpl-3.0.en.html>). Unveraenderter Betrieb loest §13 nicht aus.
- Trennung: Eigener Code, der Postiz nur ueber dessen Public API aufruft, ist laut Lizenztext kein Teil des Programms, solange nichts eingebunden oder gelinkt wird. Das ist meine Lesart, keine Rechtsberatung; bei Zweifel Anwalt.
- Praktisch: Jeder Patch an Postiz (z. B. fuer Auth-Anbindung an Supabase) machte uns offenlegungspflichtig. Wegen der Advisories (JWT-Umgehung, Pfad-Traversal, SSRF) waeren Patches zu erwarten.
- Betrieb: Compose-Datei fuehrt 9 Container: `postiz`, `postiz-postgres`, `postiz-redis`, `spotlight`, `temporal`, `temporal-elasticsearch`, `temporal-postgresql`, `temporal-admin-tools`, `temporal-ui` (<https://github.com/gitroomhq/postiz-app/blob/main/docker-compose.yaml>). Kosten fuer Hosting: ungeprueft, aber nicht null.
- Rate-Limit der API: 90 Anfragen/Stunde auf `create post` (konfigurierbar, <https://docs.postiz.com/public-api/introduction>).
- Ersatz fuer Phase 3: direkte offizielle Plattform-APIs hinter Adapter, mit Freigabe, Idempotency-Key und Doppelpost-Schutz (`ARCHITECTURE.md`).

## 3. FFmpeg/ffprobe-Baseline
| Punkt | Befund | Quelle |
| --- | --- | --- |
| Aktuelle Version | 9.0.2, 18.09.2026 (Download-Seite nennt zusaetzlich 8.1.3 vom 21.09.2026 auf dem 8.1-Zweig; GitHub-Tag `n9.0.2` ist der neueste Release-Tag) | <https://ffmpeg.org/download.html>, `gh api repos/FFmpeg/FFmpeg/tags` |
| Lizenz | Kern LGPL-2.1 oder neuer; mit `--enable-gpl` (z. B. `libx264`) gilt GPL fuer das ganze Binary; `--enable-nonfree` nicht weitergebbar | <https://ffmpeg.org/legal.html> |
| Wir verteilen FFmpeg nicht | Worker ruft das auf dem Host installierte `ffmpeg`/`ffprobe` als eigenen Prozess auf (`worker/socialmedia_worker/probe.py`). Rot-Regel ("GPL als eigenstaendiges Programm") greift nicht, solange wir weder linken noch ein Image mit FFmpeg ausliefern | `license-policy.md` |
| Falls spaeter ausgeliefert (Docker-Image fuer den Worker) | GPL-Build bringt die Pflicht, Quelltext samt Configure-Zeile bereitzustellen. LGPL-Build ohne `libx264` waere schlanker, dann `libopenh264` o. ae. oder Hardware-Encoder. Entscheidung dann in einem eigenen Issue | <https://ffmpeg.org/legal.html> |
| CI-Version | Job `build` installiert `ffmpeg` per apt auf ubuntu-24.04 (`.github/workflows/build.yml:54`). Welche Version und ob GPL-Build: ungeprueft, Log der letzten Laeufe enthielt keine Zeile dazu; `ffmpeg -version` in CI ausgeben, sobald Rendering beginnt | `.github/workflows/build.yml` |
| Lokal | `ffmpeg` auf diesem Entwicklungsrechner nicht installiert (PATH-Pruefung 27.10.2026); `README.md` nennt es als Voraussetzung | `where.exe ffmpeg` |
| Patente | Projekt gibt keine Patentaussage ab; fuer H.264 koennen bei kommerzieller Verteilung Gebuehren anfallen. Bei reinem Serverbetrieb: ungeprueft | <https://ffmpeg.org/legal.html> |
| Fuer den MVP ausreichend? | Ja fuer `probe`, Schnitt, 9:16-Crop/Scale, Untertitel (ASS/SRT per `subtitles`/`drawtext`), Cover (`-frames:v 1`). Nicht enthalten: Szenenerkennung mit Ranking, ASR, Gesichtsverfolgung | Phase-1-Liste in `ROADMAP.md` |
| Entscheidung | **Uebernehmen** als Subprozess hinter eigenem Adapter. Szenenerkennung (PySceneDetect), ASR (faster-whisper) und Gesichts-Reframing als getrennte, versionierte Adapter in eigenen Issues pruefen; ihre Lizenzen sind hier **ungeprueft** | `ARCHITECTURE.md` |

## 4. Offener Punkt aus SIN-1137: Revideo
Das Lern-App-Repo nutzt Revideo (`BESTANDSABGLEICH.md`, Abschnitt 2). Revideo: MIT, letzter Commit 15.07.2026, keine Releases, 4.149 Sterne (<https://github.com/redotvideo/revideo>, 27.10.2026). Rendert programmierte Szenen mit Node und Chromium, kein Highlight-Schnitt. **Ablehnen** fuer die Medien-Pipeline (falsche Aufgabe, zweiter Stack neben Python/FFmpeg). Remotion (OpenNolan nutzt es): Company-License-Pflicht ab >3 Mitarbeitern, deshalb ebenfalls nicht als Baustein vorgesehen (<https://raw.githubusercontent.com/remotion-dev/remotion/main/LICENSE.md>).

## 5. Folgen
- Phase 1 baut auf FFmpeg/ffprobe plus Eigenbau im `worker/`. Keine der sieben Kandidaten-Abhaengigkeiten wird Teil von `package.json` oder `pyproject.toml`.
- `ARCHITECTURE.md`, "Optional adapters": Liste auf Voicebox (Phase 2, optional) kuerzen.
- Wiedervorlage: Postiz (Phase 3, nur wenn Advisory-Lage und Betriebskosten tragbar), PhotoCraft (Karussells, wenn aus "early alpha" heraus), Voicebox (Phase 2).
- Alle Aussagen ohne Quelle in diesem Dokument sind als "ungeprueft" markiert.
