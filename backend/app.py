"""
Flask + Vue Web System for WeChat Protocol Login

Backend (Flask):
- Serves a JSON API for the Vue frontend
- Proxies requests to the WeChat protocol server (mgr port + per-instance port)
- Persists RDV -> WXID mappings on disk (scoped by server:mgr_port)

API endpoints (all under /api, JSON only):
    POST /api/login                          - {server, mgr_port, username, password}
    POST /api/logout
    GET  /api/session                        - returns current server / mgr_port / logged_in
    POST /api/check_port                     - {StartPort} -> Get_PortOccupiedInfo          (mgr 端口 29999)
    POST /api/start_object_process           - {StartPort} -> StartObjectProcess            (mgr 端口 29999)
    POST /api/start_wechat                   - {port, RDV, CallBackURL, Proxy_*} -> instance:port/StartWechat
    POST /api/get_qrcode                     - {port, session_id} -> instance:port/getloginqrcode
    POST /api/check_qrcode                   - {port, session_id, uuid} -> instance:port/checkloginqrcode
    POST /api/push_login_url                 - {port, session_id, wxid} -> instance:port/pushloginurl
    POST /api/get_object_process_number      - mgr:port/Get_ObjectProcessNumber (lists running protocols)
    POST /api/get_session_list               - {port, key, not_started_after_seconds} -> instance:port/GetSessionList
    POST /api/get_profile                    - {port, session_id} -> instance:port/getprofile
    POST /api/newsendmsg                     - {port, session_id, userName, content, msgType} -> instance:port/newsendmsg
    GET  /api/get_rdv_mapping
    POST /api/save_rdv_mapping
    POST /api/delete_rdv_mapping
"""

import os
import re
import json
import time
import threading
import requests
from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production-please")

# In dev, the Vue dev server runs on http://localhost (port 80)
CORS(app, supports_credentials=True, origins=[
    "http://localhost:80",
    "http://127.0.0.1:80",
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
])

# ─────────────────────────────── config ───────────────────────────────
MGR_PORT_DEFAULT = 29999
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAPPING_FILE = os.path.join(BASE_DIR, "rdv_wxid_mapping.json")


# ─────────────────────────── rdv/wxid storage ────────────────────────
def load_mapping():
    if not os.path.exists(MAPPING_FILE):
        return {"version": 2, "scopes": {}}
    try:
        with open(MAPPING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": 2, "scopes": {}}


def save_mapping(data):
    try:
        with open(MAPPING_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"save_mapping error: {e}")


def scope_key():
    server_ip = (session.get("server_ip") or "").strip()
    mgr_port = str(session.get("mgr_port") or MGR_PORT_DEFAULT).strip()
    return f"{server_ip}:{mgr_port}"


def current_scope_mapping():
    data = load_mapping()
    return dict(data.get("scopes", {}).get(scope_key(), {}))


def upsert_mapping(rdv, wxid, port="", proxy=None):
    data = load_mapping()
    scopes = data.setdefault("scopes", {})
    scoped = scopes.setdefault(scope_key(), {})
    scoped[rdv] = {
        "wxid": wxid,
        "port": str(port or ""),
        "proxy": proxy if isinstance(proxy, dict) else {},
    }
    save_mapping(data)
    return dict(scoped)


def delete_mapping(rdv):
    data = load_mapping()
    scopes = data.setdefault("scopes", {})
    scoped = scopes.setdefault(scope_key(), {})
    scoped.pop(rdv, None)
    save_mapping(data)
    return dict(scoped)


# ─────────────────────────── helpers ─────────────────────────────────
def mgr_url(path):
    server_ip = session.get("server_ip", "")
    mgr_port = session.get("mgr_port", MGR_PORT_DEFAULT)
    return f"http://{server_ip}:{mgr_port}{path}"


def inst_url(port, path):
    server_ip = session.get("server_ip", "")
    return f"http://{server_ip}:{port}{path}"


def require_login():
    if not session.get("logged_in"):
        return jsonify({"error": "请先登录"}), 401
    return None


def safe_post(url, payload, timeout=15):
    """POST with JSON body, return (ok, json_or_text, status_code)."""
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        try:
            return True, r.json(), r.status_code
        except ValueError:
            return True, {"text": r.text, "status_code": r.status_code}, r.status_code
    except Exception as e:
        return False, {"error": str(e)}, 500


# ─────────────────────────── auth ────────────────────────────────────
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    server = (data.get("server") or "").strip()
    mgr_port = data.get("mgr_port", MGR_PORT_DEFAULT)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    try:
        mgr_port_int = int(mgr_port)
        if mgr_port_int < 1 or mgr_port_int > 65535:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "端口必须是 1-65535 的数字"}), 400

    if username != ADMIN_USER or password != ADMIN_PASS:
        return jsonify({"error": "用户名或密码错误"}), 401

    session.clear()
    session["logged_in"] = True
    session["server_ip"] = server
    session["mgr_port"] = mgr_port_int
    return jsonify({"success": True, "server": server, "mgr_port": mgr_port_int})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"success": True})


@app.route("/api/session", methods=["GET"])
def api_session():
    return jsonify({
        "logged_in": bool(session.get("logged_in")),
        "server": session.get("server_ip", ""),
        "mgr_port": session.get("mgr_port", MGR_PORT_DEFAULT),
    })


# ─────────────────────────── upstream proxy ──────────────────────────
@app.route("/api/check_port", methods=["POST"])
def api_check_port():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    try:
        port = int(data.get("StartPort"))
    except (TypeError, ValueError):
        return jsonify({"error": "请填写正确的 StartPort"}), 400
    ok, body, code = safe_post(mgr_url("/Get_PortOccupiedInfo"), {"CheckPort": port})
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/start_object_process", methods=["POST"])
def api_start_object_process():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    try:
        port = int(data.get("StartPort"))
    except (TypeError, ValueError):
        return jsonify({"error": "请填写正确的 StartPort"}), 400
    ok, body, code = safe_post(mgr_url("/StartObjectProcess"), {"StartPort": port}, timeout=30)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/start_wechat", methods=["POST"])
def api_start_wechat():
    """
    StartWechat is called on the INSTANCE port (the user-entered port),
    NOT on the mgr port (29999).
    Frontend MUST pass {"port": <instance_port>, ...}.
    """
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    # /StartWechat 跑在实例端口（用户在页面填的），不是 mgr 端口
    port = data.get("port")
    if not port:
        return jsonify({"error": "请提供实例端口 (port) - /StartWechat 走用户输入的端口，不是 29999"}), 400
    payload = {
        "RDV": data.get("RDV", ""),
        "CallBackURL": data.get("CallBackURL", ""),
        "Proxy_Type": data.get("Proxy_Type", ""),
        "Proxy_IP": data.get("Proxy_IP", ""),
        "Proxy_Port": data.get("Proxy_Port", ""),
        "Proxy_Usr": data.get("Proxy_Usr", ""),
        "Proxy_Pwd": data.get("Proxy_Pwd", ""),
    }
    ok, body, code = safe_post(inst_url(port, "/StartWechat"), payload, timeout=30)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/get_qrcode", methods=["POST"])
def api_get_qrcode():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    port = data.get("port")
    session_id = data.get("session_id", "")
    if not port:
        return jsonify({"error": "请提供 port"}), 400
    payload = {"session_id": session_id} if session_id else {}
    ok, body, code = safe_post(inst_url(port, "/getloginqrcode"), payload, timeout=15)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/check_qrcode", methods=["POST"])
def api_check_qrcode():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    port = data.get("port")
    session_id = data.get("session_id", "")
    uuid = data.get("uuid", "")
    if not port:
        return jsonify({"error": "请提供 port"}), 400
    payload = {"session_id": session_id, "uuid": uuid}
    ok, body, code = safe_post(inst_url(port, "/checkloginqrcode"), payload, timeout=10)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/push_login_url", methods=["POST"])
def api_push_login_url():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    port = data.get("port")
    session_id = data.get("session_id", "")
    wxid = data.get("wxid", "")
    if not port:
        return jsonify({"error": "请提供 port"}), 400
    if not wxid:
        return jsonify({"error": "请提供 wxid"}), 400
    payload = {"session_id": session_id, "wxid": wxid}
    ok, body, code = safe_post(inst_url(port, "/pushloginurl"), payload, timeout=15)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


# ─────────────────────────── accounts management ─────────────────────
def _extract_start_port(par):
    """
    The mgr's List[i].Par is a free-form string like 'StartPort=30004'.
    We need the numeric port for downstream calls.
    """
    if not par or not isinstance(par, str):
        return None
    m = re.search(r"StartPort\s*=\s*(\d+)", par, flags=re.IGNORECASE)
    return int(m.group(1)) if m else None


@app.route("/api/get_object_process_number", methods=["POST"])
def api_get_object_process_number():
    """
    Lists every running protocol process from the mgr (port 29999).
    Returns the upstream response verbatim, with a normalized 'port' field
    parsed out of 'Par' (StartPort=30004) for convenience.
    """
    guard = require_login()
    if guard:
        return guard
    ok, body, code = safe_post(mgr_url("/Get_ObjectProcessNumber"), {}, timeout=15)
    if not ok:
        return jsonify(body), 500
    # Normalize: extract StartPort from Par so the frontend doesn't have to.
    try:
        items = body.get("List") or []
        for it in items:
            if isinstance(it, dict) and "port" not in it:
                p = _extract_start_port(it.get("Par"))
                if p is not None:
                    it["port"] = p
    except Exception:
        pass
    return jsonify(body), code


@app.route("/api/get_session_list", methods=["POST"])
def api_get_session_list():
    """
    For a given instance port, list the WeChat sessions running on it
    (online / offline / not_started counts, rdv, start_port, etc).

    The upstream /GetSessionList takes a shared API key plus an optional
    'not_started_after_seconds' threshold; we forward both as-is.
    """
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    port = data.get("port")
    if not port:
        return jsonify({"error": "请提供实例 port"}), 400
    key = (data.get("key") or "").strip()
    if not key:
        return jsonify({"error": "请提供 key (上游 /GetSessionList 的鉴权参数)"}), 400
    payload = {
        "key": key,
        "not_started_after_seconds": data.get("not_started_after_seconds", 300),
    }
    # Coerce to int if possible; fall back to 300 on garbage.
    try:
        n = int(payload["not_started_after_seconds"])
        if n < 0:
            n = 300
        payload["not_started_after_seconds"] = n
    except (TypeError, ValueError):
        payload["not_started_after_seconds"] = 300
    ok, body, code = safe_post(inst_url(port, "/GetSessionList"), payload, timeout=15)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/get_profile", methods=["POST"])
def api_get_profile():
    """
    Pull the WeChat profile for a single session (by session_id) on an
    instance port. Returns nick_name, wxid (user_name), avatar, etc.
    """
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    port = data.get("port")
    session_id = (data.get("session_id") or "").strip()
    if not port:
        return jsonify({"error": "请提供实例 port"}), 400
    if not session_id:
        return jsonify({"error": "请提供 session_id"}), 400
    ok, body, code = safe_post(inst_url(port, "/getprofile"), {"session_id": session_id}, timeout=15)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


@app.route("/api/newsendmsg", methods=["POST"])
def api_newsendmsg():
    """
    Generic test endpoint - send a message via the instance's /newsendmsg.
    Forwarded fields: session_id, userName, content, msgType.
    """
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    port = data.get("port")
    if not port:
        return jsonify({"error": "请提供实例 port"}), 400
    payload = {
        "session_id": data.get("session_id", ""),
        "userName": data.get("userName", ""),
        "content": data.get("content", ""),
        "msgType": data.get("msgType", 1),
    }
    ok, body, code = safe_post(inst_url(port, "/newsendmsg"), payload, timeout=20)
    if not ok:
        return jsonify(body), 500
    return jsonify(body), code


# ─────────────────────────── rdv mapping ─────────────────────────────
@app.route("/api/get_rdv_mapping", methods=["GET"])
def api_get_rdv_mapping():
    guard = require_login()
    if guard:
        return guard
    return jsonify(current_scope_mapping())


@app.route("/api/save_rdv_mapping", methods=["POST"])
def api_save_rdv_mapping():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    rdv = (data.get("rdv") or "").strip()
    wxid = (data.get("wxid") or "").strip()
    port = data.get("port", "")
    proxy = data.get("proxy", {})
    if not rdv or not wxid:
        return jsonify({"error": "RDV 和 wxid 不能为空"}), 400
    mapping = upsert_mapping(rdv, wxid, port, proxy)
    return jsonify({"success": True, "mapping": mapping})


@app.route("/api/delete_rdv_mapping", methods=["POST"])
def api_delete_rdv_mapping():
    guard = require_login()
    if guard:
        return guard
    data = request.get_json(silent=True) or {}
    rdv = (data.get("rdv") or "").strip()
    if not rdv:
        return jsonify({"error": "RDV 不能为空"}), 400
    mapping = delete_mapping(rdv)
    return jsonify({"success": True, "mapping": mapping})


# ─────────────────────────── main ────────────────────────────────────
# Optional: serve the built Vue app from ../frontend/dist
FRONTEND_DIST = os.path.normpath(
    os.path.join(BASE_DIR, "..", "frontend", "dist")
)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    # API requests are handled above; this only runs for non-API paths.
    if path.startswith("api/") or path == "api":
        return jsonify({"error": "not found"}), 404
    if not os.path.isdir(FRONTEND_DIST):
        return (
            "<h3>Frontend not built.</h3>"
            "<p>Run <code>cd frontend && npm install && npm run build</code> first, "
            "or use the dev mode (<code>npm run dev</code> on port 5173).</p>",
            200,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    full = os.path.join(FRONTEND_DIST, path)
    if path and os.path.isfile(full):
        return send_from_directory(FRONTEND_DIST, path)
    index_html = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.isfile(index_html):
        return send_from_directory(FRONTEND_DIST, "index.html")
    return jsonify({"error": "frontend not built"}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
