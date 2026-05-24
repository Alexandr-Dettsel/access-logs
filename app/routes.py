import json
import os
from collections import deque
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request

main_bp = Blueprint("main", __name__)

LOG_MAX = int(os.getenv("LOG_MAX", "10"))
lastN = deque(maxlen=LOG_MAX)
last_access_utc = None


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


@main_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html", title="Логи подключений")


@main_bp.get("/logs")
def logs():
    global last_access_utc
    last_access_utc = now_utc_iso()
    entries = list(lastN)
    return jsonify({
        "last_access_utc": last_access_utc,
        "last_N_log_entries": entries,
        "last_10_log_entries": entries,  # алиас (тот же список) — чтобы не ломать старые клиенты
        "count": len(lastN),
    })


@main_bp.post("/ingest")
def ingest():
    data = request.get_json(force=True, silent=False) or {}
    lines = data.get("lines", [])

    received = 0
    for line in lines:
        line = (line or "").strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except Exception:
            obj = {"raw": line}

        obj["_ingested_at_utc"] = now_utc_iso()
        lastN.append(obj)
        received += 1

    return jsonify({"ok": True, "received": received}), 200
