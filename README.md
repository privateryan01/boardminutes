# CCSD Board Personnel Watch

Local tool for scanning Clark County School District Diligent board meeting personnel attachments against the watched school clusters from the provided screenshots.

## What it does

- Pulls the public Diligent meeting JSON for a meeting URL.
- Extracts personnel-looking agenda attachments such as employment/new hires, promotions/transfers, separations, and staffing reports.
- Downloads the PDFs, extracts text, and caches PDF/text copies for review.
- Matches watched schools from `data/schools.csv`.
- Treats CCSD `Personnel Employment` reference PDFs as `new_hire` sources and includes any watched-school matches in the same report as promotions and separations.
- Dates every finding with both the board meeting date/name/link and the employment effective/start date extracted from the PDF.
- Separates findings by board-meeting calendar year in the dashboard and writes `findings_YYYY.csv` files for each year in a range run.
- Adds a `Trace` link for each finding that points to the official board meeting website first, then shows the extracted and highlighted evidence used for the match.
- Filters the dashboard by watched school cluster while keeping Trace links tied to the original source records.
- Lets users add, edit, and delete watched clusters/schools from the browser at `/schools`.
- Keeps hosted-user preferences private by assigning each browser a `ccsd_watch_user` cookie and storing that browser's school list and scan results in its own data folder.
- Can run as a hosted web app with background auto-refresh, so users on locked-down work computers do not need to install anything.
- Writes `findings.csv`, `findings.json`, `attachments.csv`, cached PDFs, and extracted text under `data/runs/`.
- Serves a small local dashboard for running scans and reviewing findings.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m ccsd_board_watch.cli --meeting-url "https://ccsd.community.diligentoneplatform.com/Portal/MeetingInformation.aspx?Org=Cal&Id=1678"
```

Dashboard:

```bash
.venv/bin/python -m ccsd_board_watch.web
```

Then open `http://127.0.0.1:5057`.

Manage watched schools and clusters:

```text
http://127.0.0.1:5057/schools
```

Scan the previous calendar year plus the current year-to-date:

```bash
.venv/bin/python -m ccsd_board_watch.cli --previous-year
```

Scan a specific date range:

```bash
.venv/bin/python -m ccsd_board_watch.cli --from-date 2025-01-01 --to-date 2026-05-20
```

## Build the Mac app

```bash
./scripts/build_macos_app.sh
```

The app bundle is written to `dist/CCSD Board Personnel Watch.app`. The packaged app opens the dashboard in your browser and stores scans in `~/Library/Application Support/CCSD Board Personnel Watch/runs`. This local build is unsigned; sharing outside your Mac may trigger a Gatekeeper warning until the app is signed and notarized with an Apple Developer ID.

## Host it for no-download access

### Zero-cost browser version with GitHub Pages

The `docs/` folder is a browser-only version of the app. It does not need Flask, Render, a database, or any installed software for viewers. Each user's school and cluster preferences are stored in that person's browser `localStorage`, so editing schools on one computer does not change anyone else's preferences.

The static site works by publishing compact extracted personnel attachment text in `docs/data/board-data.json`. The browser then matches that text against the current user's school list. That is what lets a user replace the default clusters with a completely different list without needing a server.

To publish it at zero cost:

1. Create a public GitHub repository for this folder.
2. Push the project to GitHub.
3. In the repository settings, enable GitHub Pages with `GitHub Actions` as the source.
4. In the Actions tab, run `Update board data` once.
5. Open the Pages URL that GitHub shows after deployment.

The scheduled workflow scans the previous calendar year plus the current year-to-date, exports fresh static data into `docs/data/`, and commits that data back to the repository when CCSD publishes new or changed meeting records.

Build the static data locally:

```bash
PYTHONPATH=src .venv/bin/python -m ccsd_board_watch.cli --previous-year --output-dir .generated/runs
PYTHONPATH=src .venv/bin/python -m ccsd_board_watch.static_export --output-dir .generated/runs --docs-dir docs
```

Preview the static site locally:

```bash
python3 -m http.server 8080 --directory docs
```

Then open `http://127.0.0.1:8080`.

### Server-hosted option

The repo includes `wsgi.py` and `render.yaml` for a hosted web deployment. On Render, use the Blueprint file and attach the included persistent disk at `/var/data`. The hosted app uses:

- `CCSD_WATCH_DATA_DIR=/var/data` for editable schools and scan history.
- `CCSD_AUTO_REFRESH=1` to refresh automatically.
- `CCSD_REFRESH_INTERVAL_MINUTES=360` to check for newly published meetings every six hours.
- `CCSD_REFRESH_ON_START=1` to seed or refresh the hosted app when it starts.

In hosted mode, each browser gets a private profile cookie. School edits and scan outputs are stored under `users/<profile-id>/`, so one user's watched schools do not affect another user's list. Clearing browser cookies creates a new default profile.

The app can also run on any internal server that supports Python:

```bash
pip install -r requirements.txt
CCSD_WATCH_DATA_DIR=/var/data CCSD_AUTO_REFRESH=1 gunicorn "wsgi:app" --bind 0.0.0.0:8000 --workers 1 --threads 4 --timeout 180
```

Keep `--workers 1` when using the built-in background refresh so the scanner does not run in multiple web workers at once.

## Edit watched schools

The screenshots were transcribed into `data/schools.csv`. Add aliases there when a CCSD PDF uses a different abbreviation for a school. The scanner expands common suffixes such as `ES`, `MS`, `JHS`, and `HS`.

## Current limits

The first parser is deterministic and context-based. It catches school hits and nearby person/effective-date/reason fields, then includes the raw context so uncertain rows can be reviewed. A next hardening pass should add document-specific table parsers for each recurring CCSD personnel report layout.
