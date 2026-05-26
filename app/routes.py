import json
import os
from collections import deque
from datetime import datetime, timezone

from flask import Blueprint, jsonify, render_template, request

import urllib.request

main_bp = Blueprint("main", __name__)

LOG_MAX = int(os.getenv("LOG_MAX", "10"))
lastN = deque(maxlen=LOG_MAX)
last_access_utc = None

# простой кеш гео: ip -> {"country":"...", "city":"..."}
GEO_CACHE = {}


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def lookup_geo(ip):
    if not ip or ip in ("-", "127.0.0.1", "::1"):
        return {"country": "", "city": ""}

    if ip in GEO_CACHE:
        return GEO_CACHE[ip]

    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,country,city"
        with urllib.request.urlopen(url, timeout=2) as resp:
            raw = resp.read()
            try:
                obj = json.loads(raw)
            except Exception:
                obj = {}
        if obj.get("status") == "success":
            res = {"country": obj.get("country") or "", "city": obj.get("city") or ""}
        else:
            res = {"country": "", "city": ""}
    except Exception:
        res = {"country": "", "city": ""}

    GEO_CACHE[ip] = res
    return res


@main_bp.route("/", methods=["GET"])
def index():
    return render_template("index.html", title="Логи подключений")


@main_bp.get("/logs")
def logs():
    global last_access_utc
    last_access_utc = now_utc_iso()
    entries = list(lastN)

    # не модифицируем исходные объекты, отдаём копии с полем geo
    annotated = []
    for e in entries:
        copy = dict(e)
        ip = copy.get("remote_addr") or copy.get("remote") or ""
        copy["geo"] = lookup_geo(ip)
        annotated.append(copy)

    return jsonify({
        "last_access_utc": last_access_utc,
        "last_N_log_entries": annotated,
        "last_10_log_entries": annotated,
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
