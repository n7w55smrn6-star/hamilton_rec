"""
app.py — Hamilton Rec Programs
Flask web app, deployable to Render.com.

Serves the dashboard and JSON data.
Runs the scraper on startup and every REFRESH_HOURS hours in a background thread.
"""

import json
import logging
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, Response

from scraper import scrape_all, save as save_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)

DATA_FILE     = Path(__file__).parent / "data" / "programs.json"
REFRESH_HOURS = 6

# ---------------------------------------------------------------------------
# Background refresh thread
# ---------------------------------------------------------------------------

def refresh_loop():
    while True:
        log.info("[Scheduler] Scraping Hamilton rec programs…")
        try:
            programs = scrape_all()
            save_data(programs)
            log.info("[Scheduler] Done — %d programs saved.", len(programs))
        except Exception as exc:
            log.error("[Scheduler] Scrape error: %s", exc)
        time.sleep(REFRESH_HOURS * 3600)

# Start background thread once on startup
threading.Thread(target=refresh_loop, daemon=True).start()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/data/programs.json")
def programs_json():
    if DATA_FILE.exists():
        return Response(DATA_FILE.read_text(), mimetype="application/json")
    return jsonify({"last_updated": None, "count": 0, "programs": []})


@app.route("/refresh")
def manual_refresh():
    def _run():
        try:
            programs = scrape_all()
            save_data(programs)
            log.info("[Manual Refresh] Done — %d programs.", len(programs))
        except Exception as exc:
            log.error("[Manual Refresh] Error: %s", exc)
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "refresh started"})


# ---------------------------------------------------------------------------
# Entry point (local dev)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8080)
