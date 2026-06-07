from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.network.connection.tcpabridged import ConnectionTcpAbridged
from telethon.tl.types import MessageEntityPre, MessageEntityCode
import asyncio
import threading
import re
import json
import logging
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps

API_ID = 35240692
API_HASH = "8e95febf3563b0da51e9cbb72640c541"

STRING_SESSION = "1BVtsOKwBu1L6AWnsFbVYAc-ZnzDao-BdE6PYtKSAV56iqrCi_IGVSs4lawVgOVtoVWRZWkye2o816OyaTZL2hDZ3iCNhExpu3F8eubacjxiWPVGQo2-5PDq_Jw7UcZbyGTVjFfCW4jlWrs5k_EG5zdVyPh0L-MYwmZCCXM-pnwtoOmdjmw7SsB-Gr2117b4Yd5bNUyv9Cat4robcra7XbS-rNgzCNdT-7IbHrADsHrgH60NjLp9qP9TfFRh4ITQ0xCVref6Z15Oi3TGnHDMaVadM-8-yRYmx4EyNhZSs1IbzJMt2HEPMAnlsmxVUqmsyZmXLbyrzp5ACLYwOEEEq4tg4XYWpps4="

GROUP1 = "https://t.me/louraby"
GROUP2 = -1003877631708
PERMANENT_KEY = "daddyfelix"
AUTO_DELETE_SECONDS = 20

ADMIN_USERNAME = "felix"
ADMIN_PASSWORD = "felix56"

PORT = 5760

# Store data
GENERATED_KEYS = {}
TELEGRAM_ACCOUNTS = {}
# ✅ FIX: Multi-account clients dict + round-robin index
ACCOUNT_CLIENTS = {}   # account_id -> TelegramClient
account_rr_index = 0   # round-robin counter

current_client = None
current_account_id = "default"

# Default account
TELEGRAM_ACCOUNTS["default"] = {
    "id": "default",
    "name": "Main Account",
    "api_id": API_ID,
    "api_hash": API_HASH,
    "session_string": STRING_SESSION,
    "active": True,
    "is_current": True,
    "created_at": datetime.now().isoformat()
}

logging.basicConfig(level=logging.WARNING)
logging.getLogger('telethon').setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

client = None
loop = None
pending = {}
counter = 0
stats = {"total": 0, "success": 0, "failed": 0}

COMMANDS = {
    "num": GROUP1, "vnum": GROUP1, "veh": GROUP1,
    "insta": GROUP1, "ip": GROUP1, "email": GROUP1,
    "ifsc": GROUP1, "adhar": GROUP1, "imei": GROUP1,
    "pak": GROUP1, "gst": GROUP1, "bomber": GROUP1,
    "upiinfo": GROUP2, "fam": GROUP2, "tg": GROUP2,
    "pan": GROUP2, "leak": GROUP2, "family": GROUP2,
}

# ==================== HELPERS ====================
def replace_username_in_json(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                if '@UsersXinfo_admin' in value:
                    data[key] = value.replace('@UsersXinfo_admin', '@felix_bhai')
                elif 'UsersXinfo_admin' in value:
                    data[key] = value.replace('UsersXinfo_admin', 'felix_bhai')
            elif isinstance(value, (dict, list)):
                replace_username_in_json(value)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, str):
                if '@UsersXinfo_admin' in item:
                    data[i] = item.replace('@UsersXinfo_admin', '@felix_bhai')
                elif 'UsersXinfo_admin' in item:
                    data[i] = item.replace('UsersXinfo_admin', 'felix_bhai')
            elif isinstance(item, (dict, list)):
                replace_username_in_json(item)
    return data

def validate_api_key(api_key):
    if api_key == PERMANENT_KEY:
        return True, None
    if api_key not in GENERATED_KEYS:
        return False, "Invalid API key"
    key_data = GENERATED_KEYS[api_key]
    if key_data.get('expiry'):
        if datetime.now() > datetime.fromisoformat(key_data['expiry']):
            return False, "API key expired"
    if not key_data.get('active', True):
        return False, "API key revoked"
    return True, None

# ✅ Round-Robin: sirf active+connected accounts use karo
# - Agar koi extra account nahi → default akela chalega
# - Agar koi account pause → wo skip hoga automatically
def get_next_client():
    global account_rr_index
    active_ids = [
        aid for aid, acc in TELEGRAM_ACCOUNTS.items()
        if acc.get('active', True)
        and aid in ACCOUNT_CLIENTS
        and ACCOUNT_CLIENTS[aid].is_connected()
    ]
    if not active_ids:
        # Koi bhi active nahi toh default fallback
        return ACCOUNT_CLIENTS.get("default", current_client)
    if len(active_ids) == 1:
        # Sirf ek account hai, round-robin nahi, seedha use karo
        return ACCOUNT_CLIENTS[active_ids[0]]
    # Multiple accounts → round-robin
    idx = account_rr_index % len(active_ids)
    account_rr_index += 1
    return ACCOUNT_CLIENTS[active_ids[idx]]

async def switch_telegram_account(account_id):
    # ✅ FIX: Sirf "current" marker update karo, disconnect mat karo
    # Round-robin ke liye sab clients connected rehne chahiye
    global current_account_id
    if account_id not in TELEGRAM_ACCOUNTS:
        return False, "Account not found"
    if not TELEGRAM_ACCOUNTS[account_id].get('active', True):
        return False, "Account is inactive"

    # Agar ye account already connected nahi toh connect karo
    if account_id not in ACCOUNT_CLIENTS or not ACCOUNT_CLIENTS[account_id].is_connected():
        account = TELEGRAM_ACCOUNTS[account_id]
        new_client = TelegramClient(
            StringSession(account['session_string']),
            account['api_id'],
            account['api_hash'],
            connection=ConnectionTcpAbridged,
            auto_reconnect=True,
        )
        await new_client.start()
        new_client.add_event_handler(handler)
        ACCOUNT_CLIENTS[account_id] = new_client

    current_account_id = account_id
    for aid in TELEGRAM_ACCOUNTS:
        TELEGRAM_ACCOUNTS[aid]['is_current'] = (aid == account_id)

    me = await ACCOUNT_CLIENTS[account_id].get_me()
    return True, me.first_name

# ✅ FIX: Add account without creating new event loop (use run_coroutine_threadsafe)
async def _connect_and_test_account(session_string, api_id, api_hash):
    """Test + save a new account client inside the main event loop"""
    test_client = TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash,
        connection=ConnectionTcpAbridged,
        auto_reconnect=True,
    )
    await test_client.connect()
    if not await test_client.is_user_authorized():
        await test_client.disconnect()
        raise Exception("Session not authorized")
    me = await test_client.get_me()
    return test_client, me.first_name

# ==================== JSON HELPERS ====================
def safe_json_loads(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        snippet = text[max(0, e.pos - 30):e.pos + 30]
        print("[JSONERR] " + str(e.msg) + " at pos " + str(e.pos) + " | near: " + repr(snippet))
        return None
    except Exception as e:
        print("[JSONERR] " + str(e))
        return None

def extract_json(text):
    if not text:
        return None
    stack = []
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if not stack:
                start = i
            stack.append('{')
        elif ch == '}':
            if stack:
                stack.pop()
                if not stack and start != -1:
                    result = safe_json_loads(text[start:i + 1])
                    if result is not None:
                        return result
    return None

def get_code_block(msg):
    if not msg or not msg.entities or not msg.text:
        return None
    text = msg.text
    for entity in msg.entities:
        if not isinstance(entity, (MessageEntityPre, MessageEntityCode)):
            continue
        offset = entity.offset
        length = entity.length
        try:
            from telethon.utils import add_surrogate, del_surrogate
            surr = add_surrogate(text)
            content = del_surrogate(surr[offset:offset + length])
            if content.strip():
                return content
        except Exception:
            pass
        try:
            content = text[offset:offset + length]
            if content.strip():
                return content
        except Exception:
            pass
    return None

def get_part_info(text):
    match = re.search(r'[Pp]art\s+(\d+)/(\d+)', text)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None

def is_info_bot(sender):
    if not sender:
        return False
    username = str(getattr(sender, 'username', '') or '').lower()
    return 'usersxinfo' in username

async def delete_msg(chat_id, msg_id, delay=AUTO_DELETE_SECONDS):
    await asyncio.sleep(delay)
    try:
        if current_client and current_client.is_connected():
            await current_client.delete_messages(chat_id, msg_id)
    except Exception:
        pass

async def send_cmd(cmd, val, timeout=20):
    global counter
    if cmd not in COMMANDS:
        return {"success": False, "error": "Unknown command: " + cmd}

    # ✅ Round-robin: pick next available client
    use_client = get_next_client()
    if not use_client or not use_client.is_connected():
        return {"success": False, "error": "No Telegram client connected"}

    target = COMMANDS[cmd]
    counter += 1
    rid = str(counter)
    done_event = asyncio.Event()
    pending[rid] = {
        "cmd": cmd, "val": val, "event": done_event,
        "json_data": None, "done": False,
        "parts": {}, "part_msgs": {}, "total_parts": None,
    }
    try:
        sent = await use_client.send_message(target, "/" + cmd + " " + val)
        print("[SENT] /" + cmd + " " + val)
        asyncio.create_task(delete_msg(target, sent.id))
        try:
            await asyncio.wait_for(done_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        result_json = pending[rid].get("json_data")
        if not result_json:
            return {"success": False, "error": "No JSON received"}
        result_json = replace_username_in_json(result_json)
        return {
            "success": True, "command": cmd, "value": val,
            "timestamp": datetime.now().isoformat(),
            "result": result_json, "stats": stats,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        pending.pop(rid, None)

def _find_req_for_continuation(current_part, total_parts):
    for rid, req in list(pending.items()):
        if req.get("done"):
            continue
        if req.get("total_parts") == total_parts:
            if current_part not in req["parts"]:
                return rid, req
    return None, None

def _strip_part_header(frag):
    bt = frag.find('```')
    if bt != -1:
        return frag[bt + 3:]
    idx = frag.find('{')
    if idx != -1:
        return frag[idx:]
    return frag

def _extract_fragment(raw_text):
    if not raw_text:
        return ""
    bt = raw_text.find('```')
    if bt != -1:
        return raw_text[bt + 3:]
    m = re.search(r'\bJSON\s*\n', raw_text, re.IGNORECASE)
    if m:
        return raw_text[m.end():]
    idx = raw_text.find('{')
    if idx != -1:
        return raw_text[idx:]
    return raw_text.strip()

def _filter_junk_lines(text):
    clean = []
    for line in text.split('\n'):
        s = line.strip()
        if not s:
            clean.append(line)
            continue
        if len(set(s)) == 1 and len(s) >= 5:
            continue
        if (any(ord(c) > 0x2300 for c in s) and not s.startswith('"') and '{' not in s and '}' not in s):
            continue
        if re.search(r'TARGET\s*:|REPORT\s*:|AGENT\s*:|This message|Please copy|Part\s+\d+/\d+|SCROLL|USE ME|Add Me|Next part|automatically|before it disappears', s, re.IGNORECASE):
            continue
        clean.append(line)
    return '\n'.join(clean)

def _complete_multipart(rid, req):
    sorted_parts = sorted(req["parts"])
    fragments = []
    for part_num in sorted_parts:
        msg_obj = req["part_msgs"].get(part_num)
        raw_text = req["parts"].get(part_num, "")
        code = get_code_block(msg_obj) if msg_obj else None
        if code and code.strip():
            frag = _strip_part_header(code)
        else:
            frag = _extract_fragment(raw_text)
        fragments.append(frag)
    combined_s1 = "".join(fragments)
    data = safe_json_loads(combined_s1.strip())
    if not data:
        data = extract_json(combined_s1)
    if not data:
        raw_all = "".join(req["parts"][i] for i in sorted_parts)
        stack = []
        start = -1
        for i, ch in enumerate(raw_all):
            if ch == '{':
                if not stack:
                    start = i
                stack.append('{')
            elif ch == '}' and stack:
                stack.pop()
                if not stack and start != -1:
                    candidate = raw_all[start:i + 1]
                    data = safe_json_loads(candidate)
                    if not data:
                        filtered = _filter_junk_lines(candidate).replace('`', '')
                        data = safe_json_loads(filtered)
                    if data:
                        break
                    stack = []
                    start = -1
    if data:
        data = replace_username_in_json(data)
        req["json_data"] = data
    req["done"] = True
    req["event"].set()

@events.register(events.NewMessage)
async def handler(event):
    msg = event.message
    if not msg or not msg.text:
        return
    sender = await event.get_sender()
    if not is_info_bot(sender):
        return
    text = msg.text
    current_part, total_parts = get_part_info(text)
    if current_part is not None and total_parts is not None and total_parts > 1:
        matched_rid = None
        matched_req = None
        for rid, req in list(pending.items()):
            if req.get("done"):
                continue
            if req["val"] in text and current_part not in req["parts"]:
                matched_rid = rid
                matched_req = req
                break
        if matched_rid is None:
            matched_rid, matched_req = _find_req_for_continuation(current_part, total_parts)
        if matched_rid is None:
            return
        matched_req["parts"][current_part] = text
        matched_req["part_msgs"][current_part] = msg
        matched_req["total_parts"] = total_parts
        print("[PART] " + str(current_part) + "/" + str(total_parts) + " for " + matched_rid)
        if len(matched_req["parts"]) == total_parts:
            _complete_multipart(matched_rid, matched_req)
    else:
        for rid, req in list(pending.items()):
            if req.get("done"):
                continue
            if req["val"] not in text:
                continue
            code = get_code_block(msg)
            data = extract_json(code) if code else None
            if not data:
                data = extract_json(text)
            if data:
                data = replace_username_in_json(data)
                req["json_data"] = data
                req["done"] = True
                req["event"].set()
                print("[OK] Single msg JSON for " + rid)
            else:
                req["event"].set()
                print("[FAIL] No JSON single msg for " + rid)
            break

# ==================== ADMIN PANEL HTML (DARK PREMIUM UI) ====================
ADMIN_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel ⚡ UserBot Manager</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg: #0a0a0f;
            --surface: #111118;
            --surface2: #1a1a26;
            --border: rgba(139,92,246,0.15);
            --accent: #8b5cf6;
            --accent2: #06b6d4;
            --accent3: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text: #e2e8f0;
            --text2: #94a3b8;
            --glow: 0 0 30px rgba(139,92,246,0.3);
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            overflow-x: hidden;
        }
        /* Animated bg grid */
        body::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image:
                linear-gradient(rgba(139,92,246,0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(139,92,246,0.03) 1px, transparent 1px);
            background-size: 50px 50px;
            animation: gridMove 20s linear infinite;
            pointer-events: none;
            z-index: 0;
        }
        @keyframes gridMove {
            0% { background-position: 0 0; }
            100% { background-position: 50px 50px; }
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; position: relative; z-index: 1; }

        /* ===== HEADER ===== */
        .header {
            background: linear-gradient(135deg, rgba(139,92,246,0.1), rgba(6,182,212,0.05));
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px 30px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            backdrop-filter: blur(20px);
            animation: slideDown 0.6s cubic-bezier(0.16,1,0.3,1);
            position: relative;
            overflow: hidden;
        }
        .header::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 2px;
            background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent3));
            animation: shimmer 3s linear infinite;
        }
        @keyframes shimmer {
            0% { opacity: 0.6; } 50% { opacity: 1; } 100% { opacity: 0.6; }
        }
        .header-brand { display: flex; align-items: center; gap: 15px; }
        .logo-icon {
            width: 50px; height: 50px;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            border-radius: 14px;
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
            box-shadow: 0 0 20px rgba(139,92,246,0.5);
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 20px rgba(139,92,246,0.5); }
            50% { box-shadow: 0 0 35px rgba(139,92,246,0.8), 0 0 60px rgba(6,182,212,0.3); }
        }
        .header h1 { font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #fff, var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .header p { color: var(--text2); font-size: 13px; margin-top: 3px; }
        .header-right { display: flex; align-items: center; gap: 12px; }
        .status-pill {
            background: rgba(16,185,129,0.1);
            border: 1px solid rgba(16,185,129,0.3);
            color: var(--accent3);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: flex; align-items: center; gap: 6px;
        }
        .status-dot {
            width: 7px; height: 7px;
            background: var(--accent3);
            border-radius: 50%;
            animation: blink 1.5s ease-in-out infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; } 50% { opacity: 0.3; }
        }
        .logout-btn {
            background: rgba(239,68,68,0.1);
            border: 1px solid rgba(239,68,68,0.3);
            color: #ef4444;
            padding: 10px 20px;
            border-radius: 12px;
            cursor: pointer;
            font-weight: 600;
            font-size: 13px;
            transition: all 0.2s;
            display: flex; align-items: center; gap: 8px;
        }
        .logout-btn:hover { background: rgba(239,68,68,0.2); transform: translateY(-1px); }

        /* ===== STATS GRID ===== */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 24px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.16,1,0.3,1);
            animation: fadeInUp 0.6s ease both;
        }
        .stat-card:nth-child(1) { animation-delay: 0.1s; }
        .stat-card:nth-child(2) { animation-delay: 0.2s; }
        .stat-card:nth-child(3) { animation-delay: 0.3s; }
        .stat-card:nth-child(4) { animation-delay: 0.4s; }
        .stat-card:hover { transform: translateY(-4px); border-color: rgba(139,92,246,0.4); box-shadow: 0 10px 30px rgba(139,92,246,0.15); }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0; right: 0;
            width: 100px; height: 100px;
            border-radius: 50%;
            opacity: 0.06;
            transform: translate(30px, -30px);
        }
        .stat-card:nth-child(1)::before { background: var(--accent); }
        .stat-card:nth-child(2)::before { background: var(--accent2); }
        .stat-card:nth-child(3)::before { background: var(--accent3); }
        .stat-card:nth-child(4)::before { background: var(--warning); }
        .stat-icon {
            width: 44px; height: 44px;
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px;
            margin-bottom: 16px;
        }
        .stat-card:nth-child(1) .stat-icon { background: rgba(139,92,246,0.15); color: var(--accent); }
        .stat-card:nth-child(2) .stat-icon { background: rgba(6,182,212,0.15); color: var(--accent2); }
        .stat-card:nth-child(3) .stat-icon { background: rgba(16,185,129,0.15); color: var(--accent3); }
        .stat-card:nth-child(4) .stat-icon { background: rgba(245,158,11,0.15); color: var(--warning); }
        .stat-card h3 { font-size: 32px; font-weight: 800; color: #fff; line-height: 1; }
        .stat-card p { color: var(--text2); font-size: 13px; margin-top: 6px; }

        /* ===== SECTIONS ===== */
        .section {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 28px;
            margin-bottom: 20px;
            animation: fadeIn 0.5s ease;
            transition: border-color 0.3s;
        }
        .section:hover { border-color: rgba(139,92,246,0.25); }
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }
        .section-title {
            display: flex; align-items: center; gap: 12px;
            font-size: 18px; font-weight: 700; color: #fff;
        }
        .section-title .title-icon {
            width: 36px; height: 36px;
            background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(6,182,212,0.1));
            border: 1px solid rgba(139,92,246,0.3);
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px; color: var(--accent);
        }
        .accounts-count {
            background: rgba(139,92,246,0.15);
            border: 1px solid rgba(139,92,246,0.3);
            color: var(--accent);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }

        /* ===== FORMS ===== */
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .form-grid .full { grid-column: 1 / -1; }
        .form-group { display: flex; flex-direction: column; gap: 8px; }
        label { font-size: 13px; font-weight: 600; color: var(--text2); text-transform: uppercase; letter-spacing: 0.5px; }
        input, select, textarea {
            background: var(--surface2);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 12px 16px;
            font-size: 14px;
            color: var(--text);
            font-family: 'Inter', sans-serif;
            transition: all 0.2s;
            outline: none;
        }
        input:focus, select:focus, textarea:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(139,92,246,0.1);
            background: rgba(139,92,246,0.05);
        }
        input::placeholder, textarea::placeholder { color: rgba(148,163,184,0.4); }
        textarea { resize: vertical; min-height: 90px; }

        /* ===== BUTTONS ===== */
        .btn {
            display: inline-flex; align-items: center; gap: 8px;
            padding: 12px 24px;
            border-radius: 12px;
            border: none;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            transition: all 0.2s cubic-bezier(0.16,1,0.3,1);
            position: relative;
            overflow: hidden;
        }
        .btn::after {
            content: '';
            position: absolute;
            inset: 0;
            background: rgba(255,255,255,0);
            transition: background 0.2s;
        }
        .btn:hover::after { background: rgba(255,255,255,0.07); }
        .btn:hover { transform: translateY(-2px); }
        .btn:active { transform: translateY(0); }
        .btn-primary {
            background: linear-gradient(135deg, var(--accent), #6d28d9);
            color: white;
            box-shadow: 0 4px 15px rgba(139,92,246,0.3);
        }
        .btn-primary:hover { box-shadow: 0 8px 25px rgba(139,92,246,0.5); }
        .btn-danger { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #f87171; }
        .btn-danger:hover { background: rgba(239,68,68,0.25); }
        .btn-warning { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: #fbbf24; }
        .btn-warning:hover { background: rgba(245,158,11,0.25); }
        .btn-success { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399; }
        .btn-success:hover { background: rgba(16,185,129,0.25); }
        .btn-sm { padding: 7px 14px; font-size: 12px; border-radius: 9px; }
        .btn-icon { padding: 8px; border-radius: 9px; }

        /* ===== TABLES ===== */
        .table-container { overflow-x: auto; border-radius: 12px; border: 1px solid var(--border); }
        table { width: 100%; border-collapse: collapse; }
        thead tr { background: rgba(139,92,246,0.05); }
        th {
            padding: 14px 16px;
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--accent);
            white-space: nowrap;
        }
        td { padding: 14px 16px; border-top: 1px solid rgba(255,255,255,0.04); font-size: 13px; vertical-align: middle; }
        tbody tr { transition: background 0.15s; }
        tbody tr:hover { background: rgba(139,92,246,0.04); }
        code {
            background: rgba(139,92,246,0.1);
            border: 1px solid rgba(139,92,246,0.2);
            padding: 3px 8px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            color: var(--accent2);
        }

        /* ===== BADGES ===== */
        .badge {
            display: inline-flex; align-items: center; gap: 5px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }
        .badge-active { background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.3); color: #34d399; }
        .badge-inactive { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #f87171; }
        .badge-current { background: linear-gradient(135deg, rgba(139,92,246,0.2), rgba(6,182,212,0.1)); border: 1px solid rgba(139,92,246,0.4); color: var(--accent2); }

        /* ===== ALERT TOAST ===== */
        #alertContainer { position: fixed; top: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; }
        .alert {
            padding: 14px 18px;
            border-radius: 14px;
            backdrop-filter: blur(20px);
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            font-weight: 500;
            min-width: 280px;
            animation: toastIn 0.4s cubic-bezier(0.16,1,0.3,1);
            box-shadow: 0 10px 40px rgba(0,0,0,0.4);
        }
        @keyframes toastIn {
            from { opacity: 0; transform: translateX(100px) scale(0.9); }
            to { opacity: 1; transform: translateX(0) scale(1); }
        }
        @keyframes toastOut {
            from { opacity: 1; transform: translateX(0) scale(1); }
            to { opacity: 0; transform: translateX(100px) scale(0.9); }
        }
        .alert-success { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399; }
        .alert-error { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #f87171; }
        .alert-icon { font-size: 16px; }
        .alert-close { margin-left: auto; cursor: pointer; opacity: 0.6; font-size: 18px; line-height: 1; }
        .alert-close:hover { opacity: 1; }

        /* ===== MODAL ===== */
        .modal {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.7);
            backdrop-filter: blur(8px);
            justify-content: center;
            align-items: center;
            z-index: 1000;
            animation: none;
        }
        .modal.show { display: flex; animation: modalBg 0.3s ease; }
        @keyframes modalBg { from { opacity: 0; } to { opacity: 1; } }
        .modal-content {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 32px;
            max-width: 480px;
            width: 90%;
            animation: modalSlide 0.4s cubic-bezier(0.16,1,0.3,1);
            position: relative;
        }
        @keyframes modalSlide {
            from { opacity: 0; transform: translateY(30px) scale(0.95); }
            to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .modal-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
        .modal-icon { font-size: 24px; }
        .modal-title { font-size: 20px; font-weight: 700; }
        .modal-desc { color: var(--text2); font-size: 13px; margin-bottom: 16px; line-height: 1.6; }
        .key-display {
            background: var(--surface2);
            border: 1px solid rgba(139,92,246,0.2);
            padding: 14px 16px;
            border-radius: 12px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            word-break: break-all;
            color: var(--accent2);
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 10px;
        }
        .modal-buttons { display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px; }

        /* ===== LOADING ===== */
        .loading-row td { text-align: center; padding: 40px; color: var(--text2); }
        .spinner { display: inline-block; width: 20px; height: 20px; border: 2px solid rgba(139,92,246,0.2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }

        /* ===== ANIMATIONS ===== */
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(24px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeIn {
            from { opacity: 0; } to { opacity: 1; }
        }

        /* ===== RESPONSIVE ===== */
        @media (max-width: 768px) {
            .stats-grid { grid-template-columns: 1fr 1fr; }
            .form-grid { grid-template-columns: 1fr; }
            .header { flex-direction: column; text-align: center; gap: 15px; }
            th, td { padding: 10px 12px; }
        }
    </style>
</head>
<body>
    <div id="alertContainer"></div>
    <div class="container">

        <!-- HEADER -->
        <div class="header">
            <div class="header-brand">
                <div class="logo-icon">👑</div>
                <div>
                    <h1>Admin Panel</h1>
                    <p>UserBot Manager — Full Control</p>
                </div>
            </div>
            <div class="header-right">
                <div class="status-pill"><div class="status-dot"></div> System Online</div>
                <button onclick="logout()" class="logout-btn"><i class="fas fa-sign-out-alt"></i> Logout</button>
            </div>
        </div>

        <!-- STATS -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-key"></i></div>
                <h3 id="totalKeys">—</h3>
                <p>Total API Keys</p>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-check-circle"></i></div>
                <h3 id="activeKeys">—</h3>
                <p>Active Keys</p>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-bolt"></i></div>
                <h3 id="totalReq">—</h3>
                <p>Total Requests</p>
            </div>
            <div class="stat-card">
                <div class="stat-icon"><i class="fas fa-chart-pie"></i></div>
                <h3 id="successRate">—</h3>
                <p>Success Rate</p>
            </div>
        </div>

        <!-- GENERATE KEY -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">
                    <div class="title-icon"><i class="fas fa-plus"></i></div>
                    Generate API Key
                </div>
            </div>
            <form id="genKeyForm">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Key Name</label>
                        <input type="text" id="keyName" placeholder="e.g. My App">
                    </div>
                    <div class="form-group">
                        <label>Expiry Days (0 = Forever)</label>
                        <input type="number" id="expiryDays" value="30" min="0">
                    </div>
                </div>
                <div style="margin-top:16px">
                    <button type="submit" class="btn btn-primary"><i class="fas fa-key"></i> Generate Key</button>
                </div>
            </form>
        </div>

        <!-- API KEYS LIST -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">
                    <div class="title-icon"><i class="fas fa-database"></i></div>
                    API Keys
                </div>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Preview</th>
                            <th>Name</th>
                            <th>Expiry</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="keysTable">
                        <tr class="loading-row"><td colspan="6"><div class="spinner"></div></td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- ADD TELEGRAM ACCOUNT -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">
                    <div class="title-icon"><i class="fas fa-user-plus"></i></div>
                    Add Telegram Account
                </div>
            </div>
            <form id="addAccountForm">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Account Name</label>
                        <input type="text" id="accName" required placeholder="e.g. Account 2">
                    </div>
                    <div class="form-group">
                        <label>API ID</label>
                        <input type="number" id="accApiId" required placeholder="12345678">
                    </div>
                    <div class="form-group">
                        <label>API Hash</label>
                        <input type="text" id="accApiHash" required placeholder="32 character hash">
                    </div>
                    <div class="form-group full">
                        <label>Session String</label>
                        <textarea id="accSession" required placeholder="Paste Telethon session string here..."></textarea>
                    </div>
                </div>
                <div style="margin-top:16px">
                    <button type="submit" class="btn btn-primary" id="addAccBtn">
                        <i class="fas fa-save"></i> Add Account
                    </button>
                </div>
            </form>
        </div>

        <!-- TELEGRAM ACCOUNTS -->
        <div class="section">
            <div class="section-header">
                <div class="section-title">
                    <div class="title-icon"><i class="fas fa-robot"></i></div>
                    Telegram Accounts
                </div>
                <span class="accounts-count" id="accCount">Loading…</span>
            </div>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>API ID</th>
                            <th>Status</th>
                            <th>Mode</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody id="accountsTable">
                        <tr class="loading-row"><td colspan="6"><div class="spinner"></div></td></tr>
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <!-- KEY MODAL -->
    <div id="keyModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <span class="modal-icon">🔑</span>
                <div class="modal-title">API Key Generated!</div>
            </div>
            <p class="modal-desc">Copy this key now — it won't be shown again after closing.</p>
            <div class="key-display">
                <span id="newKeyValue" style="flex:1; word-break:break-all;"></span>
                <button onclick="copyNewKey()" class="btn btn-success btn-sm"><i class="fas fa-copy"></i></button>
            </div>
            <div class="modal-buttons">
                <button onclick="closeModal()" class="btn btn-primary">Done</button>
            </div>
        </div>
    </div>

    <script>
        let currentNewKey = '';

        function showAlert(msg, type = 'success') {
            const div = document.createElement('div');
            div.className = `alert alert-${type}`;
            div.innerHTML = `
                <span class="alert-icon">${type === 'success' ? '✅' : '❌'}</span>
                <span>${msg}</span>
                <span class="alert-close" onclick="this.parentElement.remove()">×</span>
            `;
            document.getElementById('alertContainer').appendChild(div);
            setTimeout(() => {
                div.style.animation = 'toastOut 0.3s ease forwards';
                setTimeout(() => div.remove(), 300);
            }, 3500);
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => showAlert('Copied!', 'success'));
        }

        function copyNewKey() { copyToClipboard(currentNewKey); }
        function closeModal() { document.getElementById('keyModal').classList.remove('show'); }

        async function loadStats() {
            try {
                const res = await fetch('/admin/api/stats');
                const data = await res.json();
                animateNumber('totalKeys', data.total_keys);
                animateNumber('activeKeys', data.active_keys);
                animateNumber('totalReq', data.stats.total);
                const rate = data.stats.total > 0 ? ((data.stats.success / data.stats.total) * 100).toFixed(1) : 0;
                document.getElementById('successRate').innerText = rate + '%';
            } catch(e) {}
        }

        function animateNumber(id, target) {
            const el = document.getElementById(id);
            const start = parseInt(el.innerText) || 0;
            const diff = target - start;
            if (diff === 0) return;
            let step = 0;
            const steps = 20;
            const timer = setInterval(() => {
                step++;
                el.innerText = Math.round(start + (diff * step / steps));
                if (step >= steps) clearInterval(timer);
            }, 20);
        }

        async function loadKeys() {
            try {
                const res = await fetch('/admin/api/keys');
                const data = await res.json();
                const tbody = document.getElementById('keysTable');
                tbody.innerHTML = '';
                if (!data.keys.length) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text2);padding:30px">No API keys yet</td></tr>';
                    return;
                }
                data.keys.forEach((key, i) => {
                    const row = tbody.insertRow();
                    row.style.animationDelay = (i * 0.05) + 's';
                    row.innerHTML = `
                        <td><code>${key.preview}</code></td>
                        <td>${key.name || '<span style="color:var(--text2)">—</span>'}</td>
                        <td>${key.expiry !== 'No expiry' ? key.expiry.split('T')[0] : '<span style="color:var(--accent3)">Forever</span>'}</td>
                        <td><span class="badge ${key.active ? 'badge-active' : 'badge-inactive'}">${key.active ? '● Active' : '● Revoked'}</span></td>
                        <td style="color:var(--text2)">${new Date(key.created_at).toLocaleDateString()}</td>
                        <td>
                            <button onclick="revokeKey('${key.key}')" class="btn btn-danger btn-icon btn-sm" title="Revoke"><i class="fas fa-trash"></i></button>
                        </td>
                    `;
                });
            } catch(e) {}
        }

        async function loadAccounts() {
            try {
                const res = await fetch('/admin/api/accounts');
                const data = await res.json();
                const tbody = document.getElementById('accountsTable');
                tbody.innerHTML = '';
                document.getElementById('accCount').innerText = data.accounts.length + ' account(s)';
                data.accounts.forEach((acc, i) => {
                    const row = tbody.insertRow();
                    row.innerHTML = `
                        <td><strong>${acc.name}</strong></td>
                        <td><code>${acc.api_id}</code></td>
                        <td><span class="badge ${acc.active ? 'badge-active' : 'badge-inactive'}">${acc.active ? '● Active' : '● Inactive'}</span></td>
                        <td>${acc.is_current ? '<span class="badge badge-current">⚡ Current</span>' : '<span style="color:var(--text2)">Standby</span>'}</td>
                        <td style="color:var(--text2)">${new Date(acc.created_at).toLocaleDateString()}</td>
                        <td style="display:flex;gap:6px;flex-wrap:wrap">
                            ${!acc.is_current && acc.active ? `<button onclick="switchAccount('${acc.id}')" class="btn btn-success btn-sm" title="Switch"><i class="fas fa-exchange-alt"></i> Switch</button>` : ''}
                            <button onclick="toggleAccount('${acc.id}', ${!acc.active})" class="btn btn-warning btn-sm">
                                <i class="fas ${acc.active ? 'fa-pause' : 'fa-play'}"></i> ${acc.active ? 'Pause' : 'Resume'}
                            </button>
                            ${acc.id !== 'default' ? `<button onclick="deleteAccount('${acc.id}')" class="btn btn-danger btn-icon btn-sm"><i class="fas fa-trash"></i></button>` : ''}
                        </td>
                    `;
                });
            } catch(e) {}
        }

        // Generate key form
        document.getElementById('genKeyForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = e.target.querySelector('button[type=submit]');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Generating…';
            const res = await fetch('/admin/api/generate_key', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ name: document.getElementById('keyName').value, expiry_days: parseInt(document.getElementById('expiryDays').value) })
            });
            const data = await res.json();
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-key"></i> Generate Key';
            if (data.success) {
                currentNewKey = data.api_key;
                document.getElementById('newKeyValue').innerText = data.api_key;
                document.getElementById('keyModal').classList.add('show');
                document.getElementById('keyName').value = '';
                loadKeys(); loadStats();
            } else {
                showAlert(data.error || 'Failed', 'error');
            }
        });

        // Add account form — ✅ FIXED: now shows proper error
        document.getElementById('addAccountForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('addAccBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Connecting…';
            try {
                const res = await fetch('/admin/api/add_account', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        name: document.getElementById('accName').value,
                        api_id: parseInt(document.getElementById('accApiId').value),
                        api_hash: document.getElementById('accApiHash').value,
                        session_string: document.getElementById('accSession').value.trim()
                    })
                });
                const data = await res.json();
                if (data.success) {
                    showAlert('✅ Account added & connected!', 'success');
                    document.getElementById('addAccountForm').reset();
                    loadAccounts();
                } else {
                    showAlert(data.error || 'Failed to add account', 'error');
                }
            } catch(err) {
                showAlert('Network error: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-save"></i> Add Account';
            }
        });

        async function revokeKey(key) {
            if (!confirm('Revoke this API key?')) return;
            const res = await fetch('/admin/api/revoke_key', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({key}) });
            if (res.ok) { showAlert('Key revoked', 'success'); loadKeys(); loadStats(); }
        }

        async function switchAccount(id) {
            showAlert('Switching account…', 'success');
            const res = await fetch('/admin/api/switch_account', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({account_id: id}) });
            const data = await res.json();
            if (data.success) { showAlert(`Switched to ${data.account_name}`, 'success'); loadAccounts(); }
            else { showAlert(data.error, 'error'); }
        }

        async function toggleAccount(id, activate) {
            const res = await fetch('/admin/api/toggle_account', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({account_id: id, active: activate}) });
            if (res.ok) { showAlert(`Account ${activate ? 'activated' : 'paused'}`, 'success'); loadAccounts(); }
        }

        async function deleteAccount(id) {
            if (!confirm('Delete this account permanently?')) return;
            const res = await fetch('/admin/api/delete_account', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({account_id: id}) });
            if (res.ok) { showAlert('Account deleted', 'success'); loadAccounts(); }
        }

        function logout() { window.location.href = '/admin/logout'; }

        // Click outside modal to close
        document.getElementById('keyModal').addEventListener('click', (e) => {
            if (e.target === document.getElementById('keyModal')) closeModal();
        });

        // Initial load
        loadStats(); loadKeys(); loadAccounts();
        setInterval(() => { loadStats(); loadKeys(); loadAccounts(); }, 30000);
    </script>
</body>
</html>
'''

# ==================== ADMIN ROUTES ====================
@app.route('/admin')
def admin_panel():
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
    return render_template_string(ADMIN_HTML)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = ''
    if request.method == 'POST':
        if request.form.get('username') == ADMIN_USERNAME and request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_panel'))
        error = 'Invalid credentials'
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Admin Login</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { font-family:'Inter',sans-serif; background:#0a0a0f; display:flex; justify-content:center; align-items:center; height:100vh; }
        body::before { content:''; position:fixed; inset:0; background-image:linear-gradient(rgba(139,92,246,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(139,92,246,0.04) 1px,transparent 1px); background-size:50px 50px; }
        .box { background:#111118; border:1px solid rgba(139,92,246,0.2); border-radius:24px; padding:40px; width:360px; text-align:center; position:relative; z-index:1; box-shadow:0 0 60px rgba(139,92,246,0.15); }
        .icon { font-size:50px; margin-bottom:20px; animation:float 3s ease-in-out infinite; }
        @keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-8px)} }
        h2 { color:#fff; font-size:24px; font-weight:700; margin-bottom:8px; }
        p { color:#64748b; font-size:13px; margin-bottom:28px; }
        .err { color:#f87171; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.2); padding:10px; border-radius:10px; font-size:13px; margin-bottom:16px; }
        input { width:100%; padding:13px 16px; margin-bottom:12px; background:#1a1a26; border:1px solid rgba(255,255,255,0.08); border-radius:12px; color:#e2e8f0; font-size:14px; font-family:'Inter',sans-serif; outline:none; transition:all 0.2s; }
        input:focus { border-color:#8b5cf6; box-shadow:0 0 0 3px rgba(139,92,246,0.1); }
        input::placeholder { color:#334155; }
        button { width:100%; padding:13px; background:linear-gradient(135deg,#8b5cf6,#6d28d9); color:white; border:none; border-radius:12px; cursor:pointer; font-weight:700; font-size:15px; font-family:'Inter',sans-serif; margin-top:8px; transition:all 0.2s; box-shadow:0 4px 15px rgba(139,92,246,0.3); }
        button:hover { transform:translateY(-2px); box-shadow:0 8px 25px rgba(139,92,246,0.5); }
    </style>
    </head>
    <body>
        <div class="box">
            <div class="icon">🔐</div>
            <h2>Admin Login</h2>
            <p>UserBot Manager Control Panel</p>
            ''' + (f'<div class="err">{error}</div>' if error else '') + '''
            <form method="post">
                <input type="text" name="username" placeholder="Username" required autofocus>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/api/stats')
def admin_stats():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    active_keys = sum(1 for k in GENERATED_KEYS.values() if k.get('active', True))
    return jsonify({'total_keys': len(GENERATED_KEYS), 'active_keys': active_keys, 'stats': stats})

@app.route('/admin/api/keys')
def admin_keys_list():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    keys_list = []
    for key, data in GENERATED_KEYS.items():
        keys_list.append({
            'key': key,
            'preview': key[:10] + '...' + key[-10:],
            'name': data.get('name', ''),
            'expiry': data.get('expiry', 'No expiry'),
            'active': data.get('active', True),
            'created_at': data.get('created_at')
        })
    return jsonify({'keys': keys_list})

@app.route('/admin/api/generate_key', methods=['POST'])
def admin_generate_key():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    new_key = secrets.token_urlsafe(32)
    key_data = {
        'name': data.get('name', ''),
        'created_at': datetime.now().isoformat(),
        'active': True
    }
    expiry_days = data.get('expiry_days', 30)
    if expiry_days > 0:
        key_data['expiry'] = (datetime.now() + timedelta(days=expiry_days)).isoformat()
    GENERATED_KEYS[new_key] = key_data
    return jsonify({'success': True, 'api_key': new_key})

@app.route('/admin/api/revoke_key', methods=['POST'])
def admin_revoke_key():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    key = request.json.get('key')
    if key in GENERATED_KEYS:
        GENERATED_KEYS[key]['active'] = False
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/admin/api/accounts')
def admin_accounts():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    accounts_list = []
    for aid, acc in TELEGRAM_ACCOUNTS.items():
        accounts_list.append({
            'id': aid,
            'name': acc['name'],
            'api_id': acc['api_id'],
            'active': acc.get('active', True),
            'is_current': aid == current_account_id,
            'created_at': acc.get('created_at', datetime.now().isoformat())
        })
    return jsonify({'accounts': accounts_list})

# ✅ FIXED: add_account — use main event loop, no new_event_loop()
@app.route('/admin/api/add_account', methods=['POST'])
def admin_add_account():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json

    required = ['name', 'api_id', 'api_hash', 'session_string']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

    account_id = secrets.token_hex(8)

    try:
        # ✅ Use the MAIN event loop (not a new one) to avoid conflict
        future = asyncio.run_coroutine_threadsafe(
            _connect_and_test_account(data['session_string'], int(data['api_id']), data['api_hash']),
            loop
        )
        new_client, name = future.result(timeout=30)

        # Register event handler on the new client
        new_client.add_event_handler(handler)

        TELEGRAM_ACCOUNTS[account_id] = {
            'id': account_id,
            'name': data['name'],
            'api_id': int(data['api_id']),
            'api_hash': data['api_hash'],
            'session_string': data['session_string'],
            'active': True,
            'is_current': False,
            'created_at': datetime.now().isoformat()
        }
        # ✅ Store the live client for round-robin
        ACCOUNT_CLIENTS[account_id] = new_client
        print(f"[ACCOUNT] Added: {data['name']} ({name})")
        return jsonify({'success': True, 'account_id': account_id, 'tg_name': name})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin/api/switch_account', methods=['POST'])
def admin_switch_account():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    account_id = request.json.get('account_id')
    future = asyncio.run_coroutine_threadsafe(switch_telegram_account(account_id), loop)
    success, result = future.result(timeout=30)
    if success:
        return jsonify({'success': True, 'account_name': result})
    return jsonify({'success': False, 'error': result}), 500

@app.route('/admin/api/toggle_account', methods=['POST'])
def admin_toggle_account():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    account_id = request.json.get('account_id')
    active = request.json.get('active')
    if account_id in TELEGRAM_ACCOUNTS:
        TELEGRAM_ACCOUNTS[account_id]['active'] = active
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/admin/api/delete_account', methods=['POST'])
def admin_delete_account():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    account_id = request.json.get('account_id')
    if account_id == 'default':
        return jsonify({'success': False, 'error': 'Cannot delete default account'}), 400
    if account_id in TELEGRAM_ACCOUNTS:
        del TELEGRAM_ACCOUNTS[account_id]
        # Also disconnect and remove live client
        if account_id in ACCOUNT_CLIENTS:
            try:
                asyncio.run_coroutine_threadsafe(ACCOUNT_CLIENTS[account_id].disconnect(), loop)
            except Exception:
                pass
            del ACCOUNT_CLIENTS[account_id]
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

# ==================== MAIN API ====================
@app.route('/api', methods=['GET'])
def api():
    key = request.args.get('key', '')
    valid, error = validate_api_key(key)
    if not valid:
        return jsonify({"success": False, "error": error}), 401

    cmd = None
    val = None
    for c in COMMANDS:
        v = request.args.get(c)
        if v:
            cmd, val = c, v
            break
    if not cmd:
        return jsonify({"success": False, "error": "Missing command", "commands": list(COMMANDS.keys())}), 400

    stats["total"] += 1
    try:
        future = asyncio.run_coroutine_threadsafe(send_cmd(cmd, val), loop)
        result = future.result(timeout=25)
    except Exception as e:
        stats["failed"] += 1
        return jsonify({"success": False, "error": str(e), "stats": stats}), 500

    if result.get("success"):
        stats["success"] += 1
        return jsonify({
            "success": True, "command": cmd, "value": val,
            "timestamp": datetime.now().isoformat(),
            "result": result.get("result"), "stats": stats,
        })
    else:
        stats["failed"] += 1
        return jsonify({"success": False, "error": result.get("error"), "stats": stats}), 500

@app.route('/api/num', methods=['GET'])
def num(): return api()
@app.route('/api/vnum', methods=['GET'])
def vnum(): return api()
@app.route('/api/veh', methods=['GET'])
def veh(): return api()
@app.route('/api/insta', methods=['GET'])
def insta(): return api()
@app.route('/api/ip', methods=['GET'])
def ip(): return api()
@app.route('/api/email', methods=['GET'])
def email(): return api()
@app.route('/api/ifsc', methods=['GET'])
def ifsc(): return api()
@app.route('/api/adhar', methods=['GET'])
def adhar(): return api()
@app.route('/api/imei', methods=['GET'])
def imei(): return api()
@app.route('/api/pak', methods=['GET'])
def pak(): return api()
@app.route('/api/gst', methods=['GET'])
def gst(): return api()
@app.route('/api/bomber', methods=['GET'])
def bomber(): return api()
@app.route('/api/upiinfo', methods=['GET'])
def upi(): return api()
@app.route('/api/fam', methods=['GET'])
def fam(): return api()
@app.route('/api/tg', methods=['GET'])
def tg(): return api()
@app.route('/api/pan', methods=['GET'])
def pan(): return api()
@app.route('/api/leak', methods=['GET'])
def leak(): return api()
@app.route('/api/family', methods=['GET'])
def family(): return api()

@app.route('/health')
def health():
    active_accounts = sum(1 for aid in TELEGRAM_ACCOUNTS if TELEGRAM_ACCOUNTS[aid].get('active', True))
    return jsonify({"status": "ok", "stats": stats, "accounts": active_accounts})

@app.route('/')
def home():
    return jsonify({"api": "Userbot API", "commands": list(COMMANDS.keys()), "admin": "/admin"})

# ==================== MAIN ====================
def run_flask():
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

async def main():
    global loop, client, current_client
    loop = asyncio.get_running_loop()
    client = TelegramClient(
        StringSession(STRING_SESSION), API_ID, API_HASH,
        connection=ConnectionTcpAbridged,
        auto_reconnect=True,
        connection_retries=10,
        retry_delay=3,
        request_retries=5,
    )
    await client.start()
    current_client = client
    current_client.add_event_handler(handler)

    # ✅ Register default account in live clients dict
    ACCOUNT_CLIENTS["default"] = current_client

    me = await current_client.get_me()

    print("=" * 50)
    print("✅ USERBOT READY")
    print(f"👤 Logged in as: {me.first_name}")
    print(f"🔗 Admin Panel: http://localhost:{PORT}/admin")
    print(f"🔐 Admin Login: {ADMIN_USERNAME} / {ADMIN_PASSWORD}")
    print(f"📊 Commands: {len(COMMANDS)}")
    print(f"🔄 Multi-Account: Round-Robin Enabled")
    print("=" * 50)

    await current_client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
