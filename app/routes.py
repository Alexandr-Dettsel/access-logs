import json
import os
from collections import deque
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

main_bp = Blueprint("main", __name__)

LOG_MAX = int(os.getenv("LOG_MAX", "10"))
lastN = deque(maxlen=LOG_MAX)
last_access_utc = None


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


@main_bp.route("/", methods=["GET"])
def index():
    global last_access_utc
    last_access_utc = now_utc_iso()
    return jsonify({
        "last_access_utc": last_access_utc,
        "last_N_log_entries": list(lastN),
        "count": len(lastN),
    })


@main_bp.post("/ingest")
def ingest():
    """
    POST /ingest — сюда cron присылает новые строки access.log.
    Ожидаем JSON вида: {"lines": ["{...}", "{...}"], "sent_at_utc":"..."}
    """
    data = request.get_json(force=True, silent=False)
    lines = data.get("lines", [])
    for line in lines:
        line = line.strip()
        if not line:
            continue

        try:
            obj = json.loads(line)
        except Exception:
            obj = {"raw": line}

        obj["_ingested_at_utc"] = now_utc_iso()
        lastN.append(obj)

    return jsonify({"ok": True, "received": len(lines)}), 200
