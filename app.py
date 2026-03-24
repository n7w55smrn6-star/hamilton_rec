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

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "programs.json"

REFRESH_HOURS = 6

# ---------------------------------------------------------------------------
# Background refresh loop
# ---------------------------------------------------------------------------

def refresh_loop():
    time.sleep(5)  # allow server to boot
    while True:
        log.info("[Scheduler] Scraping Hamilton rec programs…")
        try:
            programs = scrape_all()
            save_data(programs)
            log.info("[Scheduler] Done — %d programs saved.", len(programs))
        except Exception as exc:
            log.error("[Scheduler] Scrape error: %s", exc)
        time.sleep(REFRESH_HOURS * 3600)

# Start scheduler only after first request (prevents Gunicorn double-start)
@app.before_first_request
def start_scheduler():
    @app.before_first_request
def start_scheduler():
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
# Local dev
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=8080)
