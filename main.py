from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session as flask_session
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.sessions import StringSession
import asyncio
import threading
import time
import re
import logging
import os
import json
from datetime import datetime, timedelta
import uuid
import secrets
from collections import defaultdict
from functools import wraps

# ==================== CONFIG (env se load, fallback hardcoded) ====================
API_NAME    = os.environ.get("API_NAME",    "FELIX BYPASS API")
API_OWNER   = os.environ.get("API_OWNER",   "@Felix_bhai")
API_VERSION = "5.0"
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "felixadmin2026")

# Admin Web Login
ADMIN_WEB_ID   = os.environ.get("ADMIN_WEB_ID",   "felix")
ADMIN_WEB_PASS = os.environ.get("ADMIN_WEB_PASS",  "felix56")

# Group / Channel
TARGET_GROUP      = os.environ.get("TARGET_GROUP",      "felixrdx2")
STORE_CHANNEL     = os.environ.get("STORE_CHANNEL",     "felixrdx1")
FELIX_LINK        = os.environ.get("FELIX_LINK",        "https://t.me/Felix_modz1")
NICK_BOT_USERNAME = os.environ.get("NICK_BOT_USERNAME", "@Nick_Bypass_Bot")

# ==================== ACCOUNTS ====================
ACCOUNTS = [
    {
        "name":    "@SHADOW_VIP_OWNER3",
        "api_id":  21058954,
        "api_hash":"094904b951218650c96c9cfb2195cdc2",
        "session": "1BVtsOKwBuz8LKo0CKyj2OgZo8UFLdJOi02DZ0r0h800nkXH3044F84P8TutV8-CRrbz169s1GIlWCUStPE4WxHlHDJBnaDR4ttnzVr4hrGD6dznuopa7_WxbEWT5Zm3xVs-tMo2vWe8JaUTLtmaqU6iUX7wbDbWDR4mdSqv_D2RiHZ-zdXu1fa23EuJ7FF2p_a4uCwQM0V8-H93r4bLLiv7LJeX1DeT79j8kgCPYsSm1ER2vS2lkZe3gV9NRJbq3PwvWm3cGm1X2wwip7U4uEn8Ssbt133RsODRv-OOQjywXOvOcwYgBqUF1cmaRCBZWdbmEW93FqWua46_0-LZTwcmVLQJn9O8=",
        "count":   0,
        "blacklisted": False,
        "blacklisted_at": None,
    },
    {
        "name":    "@Robotfelix1",
        "api_id":  35240692,
        "api_hash":"8e95febf3563b0da51e9cbb72640c541",
        "session": "1BVtsOKwBuziA0KqN9tQAyXmK4odLN63lN80peNmIGrgc5FpLHtPcxIN6prrgVLQd5gULnfnV2r_XHCOk2iF4bVa7U0bCXMulWFgOnN0xSv9pbzwPLB5PizaKW8miiMJzLAVndwsxFoXqjBHTcoO32lcSe22LEHNJcPpSV3jFLvwCFek4SNilltxZiO7f9hZXmMA00j66xETXGMjne4gC6MncJeAHIGTYsiEDiCzx508BUXhpodjjLX8zHQQIQSiDaMp_TkqomQaA0x1NEYrV955528xnoQ_ZWcMf-t46OEt9qtmIIHolWOjTv_g_z_lUAHS1iDwMvw4s5WcWGaI_xRHNYX0sH9U=",
        "count":   0,
        "blacklisted": False,
        "blacklisted_at": None,
    },
    {
        "name":    "@Redoxlala",
        "api_id":  30507352,
        "api_hash":"5cf21ea9611af88bd05c851248d4aca1",
        "session": "1BVtsOKwBuwuhwRZohmCeDOwGU_oj0IuKGkrVQd7sGQJ8kxjv2CvqImQ0Q1C0x79xnpq-anltBqMXpQEI-bCu59S7Su7FBA_DsktFfnWNgUoSc2yw3lLjv7pNbxMI-Ad8MpEgc_0k8_bcHjGnGjiyAS3HC9X5UaOwZTkWMG2i94wFcHsQSgeG-RVQt8rYBinFrgj8CcPeIzxeeNbbEOikYKKvzQP6vWXVMzuxi6Bf94TTKGztXsug38fpmNz9YICq79MUyAZl7AruYlRiJ_YoDNYmjbsHb2kcBJyXfkWYSVmUJZPVH6LYDJbQPOCwRvbKMatwxK9tJpRBdPoOw1dWVbzdr0rXZA8=",
        "count":   0,
        "blacklisted": False,
        "blacklisted_at": None,
    },
    {
        "name":    "@Robotfelix2",
        "api_id":  30269370,
        "api_hash":"753ad9fdb88508b5e3627625e5c3fada",
        "session": "1BVtsOKwBu5vrcrhia-qKiCYm37iGtDItaI6C-VdYHay_fKdVD8nmg8RZbJLXJ0krrG8l27z48yfnG8jMzHndNn9_9aboczGSJjvqYXdFg6mCrUWKfEyuv0UnyvaHvOciORZ1ABummdlk_7AlwJhP6P0wa_PeeSkZCKy1iHfyb_1nWP1L1CN_2NWJV9KOphx50HkP2V8E0y9hJyZ8vuCk2h2lI79di9nGA9ec0SgVIG-PW8rfUUuqiRuBeoNvi-bBi8MHTLC1VQ0x402NtkBJaecXam91PY7tQzbFLim_lWL8ejEZ1ezALSLlmNj2eeJOMRrVP8EaAULK8xTtWPAWA0AuNdjxWEE=",
        "count":   0,
        "blacklisted": False,
        "blacklisted_at": None,
    },
]

LINKS_PER_ACCOUNT      = 3
BLACKLIST_RESET_HOURS  = 2       # Kitne ghante baad blacklisted account reset ho
EXPIRY_NOTIFY_HOURS    = 24      # Key expire hone se kitne ghante pehle notify kare
RATE_LIMIT_PER_MIN     = 10      # Per key per minute requests

# ==================== PERSIST ====================
_DEFAULT_DATA_DIR = os.environ.get("RENDER_PERSISTENT_DIR", ".")
DATA_FILE  = os.path.join(_DEFAULT_DATA_DIR, "felix_data.json")
LINKS_FILE = os.path.join(_DEFAULT_DATA_DIR, "bypassed_links.json")
BACKUP_HEADER = "FELIX_BACKUP_V2"
BACKUP_MSG_ID = None

# ==================== STATE ====================
clients      = []
current_idx  = 0
idx_lock     = threading.Lock()

active_requests   = {}
completed_requests = {}
req_lock           = threading.Lock()

bypass_cache = {}
cache_lock   = threading.Lock()

total_requests      = 0
successful_requests = 0
failed_requests     = 0

# Rate limiting: key -> list of timestamps
rate_limit_tracker = defaultdict(list)
rate_lock = threading.Lock()

# Usage logs per key: key -> list of {time, link, success}
usage_logs = defaultdict(list)
log_lock   = threading.Lock()

# Webhook urls per key
webhook_urls = {}  # key -> url

PERMANENT_KEYS = {
    "daddyfelix": {
        "key": "daddyfelix", "type": "permanent",
        "created_at": datetime.now().isoformat(),
        "total_used": 0, "status": "active",
        "ip_whitelist": [],
        "telegram_notify_id": None,
    }
}

# Free guest key — limited 5 uses per IP per day (tracked separately)
FREE_GUEST_KEY = "FREE_DAILY_GUEST"
FREE_GUEST_LIMIT = 5  # per IP per day
free_guest_usage = defaultdict(lambda: {"count": 0, "date": ""})
free_guest_lock = threading.Lock()

def check_free_guest(client_ip):
    """Return True if IP can do a free bypass, else False."""
    today = datetime.now().strftime("%Y-%m-%d")
    with free_guest_lock:
        rec = free_guest_usage[client_ip]
        if rec["date"] != today:
            rec["count"] = 0
            rec["date"] = today
        if rec["count"] >= FREE_GUEST_LIMIT:
            return False
        rec["count"] += 1
        return True
temp_keys_db = {}

logging.getLogger('telethon').setLevel(logging.WARNING)
app  = Flask(__name__)
app.secret_key = secrets.token_hex(32)
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

_channel_client_ref = None

# ==================== DATA PERSIST ====================
def _build_data_dict():
    return {
        "bypass_cache": bypass_cache,
        "stats": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
        },
        "temp_keys": temp_keys_db,
        "permanent_keys_usage": {k: v["total_used"] for k, v in PERMANENT_KEYS.items()},
        "webhook_urls": webhook_urls,
        "usage_logs": {k: v[-200:] for k, v in usage_logs.items()},  # last 200 logs
    }

def _apply_data_dict(data):
    global bypass_cache, total_requests, successful_requests, failed_requests
    bypass_cache = data.get("bypass_cache", {})
    stats = data.get("stats", {})
    total_requests      = stats.get("total_requests", 0)
    successful_requests = stats.get("successful_requests", 0)
    failed_requests     = stats.get("failed_requests", 0)
    temp_keys_db.update(data.get("temp_keys", {}))
    pku = data.get("permanent_keys_usage", {})
    for k, used in pku.items():
        if k in PERMANENT_KEYS:
            PERMANENT_KEYS[k]["total_used"] = used
    webhook_urls.update(data.get("webhook_urls", {}))
    for k, logs in data.get("usage_logs", {}).items():
        usage_logs[k] = logs

def save_data_local():
    try:
        d = os.path.dirname(DATA_FILE)
        if d: os.makedirs(d, exist_ok=True)
        with open(DATA_FILE, "w") as f:
            json.dump(_build_data_dict(), f, indent=2)
    except Exception as e:
        print(f"⚠️  Local save error: {e}")

def load_data_local():
    try:
        if not os.path.exists(DATA_FILE):
            return False
        with open(DATA_FILE) as f:
            data = json.load(f)
        _apply_data_dict(data)
        print(f"✅ Local data loaded")
        return True
    except Exception as e:
        print(f"⚠️  Local load error: {e}")
        return False

async def save_data_channel(client):
    global BACKUP_MSG_ID
    try:
        json_str = json.dumps(_build_data_dict(), separators=(',', ':'))
        text = BACKUP_HEADER + "\n" + json_str
        if BACKUP_MSG_ID:
            try:
                await client.edit_message(STORE_CHANNEL, BACKUP_MSG_ID, text)
            except Exception as edit_err:
                err_str = str(edit_err).lower()
                # If content same or message not found, send new message
                if "not modified" in err_str or "message_id_invalid" in err_str:
                    if "not modified" in err_str:
                        # Content same hai, no action needed
                        save_data_local()
                        return
                    BACKUP_MSG_ID = None
                    msg = await client.send_message(STORE_CHANNEL, text)
                    BACKUP_MSG_ID = msg.id
                    try:
                        await client.pin_message(STORE_CHANNEL, msg.id)
                    except Exception:
                        pass
                else:
                    raise edit_err
        else:
            msg = await client.send_message(STORE_CHANNEL, text)
            BACKUP_MSG_ID = msg.id
            try:
                await client.pin_message(STORE_CHANNEL, msg.id)
            except Exception:
                pass
        save_data_local()
    except Exception as e:
        print(f"⚠️  Channel save error: {e}")
        save_data_local()

async def load_data_channel(client):
    global BACKUP_MSG_ID
    try:
        async for msg in client.iter_messages(STORE_CHANNEL, limit=50):
            if msg.text and msg.text.startswith(BACKUP_HEADER):
                json_str = msg.text[len(BACKUP_HEADER)+1:]
                data = json.loads(json_str)
                _apply_data_dict(data)
                BACKUP_MSG_ID = msg.id
                print(f"✅ Channel backup loaded")
                save_data_local()
                return True
        return False
    except Exception as e:
        print(f"⚠️  Channel load error: {e}")
        return False

def save_data():
    save_data_local()
    if _channel_client_ref:
        asyncio.run_coroutine_threadsafe(save_data_channel(_channel_client_ref), loop)

def auto_save_loop():
    while True:
        time.sleep(60)
        save_data()

# ==================== RATE LIMITING ====================
def check_rate_limit(key):
    with rate_lock:
        now = time.time()
        timestamps = rate_limit_tracker[key]
        # Remove timestamps older than 60 seconds
        timestamps = [t for t in timestamps if now - t < 60]
        rate_limit_tracker[key] = timestamps
        if len(timestamps) >= RATE_LIMIT_PER_MIN:
            return False
        timestamps.append(now)
        return True

# ==================== IP WHITELIST ====================
def check_ip_whitelist(key, client_ip):
    kdata = PERMANENT_KEYS.get(key) or temp_keys_db.get(key)
    if not kdata:
        return False
    whitelist = kdata.get("ip_whitelist", [])
    if not whitelist:
        return True  # No restriction
    return client_ip in whitelist

# ==================== KEY FUNCTIONS ====================
def validate_key(key):
    if key in PERMANENT_KEYS:
        return {'valid': True, 'data': PERMANENT_KEYS[key], 'type': 'permanent'}
    if key in temp_keys_db:
        kd = temp_keys_db[key]
        if kd.get('status') == 'expired' or datetime.now() > datetime.fromisoformat(kd['expires_at']):
            kd['status'] = 'expired'
            return {'valid': False, 'reason': 'EXPIRED'}
        return {'valid': True, 'data': kd, 'type': 'temporary'}
    return {'valid': False, 'reason': 'INVALID_KEY'}

def generate_temp_key(days=1, ip_whitelist=None, telegram_notify_id=None):
    key = secrets.token_hex(16)
    exp = datetime.now() + timedelta(days=days)
    temp_keys_db[key] = {
        "key": key, "type": "temporary",
        "created_at": datetime.now().isoformat(),
        "expires_at": exp.isoformat(),
        "total_used": 0, "status": "active", "days": days,
        "ip_whitelist": ip_whitelist or [],
        "telegram_notify_id": telegram_notify_id,
    }
    save_data()
    return key, exp

def expire_key(key):
    if key in temp_keys_db:
        temp_keys_db[key]['expires_at'] = datetime.now().isoformat()
        temp_keys_db[key]['status'] = 'expired'
        save_data()
        return True
    return False

def delete_key(key):
    if key in temp_keys_db:
        del temp_keys_db[key]
        save_data()
        return True
    return False

def log_usage(key, success, link=""):
    global total_requests, successful_requests, failed_requests
    total_requests += 1
    if success:
        successful_requests += 1
        if key in PERMANENT_KEYS:
            PERMANENT_KEYS[key]['total_used'] += 1
        elif key in temp_keys_db:
            temp_keys_db[key]['total_used'] += 1
    else:
        failed_requests += 1
    with log_lock:
        usage_logs[key].append({
            "time": datetime.now().isoformat(),
            "link": link[:80],
            "success": success
        })
        usage_logs[key] = usage_logs[key][-500:]
    if total_requests % 5 == 0:
        save_data()

def stats_dict():
    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
    }

# ==================== ACCOUNT ROTATION + HEALTH ====================
def all_blacklisted():
    return all(a['blacklisted'] for a in ACCOUNTS)

def reset_expired_blacklists():
    """Blacklisted accounts ko BLACKLIST_RESET_HOURS ke baad reset karo."""
    now = datetime.now()
    for acc in ACCOUNTS:
        if acc['blacklisted'] and acc.get('blacklisted_at'):
            bl_time = datetime.fromisoformat(acc['blacklisted_at'])
            if (now - bl_time).total_seconds() > BLACKLIST_RESET_HOURS * 3600:
                acc['blacklisted'] = False
                acc['blacklisted_at'] = None
                acc['count'] = 0
                print(f"♻️  Account reset: {acc['name']}")

def get_active_client():
    global current_idx
    with idx_lock:
        reset_expired_blacklists()
        if all_blacklisted():
            return None, None
        tries = 0
        while ACCOUNTS[current_idx]['blacklisted'] and tries < len(ACCOUNTS):
            current_idx = (current_idx + 1) % len(ACCOUNTS)
            tries += 1
        acc = ACCOUNTS[current_idx]
        acc['count'] += 1
        if acc['count'] >= LINKS_PER_ACCOUNT:
            acc['count'] = 0
            next_idx = (current_idx + 1) % len(ACCOUNTS)
            for _ in range(len(ACCOUNTS)):
                if not ACCOUNTS[next_idx]['blacklisted']:
                    current_idx = next_idx
                    print(f"🔄 Switching to: {ACCOUNTS[current_idx]['name']}")
                    break
                next_idx = (next_idx + 1) % len(ACCOUNTS)
        return clients[ACCOUNTS.index(acc)], acc

def mark_blacklisted(acc):
    global current_idx
    with idx_lock:
        acc['blacklisted'] = True
        acc['blacklisted_at'] = datetime.now().isoformat()
        acc['count'] = 0
        print(f"🚫 Account blacklisted: {acc['name']}")
        current_idx = (current_idx + 1) % len(ACCOUNTS)
        for _ in range(len(ACCOUNTS)):
            if not ACCOUNTS[current_idx]['blacklisted']:
                break
            current_idx = (current_idx + 1) % len(ACCOUNTS)
        print(f"➡️  Switched to: {ACCOUNTS[current_idx]['name']}")

# ==================== EXPIRY NOTIFICATIONS ====================
async def send_expiry_notifications(client):
    """Keys jo EXPIRY_NOTIFY_HOURS ke andar expire hongi unhe Telegram pe notify karo."""
    now = datetime.now()
    notify_before = timedelta(hours=EXPIRY_NOTIFY_HOURS)
    for key, kd in list(temp_keys_db.items()):
        if kd.get('status') == 'expired':
            continue
        exp = datetime.fromisoformat(kd['expires_at'])
        time_left = exp - now
        if timedelta(0) < time_left <= notify_before:
            notify_id = kd.get('telegram_notify_id')
            if notify_id and not kd.get('notified'):
                try:
                    hours_left = int(time_left.total_seconds() / 3600)
                    await client.send_message(int(notify_id),
                        f"⚠️ **Felix API Key Expiry Alert!**\n\n"
                        f"🔑 Key: `{key[:8]}...{key[-4:]}`\n"
                        f"⏳ Expires in: ~{hours_left} hours\n"
                        f"📅 Expires at: {exp.strftime('%Y-%m-%d %H:%M')}\n\n"
                        f"Please renew your key to continue using the API.\n"
                        f"Contact: {API_OWNER}"
                    )
                    kd['notified'] = True
                    print(f"📨 Expiry notification sent for key {key[:8]}...")
                except Exception as e:
                    print(f"⚠️  Notify error: {e}")

def expiry_notification_loop():
    while True:
        time.sleep(3600)  # Har 1 ghante check karo
        if _channel_client_ref:
            asyncio.run_coroutine_threadsafe(
                send_expiry_notifications(_channel_client_ref), loop
            )

# ==================== WEBHOOK ====================
def send_webhook(key, result_data):
    """Webhook URL pe result push karo."""
    url = webhook_urls.get(key)
    if not url:
        return
    import urllib.request, urllib.error
    try:
        payload = json.dumps(result_data).encode('utf-8')
        req = urllib.request.Request(url, data=payload,
            headers={'Content-Type': 'application/json'}, method='POST')
        urllib.request.urlopen(req, timeout=5)
        print(f"📡 Webhook sent to: {url[:50]}")
    except Exception as e:
        print(f"⚠️  Webhook error: {e}")

# ==================== AUTO-RECONNECT ====================
async def auto_reconnect_loop():
    while True:
        await asyncio.sleep(30)
        for i, cl in enumerate(clients):
            if cl is None:
                continue
            try:
                if not cl.is_connected():
                    print(f"🔌 Reconnecting {ACCOUNTS[i]['name']}...")
                    await cl.connect()
                    if await cl.is_user_authorized():
                        print(f"✅ Reconnected: {ACCOUNTS[i]['name']}")
                    else:
                        print(f"❌ Re-auth failed: {ACCOUNTS[i]['name']}")
            except Exception as e:
                print(f"⚠️  Reconnect error [{ACCOUNTS[i]['name']}]: {e}")

# ==================== LINK EXTRACTION ====================
def extract_links(text, entities=None):
    orig = None
    bypassed = None

    m = re.search(r'Original\s*Link\s*:?\s*[✔️✅]*\s*(https?://[^\s\n]+)', text, re.IGNORECASE)
    if m: orig = m.group(1).strip()
    m = re.search(r'Bypassed\s*Link\s*:?\s*[✔️✅]*\s*(https?://[^\s\n]+)', text, re.IGNORECASE)
    if m: bypassed = m.group(1).strip()

    if not orig or not bypassed:
        for line in text.split('\n'):
            if 'Original' in line and 'http' in line and not orig:
                urls = re.findall(r'https?://[^\s]+', line)
                if urls: orig = urls[0]
            if 'Bypassed' in line and 'http' in line and not bypassed:
                urls = re.findall(r'https?://[^\s]+', line)
                if urls: bypassed = urls[0]

    if entities:
        from telethon.tl.types import MessageEntityTextUrl
        entity_urls = []
        for ent in entities:
            if isinstance(ent, MessageEntityTextUrl):
                url = ent.url
                pos = ent.offset
                snippet = text[max(0, pos-30):pos+ent.length+30].lower()
                entity_urls.append((pos, url, snippet))
        entity_urls.sort(key=lambda x: x[0])
        for pos, url, snippet in entity_urls:
            if not url.startswith('http'):
                continue
            if 't.me/nick_bypass_bot' in url.lower():
                continue
            is_download_url = (
                'go.urlking' in url.lower() or 'iili.io' in url.lower() or
                'novafile' in url.lower() or 't.me/' in url.lower() or
                '/stream/' in url.lower() or '/download/' in url.lower()
            )
            is_original_url = (
                'urlking.in' in url.lower() or 'linksgo' in url.lower() or
                'gplinks' in url.lower() or 'shrinkme' in url.lower() or
                'mdiskshortner' in url.lower()
            )
            if not bypassed and ('download link' in snippet or 'bypassed link' in snippet):
                bypassed = url
            elif not bypassed and is_download_url:
                bypassed = url
            elif not orig and ('original' in snippet or is_original_url) and not is_download_url:
                orig = url
            elif not orig and not bypassed:
                if is_original_url:
                    orig = url
                elif is_download_url:
                    bypassed = url
    # Clean Telegram markdown formatting from links (* ** __ etc.)
    def clean_link(url):
        if not url:
            return url
        # Remove trailing markdown symbols and punctuation
        url = re.sub(r'[\*\_\`\~]+$', '', url.strip())
        # Remove any leading markdown symbols
        url = re.sub(r'^[\*\_\`\~]+', '', url.strip())
        return url.strip()
    orig = clean_link(orig)
    bypassed = clean_link(bypassed)
    return orig, bypassed

# ==================== SAVE LINKS TO JSON (no channel spam) ====================
links_lock = threading.Lock()

def save_link_to_json(orig, bypassed, acc_name):
    """BR/BR links sirf JSON file mein save — channel par koi spam nahi."""
    try:
        d = os.path.dirname(LINKS_FILE)
        if d:
            os.makedirs(d, exist_ok=True)
        with links_lock:
            if os.path.exists(LINKS_FILE):
                with open(LINKS_FILE, "r") as f:
                    data = json.load(f)
            else:
                data = []
            data.append({
                "original": orig,
                "bypassed": bypassed,
                "account":  acc_name,
                "time":     datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            with open(LINKS_FILE, "w") as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Links JSON save error: {e}")

async def save_to_channel(orig, bypassed, acc_name):
    """Channel pe spam nahi — sirf JSON file mein save hoti hain."""
    threading.Thread(target=save_link_to_json, args=(orig, bypassed, acc_name), daemon=True).start()

# ==================== TELETHON HANDLER ====================
def make_handler(cl, acc):
    @cl.on(events.NewMessage(chats=TARGET_GROUP))
    async def handler(event):
        msg = event.message
        if not msg or not msg.text:
            return
        text = msg.text
        sender = await event.get_sender()
        if sender and sender.bot and NICK_BOT_USERNAME.lower().replace("@","") in (getattr(sender, 'username', '') or '').lower():
            pass
        elif not (sender and sender.bot):
            return

        orig, bypassed = extract_links(text, msg.entities)
        if not bypassed:
            return

        captured = False
        captured_orig = None

        with req_lock:
            for req_id, rd in list(active_requests.items()):
                if rd['complete']:
                    continue
                req_link = rd['original_link']
                orig_match = bool(orig) and (
                    req_link == orig or
                    req_link.rstrip('/') == orig.rstrip('/') or
                    req_link[:50] == orig[:50] or
                    req_link[:40] in orig or
                    orig[:40] in req_link
                )
                text_match = (
                    req_link in text or req_link[:50] in text or
                    req_link[:45] in text or req_link[:40] in text
                )
                acc_match = rd.get('acc_name') == acc['name']
                only_one_pending = len([r for r in active_requests.values() if not r['complete']]) == 1
                strong_match = only_one_pending and acc_match

                if (acc_match and (orig_match or text_match)) or strong_match:
                    final_orig = rd['original_link']
                    result = {'original_link': final_orig, 'bypassed_link': bypassed}
                    active_requests[req_id]['result'] = result
                    active_requests[req_id]['complete'] = True
                    completed_requests[req_id] = active_requests[req_id]
                    captured_orig = final_orig
                    del active_requests[req_id]
                    captured = True
                    # Webhook push
                    key = rd.get('key', '')
                    threading.Thread(target=send_webhook, args=(key, {
                        "status": True,
                        "original_link": final_orig,
                        "bypassed_link": bypassed,
                        "req_id": req_id
                    }), daemon=True).start()
                    break

        if captured and bypassed:
            with cache_lock:
                bypass_cache[captured_orig] = bypassed
            save_data()
            asyncio.ensure_future(save_to_channel(captured_orig, bypassed, acc['name']))

    return handler

# ==================== SEND TO GROUP ====================
async def send_to_group(link, client_obj):
    from telethon.errors import ChatWriteForbiddenError, UserNotParticipantError
    try:
        await client_obj.send_message(TARGET_GROUP, link)
    except (ChatWriteForbiddenError, UserNotParticipantError):
        try:
            await client_obj(JoinChannelRequest(TARGET_GROUP))
            await asyncio.sleep(2)
            await client_obj.send_message(TARGET_GROUP, link)
        except Exception as join_err:
            raise Exception(f"Group write failed: {join_err}")

# ==================== RESPONSE FORMATS ====================
def ok_response(orig, bypassed, key, key_type, from_cache=False):
    return {
        "status": True, "message": "API Request Successful",
        "developer": API_OWNER,
        "request": {"original_link": orig},
        "response": {"bypassed_link": bypassed},
        "from_cache": from_cache,
        "stats": stats_dict(),
    }

def err_response(error, key="", link=None):
    return {
        "status": False, "message": "API Request Failed",
        "developer": API_OWNER, "error": error,
        "request": {"original_link": link},
        "stats": stats_dict(),
    }

# ==================== ADMIN LOGIN DECORATOR ====================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not flask_session.get('admin_logged_in'):
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated


# ==================== HOME PAGE HTML ====================
HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>THE FELIX BYPASS</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#03050f;--s1:#070b18;--s2:#0a1020;
  --border:#111827;--accent:#6366f1;--accent2:#818cf8;
  --pink:#ec4899;--green:#10b981;--yellow:#f59e0b;
  --red:#ef4444;--text:#f1f5f9;--muted:#64748b;--dim:#1e293b;
}
body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(ellipse 80% 50% at 50% -20%,rgba(99,102,241,0.15),transparent),
  radial-gradient(ellipse 60% 40% at 80% 80%,rgba(236,72,153,0.08),transparent);
  pointer-events:none;z-index:0}

/* GRID LINES */
body::after{content:'';position:fixed;inset:0;
  background-image:linear-gradient(rgba(99,102,241,0.05) 1px,transparent 1px),linear-gradient(90deg,rgba(99,102,241,0.05) 1px,transparent 1px);
  background-size:80px 80px;pointer-events:none;z-index:0}

/* ADMIN BADGE — top right corner */
.admin-badge{
  position:fixed;top:16px;right:16px;z-index:1000;
  background:rgba(10,16,32,0.9);border:1px solid rgba(99,102,241,0.4);
  backdrop-filter:blur(12px);border-radius:10px;
  padding:7px 14px;font-size:12px;font-weight:700;color:var(--accent2);
  text-decoration:none;letter-spacing:.5px;
  transition:all .2s;display:flex;align-items:center;gap:6px
}
.admin-badge:hover{border-color:var(--accent);box-shadow:0 0 20px rgba(99,102,241,0.3);color:#fff}

/* HERO */
.hero{position:relative;z-index:5;text-align:center;padding:90px 24px 50px}
.hero-tag{display:inline-flex;align-items:center;gap:8px;background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);border-radius:100px;padding:6px 18px;font-size:12px;color:var(--accent2);margin-bottom:28px;letter-spacing:1px;text-transform:uppercase;font-weight:600}
.hero-tag .dot{width:6px;height:6px;background:var(--green);border-radius:50%;animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1;box-shadow:0 0 6px var(--green)}50%{opacity:.4;box-shadow:none}}

.hero h1{font-size:clamp(38px,8vw,80px);font-weight:800;line-height:1.05;letter-spacing:-2px;margin-bottom:20px}
.hero h1 .line1{display:block;color:var(--text)}
.hero h1 .line2{display:block;background:linear-gradient(135deg,var(--accent),var(--pink));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.hero-sub{font-size:16px;color:var(--muted);max-width:460px;margin:0 auto 0;line-height:1.7;font-weight:400}

/* FREE WIDGET — moved to top */
.free-wrap{position:relative;z-index:5;max-width:680px;margin:36px auto 60px;padding:0 20px}
.free-card{background:rgba(7,11,24,0.9);border:1px solid rgba(99,102,241,0.25);border-radius:20px;overflow:hidden;backdrop-filter:blur(20px);box-shadow:0 0 60px rgba(99,102,241,0.08)}
.free-header{background:linear-gradient(135deg,rgba(99,102,241,0.12),rgba(236,72,153,0.08));border-bottom:1px solid rgba(99,102,241,0.15);padding:18px 24px;display:flex;align-items:center;justify-content:space-between}
.free-title{font-size:15px;font-weight:700;display:flex;align-items:center;gap:8px}
.free-badge{background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);color:var(--green);padding:4px 12px;border-radius:100px;font-size:11px;font-weight:700;letter-spacing:.5px}
.free-body{padding:22px 24px}
.input-row{display:flex;gap:10px}
.free-input{flex:1;background:#0a1020;border:1px solid #1e2d45;color:var(--text);padding:13px 16px;border-radius:12px;font-family:'JetBrains Mono',monospace;font-size:13px;outline:none;transition:border-color .2s}
.free-input:focus{border-color:var(--accent)}
.free-input:disabled{opacity:.4}
.free-btn{padding:13px 22px;background:linear-gradient(135deg,var(--accent),var(--pink));color:#fff;border:none;border-radius:12px;font-family:'Syne',sans-serif;font-weight:700;font-size:14px;cursor:pointer;transition:all .2s;white-space:nowrap}
.free-btn:hover{opacity:.9;transform:translateY(-1px);box-shadow:0 8px 30px rgba(99,102,241,0.35)}
.free-btn:disabled{opacity:.5;cursor:not-allowed;transform:none}
.free-status{display:none;margin-top:14px;padding:11px 15px;border-radius:10px;font-size:13px}
.status-ok{background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);color:#6ee7b7}
.status-err{background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);color:#fca5a5}
.free-result{display:none;margin-top:14px;background:#0a1020;border:1px solid #1e2d45;border-radius:12px;padding:16px}
.result-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;font-weight:600}
.result-link{font-family:'JetBrains Mono',monospace;font-size:12px;color:#86efac;word-break:break-all;line-height:1.6}
.copy-btn{margin-top:10px;padding:7px 16px;background:#111827;color:var(--muted);border:1px solid #1e2d45;border-radius:8px;font-size:12px;cursor:pointer;transition:all .2s}
.copy-btn:hover{color:var(--text);border-color:var(--accent)}
.counter-row{margin-top:14px;display:flex;align-items:center;gap:10px;font-size:12px;color:var(--muted)}
.dots-bar{display:flex;gap:4px}
.dot-pip{width:20px;height:5px;border-radius:3px;background:#1e2d45;transition:background .3s}
.dot-pip.used{background:linear-gradient(90deg,var(--accent),var(--pink))}

/* BUY BANNER */
.buy-banner{display:none;margin-top:16px;background:linear-gradient(135deg,rgba(99,102,241,0.1),rgba(236,72,153,0.1));border:1px solid rgba(99,102,241,0.3);border-radius:14px;padding:22px;text-align:center}
.buy-icon{font-size:28px;margin-bottom:10px}
.buy-title{font-size:18px;font-weight:800;margin-bottom:6px}
.buy-sub{color:var(--muted);font-size:13px;margin-bottom:18px;line-height:1.6}
.buy-btn{display:inline-flex;align-items:center;gap:8px;background:linear-gradient(135deg,var(--accent),var(--pink));color:#fff;padding:13px 30px;border-radius:12px;font-weight:700;font-size:14px;text-decoration:none;transition:all .2s}
.buy-btn:hover{opacity:.9;transform:translateY(-1px);box-shadow:0 8px 30px rgba(99,102,241,0.4)}
.buy-note{margin-top:10px;font-size:11px;color:var(--muted)}

/* STATS ROW */
.stats-row{position:relative;z-index:5;display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:rgba(99,102,241,0.1);border-top:1px solid rgba(99,102,241,0.1);border-bottom:1px solid rgba(99,102,241,0.1);margin-bottom:80px}
.stat-item{background:var(--bg);padding:28px 16px;text-align:center}
.stat-num{font-size:36px;font-weight:700;letter-spacing:-1px;font-family:'JetBrains Mono',monospace;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.stat-lbl{font-size:11px;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:1.5px;font-weight:600}

/* HOW IT WORKS */
.section{position:relative;z-index:5;max-width:1100px;margin:0 auto 80px;padding:0 24px}
.section-head{text-align:center;margin-bottom:48px}
.section-head h2{font-size:clamp(28px,5vw,40px);font-weight:800;margin-bottom:10px;letter-spacing:-1px}
.section-head p{color:var(--muted);font-size:15px}
.features-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.feat{background:var(--s1);border:1px solid var(--border);border-radius:16px;padding:28px;transition:all .25s;position:relative;overflow:hidden}
.feat::before{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(99,102,241,0.03),transparent);pointer-events:none}
.feat:hover{border-color:rgba(99,102,241,0.4);transform:translateY(-3px);box-shadow:0 12px 40px rgba(99,102,241,0.1)}
.feat-icon{width:46px;height:46px;background:rgba(99,102,241,0.1);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:16px}
.feat h3{font-size:16px;font-weight:700;margin-bottom:8px}
.feat p{color:var(--muted);font-size:13px;line-height:1.7;font-weight:400}

/* CODE BOX */
.code-box{max-width:680px;margin:0 auto 80px;padding:0 24px;position:relative;z-index:5}
.code-card{background:var(--s1);border:1px solid var(--border);border-radius:18px;overflow:hidden}
.code-header{display:flex;align-items:center;gap:8px;padding:14px 20px;border-bottom:1px solid var(--border);background:var(--s2)}
.code-dot{width:11px;height:11px;border-radius:50%}
.code-url{flex:1;text-align:center;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted)}
.code-body{padding:22px 26px;font-family:'JetBrains Mono',monospace;font-size:12px;line-height:1.9;overflow-x:auto}
.c-dim{color:#475569}.c-key{color:#93c5fd}.c-val{color:#86efac}.c-str{color:#fde68a}.c-url{color:var(--accent2)}

/* ENDPOINTS */
.endpoints{display:flex;flex-direction:column;gap:8px}
.ep{display:flex;align-items:center;gap:14px;background:var(--s1);border:1px solid var(--border);border-radius:12px;padding:14px 18px;font-family:'JetBrains Mono',monospace;font-size:12px;transition:border-color .2s}
.ep:hover{border-color:rgba(99,102,241,0.3)}
.method{padding:4px 10px;border-radius:6px;font-size:10px;font-weight:700;min-width:42px;text-align:center}
.get{background:rgba(16,185,129,0.12);color:var(--green)}
.post{background:rgba(99,102,241,0.12);color:var(--accent2)}
.ep-path{color:var(--text);flex:1}
.ep-desc{color:var(--muted);font-size:11px;font-family:'Syne',sans-serif}

/* FOOTER */
footer{position:relative;z-index:5;border-top:1px solid var(--border);padding:28px 24px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;color:var(--muted);font-size:13px}
footer a{color:var(--accent2);text-decoration:none}
</style>
</head>
<body>

<!-- ADMIN BADGE top-right -->
<a href="/admin" class="admin-badge">⚙ Admin</a>

<!-- HERO -->
<div class="hero">
  <div class="hero-tag"><span class="dot"></span>System Online &amp; Ready</div>
  <h1>
    <span class="line1">THE FELIX</span>
    <span class="line2">BYPASS</span>
  </h1>
  <p class="hero-sub">Lightning-fast link bypasser with multi-account rotation, smart caching &amp; real-time monitoring.</p>
</div>

<!-- FREE BYPASS WIDGET — TOP -->
<div class="free-wrap">
  <div class="free-card">
    <div class="free-header">
      <div class="free-title">⚡ Try Free Bypass</div>
      <span class="free-badge">10 FREE / DAY</span>
    </div>
    <div class="free-body">
      <div class="input-row">
        <input id="free-link-input" class="free-input" type="text" placeholder="Paste your link here...">
        <button id="free-bypass-btn" class="free-btn" onclick="doFreeBypass()">Bypass →</button>
      </div>
      <div id="free-status" class="free-status"></div>
      <div id="free-result" class="free-result">
        <div class="result-lbl">Bypassed Link</div>
        <div id="free-result-link" class="result-link"></div>
        <button class="copy-btn" onclick="copyFreeResult()">📋 Copy Link</button>
      </div>
      <!-- counter dots -->
      <div class="counter-row">
        <div class="dots-bar" id="dots-bar"></div>
        <span id="free-counter-txt" style="font-size:12px;color:var(--muted)">10 searches left today</span>
      </div>
      <!-- BUY BANNER -->
      <div class="buy-banner" id="buy-banner">
        <div class="buy-icon">🔑</div>
        <div class="buy-title">Daily Limit Reached!</div>
        <div class="buy-sub">Aapki 10 free searches khatam ho gayi.<br>Unlimited bypass ke liye API key lo!</div>
        <a href="https://t.me/mikey_bhai1" target="_blank" class="buy-btn">📩 Buy API Key — @mikey_bhai1</a>
        <div class="buy-note">Telegram pe message karo • Fast response guaranteed</div>
      </div>
    </div>
  </div>
</div>

<script>
const FREE_LIMIT = 10;
const FREE_STORE_KEY = "felix_free_v2";

function getFreeState() {
  try {
    const raw = localStorage.getItem(FREE_STORE_KEY);
    if (!raw) return { used: 0, date: new Date().toDateString() };
    const s = JSON.parse(raw);
    if (s.date !== new Date().toDateString()) return { used: 0, date: new Date().toDateString() };
    return s;
  } catch(e) { return { used: 0, date: new Date().toDateString() }; }
}
function saveFreeState(s) {
  try { localStorage.setItem(FREE_STORE_KEY, JSON.stringify(s)); } catch(e) {}
}

function renderDots(used) {
  const bar = document.getElementById('dots-bar');
  bar.innerHTML = '';
  for (let i = 0; i < FREE_LIMIT; i++) {
    const d = document.createElement('div');
    d.className = 'dot-pip' + (i < used ? ' used' : '');
    bar.appendChild(d);
  }
}

function updateCounter() {
  const s = getFreeState();
  const left = Math.max(0, FREE_LIMIT - s.used);
  renderDots(s.used);
  const txt = document.getElementById('free-counter-txt');
  if (left === 0) {
    txt.innerHTML = '<span style="color:#f87171">❌ Limit reached today</span>';
    document.getElementById('free-bypass-btn').disabled = true;
    document.getElementById('free-bypass-btn').style.opacity = '0.5';
    document.getElementById('free-link-input').disabled = true;
    document.getElementById('buy-banner').style.display = 'block';
  } else if (left <= 3) {
    txt.innerHTML = '<span style="color:#fbbf24">⚠️ ' + left + ' searches baaki — <a href="https://t.me/mikey_bhai1" target="_blank" style="color:var(--accent2)">Key lo →</a></span>';
  } else {
    txt.textContent = left + ' searches left today';
  }
}

function showStatus(msg, ok) {
  const el = document.getElementById('free-status');
  el.style.display = 'block';
  el.className = 'free-status ' + (ok ? 'status-ok' : 'status-err');
  el.textContent = msg;
}

async function doFreeBypass() {
  const s = getFreeState();
  if (s.used >= FREE_LIMIT) { showStatus('Daily limit reached! Buy API key.', false); return; }
  const link = document.getElementById('free-link-input').value.trim();
  if (!link) { showStatus('Please paste a link first.', false); return; }
  const btn = document.getElementById('free-bypass-btn');
  btn.textContent = '⏳ Bypassing...';
  btn.disabled = true;
  document.getElementById('free-result').style.display = 'none';
  document.getElementById('free-status').style.display = 'none';
  try {
    const resp = await fetch('/bypass?key=FREE_DAILY_GUEST&link=' + encodeURIComponent(link));
    const data = await resp.json();
    if (data.status && data.response && data.response.bypassed_link) {
      s.used += 1; saveFreeState(s); updateCounter();
      document.getElementById('free-result-link').textContent = data.response.bypassed_link;
      document.getElementById('free-result').style.display = 'block';
      showStatus('✅ Bypass successful!', true);
    } else {
      showStatus('❌ ' + (data.error || 'Bypass failed. Try a different link.'), false);
    }
  } catch(e) { showStatus('❌ Network error. Please try again.', false); }
  btn.textContent = 'Bypass →';
  btn.disabled = getFreeState().used >= FREE_LIMIT;
  updateCounter();
}

function copyFreeResult() {
  const txt = document.getElementById('free-result-link').textContent;
  navigator.clipboard.writeText(txt).then(() => showStatus('✅ Copied!', true)).catch(() => showStatus('Select and copy manually.', false));
}
updateCounter();
</script>

<!-- STATS -->
<div class="stats-row">
  <div class="stat-item"><div class="stat-num">{{ stats.total_requests }}</div><div class="stat-lbl">Total Requests</div></div>
  <div class="stat-item"><div class="stat-num" style="background:linear-gradient(135deg,var(--green),#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:'JetBrains Mono',monospace">{{ stats.successful_requests }}</div><div class="stat-lbl">Successful</div></div>
  <div class="stat-item"><div class="stat-num" style="background:linear-gradient(135deg,var(--yellow),#fcd34d);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:'JetBrains Mono',monospace">{{ stats.success_rate }}%</div><div class="stat-lbl">Success Rate</div></div>
  <div class="stat-item"><div class="stat-num">{{ cache_size }}</div><div class="stat-lbl">Cache Entries</div></div>
  <div class="stat-item"><div class="stat-num" style="background:linear-gradient(135deg,var(--green),#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:'JetBrains Mono',monospace">{{ connected }}/{{ total_acc }}</div><div class="stat-lbl">Accounts Online</div></div>
</div>

<!-- CODE EXAMPLE -->
<div class="code-box">
  <div class="code-card">
    <div class="code-header">
      <div class="code-dot" style="background:#ef4444"></div>
      <div class="code-dot" style="background:#f59e0b"></div>
      <div class="code-dot" style="background:#22c55e"></div>
      <div class="code-url">GET /bypass?key=YOUR_KEY&amp;link=URL</div>
    </div>
    <div class="code-body">
<span class="c-dim">// Response</span><br>
{<br>
&nbsp;&nbsp;<span class="c-key">"status"</span>: <span class="c-val">true</span>,<br>
&nbsp;&nbsp;<span class="c-key">"message"</span>: <span class="c-str">"API Request Successful"</span>,<br>
&nbsp;&nbsp;<span class="c-key">"request"</span>: { <span class="c-key">"original_link"</span>: <span class="c-str">"https://gplinks.in/..."</span> },<br>
&nbsp;&nbsp;<span class="c-key">"response"</span>: { <span class="c-key">"bypassed_link"</span>: <span class="c-url">"https://drive.google.com/..."</span> },<br>
&nbsp;&nbsp;<span class="c-key">"from_cache"</span>: <span class="c-val">false</span><br>
}
    </div>
  </div>
</div>

<!-- FEATURES -->
<div class="section">
  <div class="section-head"><h2>Why Felix Bypass?</h2><p>Built for speed, reliability and smart automation</p></div>
  <div class="features-grid">
    <div class="feat"><div class="feat-icon">⚡</div><h3>Smart Cache</h3><p>Previously bypassed links return instantly — zero wait time for repeated links.</p></div>
    <div class="feat"><div class="feat-icon">🔄</div><h3>Account Rotation</h3><p>Auto-rotation across multiple Telegram accounts with blacklist recovery.</p></div>
    <div class="feat"><div class="feat-icon">🔑</div><h3>Key Management</h3><p>Temporary or permanent API keys with expiry, IP whitelist and usage tracking.</p></div>
    <div class="feat"><div class="feat-icon">📊</div><h3>Full Monitoring</h3><p>Real-time stats, per-key usage logs and account health dashboard.</p></div>
    <div class="feat"><div class="feat-icon">🛡️</div><h3>Rate Limiting</h3><p>Per-key rate limiting protects the API from abuse — {{ rate_limit }} req/min default.</p></div>
    <div class="feat"><div class="feat-icon">📡</div><h3>Webhooks</h3><p>Push bypass results to your own endpoint instantly after completion.</p></div>
  </div>
</div>

<!-- ENDPOINTS -->
<div class="section">
  <div class="section-head"><h2>API Endpoints</h2><p>Simple REST API — works with GET or POST</p></div>
  <div class="endpoints">
    <div class="ep"><span class="method get">GET</span><span class="ep-path">/bypass?key=KEY&amp;link=URL</span><span class="ep-desc">Bypass a link</span></div>
    <div class="ep"><span class="method get">GET</span><span class="ep-path">/stats</span><span class="ep-desc">Global API statistics</span></div>
    <div class="ep"><span class="method get">GET</span><span class="ep-path">/health</span><span class="ep-desc">Account health status</span></div>
    <div class="ep"><span class="method post">POST</span><span class="ep-path">/webhook/set</span><span class="ep-desc">Set webhook for key</span></div>
    <div class="ep"><span class="method get">GET</span><span class="ep-path">/admin</span><span class="ep-desc">Admin dashboard (login required)</span></div>
  </div>
</div>

<footer>
  <div>THE FELIX BYPASS v{{ version }} — by <a href="https://t.me/Felix_modz1">{{ owner }}</a></div>
  <div>All rights reserved &copy; 2026</div>
</footer>
</body>
</html>"""

# ==================== LOGIN PAGE HTML ====================
LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login — Felix Bypass</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{min-height:100vh;background:#050810;display:flex;align-items:center;justify-content:center;font-family:'Space Grotesk',sans-serif;color:#e2e8f0}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(59,130,246,0.04) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,0.04) 1px,transparent 1px);background-size:60px 60px;pointer-events:none}
.orb{position:fixed;border-radius:50%;filter:blur(120px);pointer-events:none}
.orb1{width:500px;height:500px;background:rgba(59,130,246,0.07);top:-150px;right:-100px}
.orb2{width:350px;height:350px;background:rgba(139,92,246,0.05);bottom:-100px;left:-80px}
.card{position:relative;z-index:10;background:#080d1a;border:1px solid #162035;border-radius:20px;padding:48px 44px;width:420px;box-shadow:0 0 80px rgba(0,0,0,0.5)}
.logo-wrap{text-align:center;margin-bottom:36px}
.logo-icon{width:56px;height:56px;background:rgba(59,130,246,0.12);border:1px solid rgba(59,130,246,0.2);border-radius:16px;display:flex;align-items:center;justify-content:center;font-size:24px;margin:0 auto 16px}
.logo-title{font-size:22px;font-weight:700;letter-spacing:-.3px}
.logo-sub{font-size:13px;color:#64748b;margin-top:4px}
label{display:block;font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
input[type=text],input[type=password]{width:100%;background:#0c1525;border:1px solid #162035;color:#e2e8f0;padding:13px 16px;border-radius:10px;font-family:'JetBrains Mono',monospace;font-size:14px;outline:none;transition:border-color .2s,box-shadow .2s;margin-bottom:20px}
input:focus{border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,0.1)}
button{width:100%;padding:14px;background:#3b82f6;color:#fff;border:none;border-radius:10px;font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:15px;cursor:pointer;transition:all .2s;margin-top:4px}
button:hover{background:#60a5fa;box-shadow:0 0 30px rgba(59,130,246,0.35);transform:translateY(-1px)}
.err{background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.3);color:#f87171;padding:12px 16px;border-radius:10px;font-size:13px;margin-bottom:20px;text-align:center}
.back{text-align:center;margin-top:20px;font-size:13px;color:#64748b}
.back a{color:#3b82f6;text-decoration:none}
.back a:hover{color:#60a5fa}
</style>
</head>
<body>
<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="card">
  <div class="logo-wrap">
    <div class="logo-icon">🔐</div>
    <div class="logo-title">Admin Login</div>
    <div class="logo-sub">Felix Bypass API · Secure Access</div>
  </div>
  {% if error %}<div class="err">⚠️ {{ error }}</div>{% endif %}
  <form method="POST">
    <label>Username</label>
    <input type="text" name="username" autocomplete="off" placeholder="Enter username" required>
    <label>Password</label>
    <input type="password" name="password" placeholder="Enter password" required>
    <button type="submit">Login to Dashboard →</button>
  </form>
  <div class="back"><a href="/">← Back to Home</a></div>
</div>
</body>
</html>"""

# ==================== ADMIN DASHBOARD HTML ====================
ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Dashboard — Felix Bypass</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--bg:#050810;--s1:#080d1a;--s2:#0c1525;--border:#162035;--accent:#3b82f6;--green:#22c55e;--red:#ef4444;--yellow:#f59e0b;--purple:#a78bfa;--text:#e2e8f0;--muted:#64748b;--dim:#1e293b}
body{background:var(--bg);color:var(--text);font-family:'Space Grotesk',sans-serif;min-height:100vh;display:flex}
/* SIDEBAR */
.sidebar{width:240px;min-height:100vh;background:var(--s1);border-right:1px solid var(--border);display:flex;flex-direction:column;flex-shrink:0;position:fixed;top:0;left:0;height:100vh;overflow-y:auto}
.sb-logo{padding:24px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.sb-logo .dot{width:8px;height:8px;background:var(--accent);border-radius:50%;box-shadow:0 0 10px var(--accent)}
.sb-logo span{font-weight:700;font-size:15px}
.sb-section{padding:20px 12px 8px;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px}
.sb-link{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;text-decoration:none;color:var(--muted);font-size:14px;font-weight:500;transition:all .15s;margin-bottom:2px}
.sb-link:hover,.sb-link.active{background:rgba(59,130,246,0.1);color:var(--text)}
.sb-link.active{color:var(--accent)}
.sb-link .icon{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:15px;background:var(--s2)}
.sb-link.active .icon{background:rgba(59,130,246,0.15)}
.sb-bottom{margin-top:auto;padding:16px 12px;border-top:1px solid var(--border)}
.sb-user{display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;background:var(--s2)}
.sb-user .av{width:32px;height:32px;background:var(--accent);border-radius:8px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;color:#fff}
.sb-user .name{font-size:13px;font-weight:600}
.sb-user .role{font-size:11px;color:var(--muted)}
.sb-logout{display:flex;align-items:center;gap:8px;padding:10px 12px;border-radius:8px;color:var(--muted);text-decoration:none;font-size:13px;margin-top:8px;transition:all .15s}
.sb-logout:hover{background:rgba(239,68,68,0.1);color:var(--red)}
/* MAIN */
.main{margin-left:240px;flex:1;min-height:100vh;display:flex;flex-direction:column}
.topbar{padding:16px 32px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--s1);position:sticky;top:0;z-index:50}
.topbar-title{font-size:18px;font-weight:700}
.topbar-right{display:flex;align-items:center;gap:12px}
.status-badge{display:flex;align-items:center;gap:6px;background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);border-radius:100px;padding:6px 14px;font-size:12px;font-weight:600;color:var(--green)}
.pulse{width:6px;height:6px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,0.4)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
.content{padding:28px 32px;flex:1}
/* ALERTS */
.alert{padding:14px 18px;border-radius:10px;margin-bottom:20px;font-size:14px;display:flex;align-items:center;gap:10px}
.alert-ok{background:rgba(34,197,94,0.08);border:1px solid rgba(34,197,94,0.2);color:var(--green)}
.alert-err{background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);color:var(--red)}
/* STATS GRID */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:28px}
.stat-card{background:var(--s1);border:1px solid var(--border);border-radius:14px;padding:22px;transition:all .2s;position:relative;overflow:hidden}
.stat-card::after{content:'';position:absolute;inset:0;background:linear-gradient(135deg,rgba(59,130,246,0.03),transparent);pointer-events:none}
.stat-card:hover{border-color:var(--accent);transform:translateY(-1px)}
.stat-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px}
.stat-value{font-size:32px;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:-1px}
.stat-value.blue{color:var(--accent)}.stat-value.green{color:var(--green)}.stat-value.red{color:var(--red)}.stat-value.yellow{color:var(--yellow)}.stat-value.purple{color:var(--purple)}
/* CARDS */
.card{background:var(--s1);border:1px solid var(--border);border-radius:14px;margin-bottom:20px;overflow:hidden}
.card-header{padding:16px 22px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between}
.card-title{font-size:14px;font-weight:700;display:flex;align-items:center;gap:8px}
.card-body{padding:22px}
/* ACCOUNT ROWS */
.acc-row{display:flex;align-items:center;justify-content:space-between;padding:14px 0;border-bottom:1px solid var(--border)}
.acc-row:last-child{border-bottom:none}
.acc-name{font-weight:600;font-size:14px;margin-bottom:4px}
.acc-meta{font-size:12px;color:var(--muted);font-family:'JetBrains Mono',monospace}
/* BADGES */
.badge{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:100px;font-size:11px;font-weight:700;letter-spacing:.3px}
.badge-green{background:rgba(34,197,94,0.1);color:var(--green)}
.badge-red{background:rgba(239,68,68,0.1);color:var(--red)}
.badge-yellow{background:rgba(245,158,11,0.1);color:var(--yellow)}
.badge-blue{background:rgba(59,130,246,0.1);color:var(--accent)}
.badge-purple{background:rgba(167,139,250,0.1);color:var(--purple)}
/* FORM */
.form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin-bottom:16px}
.form-group label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}
input[type=text],input[type=number],input[type=password],select{width:100%;background:var(--s2);border:1px solid var(--border);color:var(--text);padding:11px 14px;border-radius:8px;font-family:'JetBrains Mono',monospace;font-size:13px;outline:none;transition:border-color .2s}
input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(59,130,246,0.08)}
.btn{display:inline-flex;align-items:center;gap:6px;padding:10px 18px;border:none;border-radius:8px;cursor:pointer;font-family:'Space Grotesk',sans-serif;font-weight:600;font-size:13px;transition:all .15s}
.btn-blue{background:var(--accent);color:#fff}.btn-blue:hover{background:#60a5fa;box-shadow:0 0 20px rgba(59,130,246,0.3)}
.btn-red{background:rgba(239,68,68,0.12);color:var(--red);border:1px solid rgba(239,68,68,0.2)}.btn-red:hover{background:var(--red);color:#fff}
.btn-ghost{background:var(--s2);color:var(--muted);border:1px solid var(--border)}.btn-ghost:hover{color:var(--text);border-color:var(--accent)}
.btn-sm{padding:6px 12px;font-size:12px}
.btn-green{background:rgba(34,197,94,0.12);color:var(--green);border:1px solid rgba(34,197,94,0.2)}.btn-green:hover{background:var(--green);color:#000}
/* NEW KEY BOX */
.new-key-box{background:rgba(34,197,94,0.05);border:1px solid rgba(34,197,94,0.2);border-radius:10px;padding:18px;margin-top:16px}
.new-key-label{font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:8px}
.new-key-val{font-family:'JetBrains Mono',monospace;font-size:15px;color:var(--green);word-break:break-all;margin-bottom:6px}
.new-key-exp{font-size:12px;color:var(--muted)}
/* TABLE */
.tbl-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse;font-size:13px}
th{padding:10px 14px;text-align:left;color:var(--muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:1px;border-bottom:1px solid var(--border);background:var(--s2)}
td{padding:13px 14px;border-bottom:1px solid rgba(22,32,53,0.5);font-family:'JetBrains Mono',monospace;vertical-align:middle}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(59,130,246,0.02)}
/* CACHE LIST */
.cache-list{max-height:280px;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:12px}
.cache-row{display:flex;gap:12px;padding:8px 0;border-bottom:1px solid rgba(22,32,53,0.5);align-items:flex-start}
.cache-row:last-child{border-bottom:none}
.cache-orig{color:var(--muted);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cache-arr{color:var(--border);flex-shrink:0}
.cache-by{color:var(--green);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
/* SCROLLBAR */
::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--s1)}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:4px}
/* LOG SELECT */
.log-select-row{display:flex;gap:10px;align-items:flex-end;margin-bottom:16px}
.log-select-row select{flex:1}
/* SECTION TABS - for nav */
.tab-nav{display:flex;gap:4px;margin-bottom:24px;border-bottom:1px solid var(--border);padding-bottom:0}
.tab-link{padding:10px 16px;font-size:13px;font-weight:600;color:var(--muted);text-decoration:none;border-bottom:2px solid transparent;transition:all .15s;margin-bottom:-1px}
.tab-link:hover{color:var(--text)}
.tab-link.active{color:var(--accent);border-bottom-color:var(--accent)}
</style>
</head>
<body>

<!-- SIDEBAR -->
<div class="sidebar">
  <div class="sb-logo"><div class="dot"></div><span>Felix Bypass</span></div>

  <div class="sb-section">Overview</div>
  <a href="/admin" class="sb-link active"><div class="icon">📊</div>Dashboard</a>
  <a href="/health" class="sb-link"><div class="icon">💚</div>Health Check</a>
  <a href="/stats" class="sb-link"><div class="icon">📈</div>API Stats</a>

  <div class="sb-section">Management</div>
  <a href="/admin#keys" class="sb-link"><div class="icon">🔑</div>API Keys</a>
  <a href="/admin#accounts" class="sb-link"><div class="icon">👤</div>Accounts</a>
  <a href="/admin#cache" class="sb-link"><div class="icon">⚡</div>Cache</a>
  <a href="/admin#logs" class="sb-link"><div class="icon">📋</div>Usage Logs</a>

  <div class="sb-section">Links</div>
  <a href="/bypassed-links" class="sb-link"><div class="icon">🔗</div>Bypassed Links</a>
  <a href="/" class="sb-link"><div class="icon">🌐</div>Homepage</a>

  <div class="sb-bottom">
    <div class="sb-user">
      <div class="av">A</div>
      <div><div class="name">Admin</div><div class="role">Felix Bypass</div></div>
    </div>
    <a href="/admin/logout" class="sb-logout">⏻ Logout</a>
  </div>
</div>

<!-- MAIN -->
<div class="main">
  <div class="topbar">
    <div class="topbar-title">Dashboard</div>
    <div class="topbar-right">
      <div class="status-badge"><span class="pulse"></span>System Online</div>
    </div>
  </div>

  <div class="content">
    {% if flash_ok %}<div class="alert alert-ok">✅ {{ flash_ok }}</div>{% endif %}
    {% if flash_err %}<div class="alert alert-err">❌ {{ flash_err }}</div>{% endif %}

    <!-- STATS -->
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-label">Total Requests</div><div class="stat-value blue">{{ stats.total_requests }}</div></div>
      <div class="stat-card"><div class="stat-label">Successful</div><div class="stat-value green">{{ stats.successful_requests }}</div></div>
      <div class="stat-card"><div class="stat-label">Failed</div><div class="stat-value red">{{ stats.failed_requests }}</div></div>
      <div class="stat-card"><div class="stat-label">Success Rate</div><div class="stat-value yellow">{{ stats.success_rate }}%</div></div>
      <div class="stat-card"><div class="stat-label">Cache Entries</div><div class="stat-value purple">{{ cache_size }}</div></div>
      <div class="stat-card"><div class="stat-label">Active Keys</div><div class="stat-value blue">{{ active_keys }}</div></div>
    </div>

    <!-- ACCOUNTS -->
    <div class="card" id="accounts">
      <div class="card-header">
        <div class="card-title">👤 Telegram Accounts</div>
      </div>
      <div class="card-body" style="padding:0 22px">
        {% for acc in accounts %}
        <div class="acc-row">
          <div>
            <div class="acc-name">{{ acc.name }}</div>
            <div class="acc-meta">Links this turn: {{ acc.count }}/{{ links_per }} {% if acc.blacklisted_at %}· Blacklisted: {{ acc.blacklisted_at[:16] }}{% endif %}</div>
          </div>
          <div style="display:flex;gap:8px;align-items:center">
            <span class="badge {{ 'badge-red' if acc.blacklisted else 'badge-green' }}">
              {{ '🚫 Blacklisted' if acc.blacklisted else '✅ Active' }}
            </span>
            {% if acc.blacklisted %}
            <form method="POST" action="/admin/reset_account" style="display:inline">
              <input type="hidden" name="acc_name" value="{{ acc.name }}">
              <button class="btn btn-green btn-sm">Reset</button>
            </form>
            {% endif %}
          </div>
        </div>
        {% endfor %}
      </div>
    </div>

    <!-- ADD ACCOUNT -->
    <div class="card" id="add-account">
      <div class="card-header"><div class="card-title">➕ Add Telegram Account</div></div>
      <div class="card-body">
        <form method="POST" action="/admin/add_account">
          <div class="form-grid">
            <div class="form-group"><label>Account Name (e.g. @Username)</label><input type="text" name="acc_name" placeholder="@NewAccount" required></div>
            <div class="form-group"><label>API ID</label><input type="text" name="api_id" placeholder="12345678" required></div>
            <div class="form-group"><label>API Hash</label><input type="text" name="api_hash" placeholder="abcdef1234..." required></div>
            <div class="form-group"><label>String Session</label><input type="text" name="session" placeholder="1BVtsO..." required></div>
          </div>
          <button class="btn btn-blue">➕ Add Account</button>
        </form>
      </div>
    </div>

    <!-- GENERATE KEY -->
    <div class="card" id="keys">
      <div class="card-header"><div class="card-title">🔑 Generate API Key</div></div>
      <div class="card-body">
        <form method="POST" action="/admin/genkey">
          <div class="form-grid">
            <div class="form-group"><label>Days Valid</label><input type="number" name="days" value="1" min="1" max="90"></div>
            <div class="form-group"><label>IP Whitelist (comma sep.)</label><input type="text" name="ip_whitelist" placeholder="e.g. 1.2.3.4, 5.6.7.8"></div>
            <div class="form-group"><label>Telegram Notify ID</label><input type="text" name="tg_notify_id" placeholder="123456789"></div>
            <div class="form-group"><label>Webhook URL</label><input type="text" name="webhook_url" placeholder="https://your-site.com/hook"></div>
          </div>
          <button class="btn btn-blue">⚡ Generate Key</button>
        </form>
        {% if new_key %}
        <div class="new-key-box">
          <div class="new-key-label">✅ Key Generated Successfully</div>
          <div class="new-key-val">{{ new_key }}</div>
          <div class="new-key-exp">Expires: {{ new_key_exp }}</div>
        </div>
        {% endif %}
      </div>
    </div>

    <!-- KEYS TABLE -->
    <div class="card">
      <div class="card-header"><div class="card-title">📋 All API Keys</div></div>
      <div class="tbl-wrap">
        <table>
          <thead><tr><th>Key</th><th>Type</th><th>Status</th><th>Expires</th><th>Used</th><th>IP Whitelist</th><th>Actions</th></tr></thead>
          <tbody>
            {% for k in all_keys %}
            <tr>
              <td style="color:var(--yellow)">{{ k.key[:10] }}…{{ k.key[-6:] }}</td>
              <td><span class="badge {{ 'badge-purple' if k.type == 'permanent' else 'badge-blue' }}">{{ k.type }}</span></td>
              <td><span class="badge {{ 'badge-green' if k.status == 'active' else 'badge-red' }}">{{ k.status }}</span></td>
              <td style="color:var(--muted)">{{ k.expires_at }}</td>
              <td>{{ k.total_used }}</td>
              <td style="color:var(--muted);font-size:11px">{{ k.ip_whitelist or '—' }}</td>
              <td>
                {% if k.type != 'permanent' and k.status == 'active' %}
                <form method="POST" action="/admin/expirekey" style="display:inline">
                  <input type="hidden" name="key" value="{{ k.key }}">
                  <button class="btn btn-red btn-sm">Expire</button>
                </form>
                <form method="POST" action="/admin/deletekey" style="display:inline;margin-left:4px">
                  <input type="hidden" name="key" value="{{ k.key }}">
                  <button class="btn btn-ghost btn-sm">Delete</button>
                </form>
                {% else %}
                <span style="color:var(--muted);font-size:12px">—</span>
                {% endif %}
              </td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>

    <!-- CACHE -->
    <div class="card" id="cache">
      <div class="card-header">
        <div class="card-title">⚡ Bypass Cache <span style="font-weight:400;color:var(--muted);font-size:12px;margin-left:6px">{{ cache_size }} entries</span></div>
        <form method="POST" action="/admin/clear_cache">
          <button class="btn btn-red btn-sm">🗑 Clear Cache</button>
        </form>
      </div>
      <div class="card-body">
        <div class="cache-list">
          {% for orig, by in cache_items %}
          <div class="cache-row">
            <div class="cache-orig">{{ orig[:65] }}</div>
            <div class="cache-arr">→</div>
            <div class="cache-by">{{ by[:55] }}</div>
          </div>
          {% endfor %}
          {% if not cache_items %}<div style="color:var(--muted);text-align:center;padding:24px">Cache is empty</div>{% endif %}
        </div>
      </div>
    </div>

    <!-- USAGE LOGS -->
    <div class="card" id="logs">
      <div class="card-header"><div class="card-title">📊 Usage Logs</div></div>
      <div class="card-body">
        <form method="GET" action="/admin">
          <div class="log-select-row">
            <div style="flex:1"><label style="font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:1px;display:block;margin-bottom:6px">Select Key</label>
            <select name="log_key">
              <option value="">— Choose a key —</option>
              {% for k in all_keys %}
              <option value="{{ k.key }}" {% if selected_log_key == k.key %}selected{% endif %}>{{ k.key[:12] }}…{{ k.key[-6:] }} ({{ k.type }})</option>
              {% endfor %}
            </select></div>
            <button class="btn btn-blue">View Logs</button>
          </div>
        </form>
        {% if log_entries %}
        <div class="tbl-wrap">
          <table>
            <thead><tr><th>Time</th><th>Link</th><th>Result</th></tr></thead>
            <tbody>
              {% for lg in log_entries %}
              <tr>
                <td style="color:var(--muted)">{{ lg.time[:19] }}</td>
                <td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ lg.link }}</td>
                <td><span class="badge {{ 'badge-green' if lg.success else 'badge-red' }}">{{ '✅ OK' if lg.success else '❌ Fail' }}</span></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
        {% endif %}
      </div>
    </div>

  </div><!-- /content -->
</div><!-- /main -->
</body>
</html>"""


# ==================== ADMIN ROUTES ====================
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        if u == ADMIN_WEB_ID and p == ADMIN_WEB_PASS:
            flask_session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            error = "Invalid credentials"
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/admin/logout')
def admin_logout():
    flask_session.clear()
    return redirect('/admin/login')

@app.route('/admin', methods=['GET'])
@admin_required
def admin_panel():
    flash_ok  = flask_session.pop('flash_ok',  None)
    flash_err = flask_session.pop('flash_err', None)
    new_key   = flask_session.pop('new_key',   None)
    new_key_exp = flask_session.pop('new_key_exp', None)

    selected_log_key = request.args.get('log_key', '')
    log_entries = []
    if selected_log_key:
        log_entries = list(reversed(usage_logs.get(selected_log_key, [])))[:50]

    all_keys = []
    for k, v in PERMANENT_KEYS.items():
        masked_key = k[:4] + "****" + k[-4:] if len(k) > 8 else "****"
        entry = {**v, "key": masked_key, "_real_key": k, "expires_at": "Never",
            "ip_whitelist": ', '.join(v.get('ip_whitelist', []))}
        all_keys.append(entry)
    for k, v in temp_keys_db.items():
        all_keys.append({**v, "expires_at": v.get('expires_at','')[:19],
            "ip_whitelist": ', '.join(v.get('ip_whitelist', []))})

    cache_items = list(bypass_cache.items())[:50]

    active_keys = sum(1 for v in temp_keys_db.values() if v.get('status') == 'active')
    active_keys += len(PERMANENT_KEYS)

    return render_template_string(ADMIN_HTML,
        stats=stats_dict(), cache_size=len(bypass_cache),
        active_keys=active_keys, accounts=ACCOUNTS,
        links_per=LINKS_PER_ACCOUNT,
        all_keys=all_keys, cache_items=cache_items,
        flash_ok=flash_ok, flash_err=flash_err,
        new_key=new_key, new_key_exp=new_key_exp,
        selected_log_key=selected_log_key,
        log_entries=log_entries
    )

@app.route('/admin/genkey', methods=['POST'])
@admin_required
def admin_genkey():
    days = int(request.form.get('days', 1))
    days = max(1, min(days, 90))
    ip_raw = request.form.get('ip_whitelist', '').strip()
    ip_list = [x.strip() for x in ip_raw.split(',') if x.strip()] if ip_raw else []
    tg_id = request.form.get('tg_notify_id', '').strip() or None
    wh_url = request.form.get('webhook_url', '').strip()
    key, exp = generate_temp_key(days=days, ip_whitelist=ip_list, telegram_notify_id=tg_id)
    if wh_url:
        webhook_urls[key] = wh_url
        save_data()
    flask_session['new_key'] = key
    flask_session['new_key_exp'] = exp.strftime('%Y-%m-%d %H:%M:%S')
    flask_session['flash_ok'] = f"Key generated for {days} day(s)"
    return redirect('/admin')

@app.route('/admin/expirekey', methods=['POST'])
@admin_required
def admin_expirekey():
    key = request.form.get('key','')
    if expire_key(key):
        flask_session['flash_ok'] = "Key expired successfully"
    else:
        flask_session['flash_err'] = "Key not found"
    return redirect('/admin')

@app.route('/admin/deletekey', methods=['POST'])
@admin_required
def admin_deletekey():
    key = request.form.get('key','')
    if delete_key(key):
        flask_session['flash_ok'] = "Key deleted"
    else:
        flask_session['flash_err'] = "Key not found"
    return redirect('/admin')

@app.route('/admin/clear_cache', methods=['POST'])
@admin_required
def admin_clear_cache():
    with cache_lock:
        bypass_cache.clear()
    save_data()
    flask_session['flash_ok'] = "Cache cleared"
    return redirect('/admin')

@app.route('/admin/reset_account', methods=['POST'])
@admin_required
def admin_reset_account():
    acc_name = request.form.get('acc_name','')
    for acc in ACCOUNTS:
        if acc['name'] == acc_name:
            acc['blacklisted'] = False
            acc['blacklisted_at'] = None
            acc['count'] = 0
            flask_session['flash_ok'] = f"Account {acc_name} reset"
            return redirect('/admin')
    flask_session['flash_err'] = "Account not found"
    return redirect('/admin')

@app.route('/admin/add_account', methods=['POST'])
@admin_required
def admin_add_account():
    acc_name = request.form.get('acc_name', '').strip()
    api_id   = request.form.get('api_id', '').strip()
    api_hash = request.form.get('api_hash', '').strip()
    session  = request.form.get('session', '').strip()
    if not all([acc_name, api_id, api_hash, session]):
        flask_session['flash_err'] = "All fields required"
        return redirect('/admin')
    try:
        api_id_int = int(api_id)
    except ValueError:
        flask_session['flash_err'] = "API ID must be a number"
        return redirect('/admin')

    new_acc = {
        "name": acc_name,
        "api_id": api_id_int,
        "api_hash": api_hash,
        "session": session,
        "count": 0,
        "blacklisted": False,
        "blacklisted_at": None,
    }
    ACCOUNTS.append(new_acc)

    # Try to connect this account immediately
    async def connect_new():
        try:
            from telethon.sessions import StringSession
            cl = TelegramClient(StringSession(session), api_id_int, api_hash, loop=loop)
            await cl.connect()
            if await cl.is_user_authorized():
                clients.append(cl)
                make_handler(cl, new_acc)
                print(f"✅ New account connected: {acc_name}")
                return True
            else:
                clients.append(None)
                print(f"❌ New account session invalid: {acc_name}")
                return False
        except Exception as e:
            clients.append(None)
            print(f"❌ New account error {acc_name}: {e}")
            return False

    future = asyncio.run_coroutine_threadsafe(connect_new(), loop)
    try:
        ok = future.result(timeout=15)
        if ok:
            flask_session['flash_ok'] = f"Account {acc_name} added and connected!"
        else:
            flask_session['flash_err'] = f"Account {acc_name} added but session invalid — check credentials"
    except Exception as e:
        flask_session['flash_err'] = f"Account added but connect error: {e}"
    return redirect('/admin')

# ==================== API ROUTES ====================
@app.route('/')
def index():
    connected = sum(1 for c in clients if c and c.is_connected())
    return render_template_string(HOME_HTML,
        stats=stats_dict(),
        cache_size=len(bypass_cache),
        connected=connected,
        total_acc=len(ACCOUNTS),
        rate_limit=RATE_LIMIT_PER_MIN,
        version=API_VERSION,
        owner=API_OWNER,
    )

@app.route('/bypassed-links')
def bypassed_links_page():
    from flask import send_file
    if os.path.exists(LINKS_FILE):
        return send_file(LINKS_FILE, mimetype='application/json', as_attachment=False)
    return jsonify([])

@app.route('/bypass', methods=['GET', 'POST'])
def bypass():
    if request.method == 'GET':
        key  = request.args.get('key')
        link = request.args.get('link')
    else:
        d    = request.json or {}
        key  = d.get('key')
        link = d.get('link')

    if not key:  return jsonify(err_response("Missing 'key' parameter")), 400
    if not link: return jsonify(err_response("Missing 'link' parameter", key)), 400
    if not link.startswith(('http://', 'https://')): link = 'https://' + link

    # Free guest key handling
    if key == FREE_GUEST_KEY:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
        if not check_free_guest(client_ip):
            return jsonify(err_response("Free daily limit (5/day) reached. Contact admin for API key.", key, link)), 429
        kc = {'valid': True, 'type': 'free_guest'}
    else:
        kc = validate_key(key)
        if not kc['valid']:
            return jsonify(err_response(f"Invalid/Expired key: {kc.get('reason')}", key, link)), 401

    # IP Whitelist check
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr or '').split(',')[0].strip()
    if key != FREE_GUEST_KEY and not check_ip_whitelist(key, client_ip):
        return jsonify(err_response(f"IP not whitelisted: {client_ip}", key, link)), 403

    # Rate limit check
    if key != FREE_GUEST_KEY and not check_rate_limit(key):
        return jsonify(err_response(f"Rate limit exceeded ({RATE_LIMIT_PER_MIN}/min)", key, link)), 429

    # Cache check
    with cache_lock:
        if link in bypass_cache:
            log_usage(key, True, link)
            print(f"⚡ Cache hit: {link[:50]}")
            return jsonify(ok_response(link, bypass_cache[link], key, kc['type'], from_cache=True))

    cl, acc = get_active_client()
    if cl is None:
        log_usage(key, False, link)
        return jsonify({
            "status": False, "developer": API_OWNER,
            "message": "All bypass accounts unavailable",
            "response": {"alternative_link": FELIX_LINK},
            "stats": stats_dict()
        }), 503

    req_id = str(uuid.uuid4())
    with req_lock:
        active_requests[req_id] = {
            'id': req_id, 'key': key,
            'original_link': link, 'acc_name': acc['name'],
            'timestamp': time.time(), 'complete': False,
            'result': None, 'blacklisted': False
        }

    try:
        future = asyncio.run_coroutine_threadsafe(send_to_group(link, cl), loop)
        future.result(timeout=5)
        print(f"📤 [{acc['name']}] Sending: {link[:50]}...")
    except Exception as e:
        with req_lock:
            active_requests.pop(req_id, None)
        log_usage(key, False, link)
        return jsonify(err_response(f"Send error: {e}", key, link)), 500

    start = time.time()
    timeout = 130

    while time.time() - start < timeout:
        time.sleep(0.3)
        with req_lock:
            rd = completed_requests.pop(req_id, None)
            if rd:
                if rd.get('blacklisted'):
                    cl2, acc2 = get_active_client()
                    if cl2 is None:
                        log_usage(key, False, link)
                        return jsonify(err_response("All accounts unavailable", key, link)), 503
                    req_id2 = str(uuid.uuid4())
                    active_requests[req_id2] = {
                        'id': req_id2, 'key': key,
                        'original_link': link, 'acc_name': acc2['name'],
                        'timestamp': time.time(), 'complete': False,
                        'result': None, 'blacklisted': False
                    }
                    try:
                        f2 = asyncio.run_coroutine_threadsafe(send_to_group(link, cl2), loop)
                        f2.result(timeout=5)
                        req_id = req_id2
                        start = time.time()
                        continue
                    except Exception as e2:
                        log_usage(key, False, link)
                        return jsonify(err_response(f"Retry error: {e2}", key, link)), 500
                elif rd.get('error'):
                    log_usage(key, False, link)
                    return jsonify(err_response("Nick Bot error — unsupported link", key, link)), 422
                else:
                    res = rd['result']
                    log_usage(key, True, link)
                    return jsonify(ok_response(res['original_link'], res['bypassed_link'], key, kc['type']))

        with req_lock:
            ar = active_requests.get(req_id)
            if ar and ar.get('complete'):
                active_requests.pop(req_id, None)
                res = ar['result']
                log_usage(key, True, link)
                return jsonify(ok_response(res['original_link'], res['bypassed_link'], key, kc['type']))

    with req_lock:
        active_requests.pop(req_id, None)
        completed_requests.pop(req_id, None)
    log_usage(key, False, link)
    return jsonify(err_response("Timeout: No response within 130 seconds", key, link)), 504

@app.route('/key/felixgenerate', methods=['GET', 'POST'])
def felix_generate_key():
    # Key generation sirf admin panel se allowed hai
    return jsonify({"status": False, "error": "Key generation only allowed via Admin Panel. Contact: " + API_OWNER}), 403

@app.route('/expirekey/<key>', methods=['GET'])
def expire_key_endpoint(key):
    if key in PERMANENT_KEYS:
        return jsonify({"status": False, "error": "Cannot expire permanent key"}), 403
    if expire_key(key):
        return jsonify({"status": True, "message": "Key expired", "key": key[:8]+"..."+key[-4:]})
    return jsonify({"status": False, "error": "Key not found"}), 404

@app.route('/webhook/set', methods=['GET', 'POST'])
def set_webhook():
    if request.method == 'GET':
        key = request.args.get('key')
        url = request.args.get('url')
    else:
        d = request.json or {}
        key = d.get('key')
        url = d.get('url')
    if not key or not url:
        return jsonify({"status": False, "error": "key and url required"}), 400
    kc = validate_key(key)
    if not kc['valid']:
        return jsonify({"status": False, "error": "Invalid key"}), 401
    webhook_urls[key] = url
    save_data()
    return jsonify({"status": True, "message": "Webhook set", "url": url})

@app.route('/webhook/remove', methods=['GET'])
def remove_webhook():
    key = request.args.get('key')
    if not key: return jsonify({"status": False, "error": "key required"}), 400
    webhook_urls.pop(key, None)
    save_data()
    return jsonify({"status": True, "message": "Webhook removed"})

@app.route('/logs', methods=['GET'])
def key_logs():
    if request.args.get('admin_secret') != ADMIN_SECRET:
        return jsonify({"status": False, "error": "Unauthorized"}), 401
    key = request.args.get('key')
    if not key:
        return jsonify({"status": False, "error": "key required"}), 400
    logs = list(reversed(usage_logs.get(key, [])))[:100]
    return jsonify({"status": True, "key": key[:8]+"..."+key[-4:], "logs": logs})

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify({
        "api_name": API_NAME, "version": API_VERSION,
        "developer": API_OWNER, "status": "online",
        "statistics": stats_dict(),
        "cache_size": len(bypass_cache),
        "active_requests": len(active_requests)
    })

@app.route('/health', methods=['GET'])
def health():
    connected = [c.is_connected() if c else False for c in clients]
    return jsonify({
        "status": "healthy",
        "accounts": [{"name": ACCOUNTS[i]['name'], "connected": connected[i], "blacklisted": ACCOUNTS[i]['blacklisted']} for i in range(len(ACCOUNTS))],
        "total_connected": sum(connected),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/accounts', methods=['GET'])
def accounts_status():
    return jsonify({
        "total": len(ACCOUNTS),
        "current_active": ACCOUNTS[current_idx]['name'],
        "accounts": [
            {
                "name": a['name'], "blacklisted": a['blacklisted'],
                "blacklisted_at": a.get('blacklisted_at'),
                "links_this_turn": a['count'], "links_per_turn": LINKS_PER_ACCOUNT
            } for a in ACCOUNTS
        ]
    })

@app.route('/key/list', methods=['GET'])
def list_keys():
    if request.args.get('admin_secret') != ADMIN_SECRET:
        return jsonify({"status": False, "error": "Unauthorized"}), 401
    return jsonify({
        "permanent_keys": list(PERMANENT_KEYS.keys()),
        "temp_keys": [
            {"key": k[:8]+"..."+k[-4:], "expires_at": v['expires_at'],
             "used": v['total_used'], "status": v['status'],
             "ip_whitelist": v.get('ip_whitelist', [])}
            for k, v in temp_keys_db.items()
        ]
    })

# ==================== TELEGRAM STARTUP ====================
def start_telegram_sync():
    async def start():
        print("\n" + "="*60)
        print(f"🚀 {API_NAME} v{API_VERSION}")
        print(f"👑 Developer: {API_OWNER}")
        print("="*60)

        first_client = None
        for i, acc in enumerate(ACCOUNTS):
            try:
                cl = TelegramClient(
                    StringSession(acc['session']),
                    acc['api_id'], acc['api_hash'], loop=loop
                )
                await cl.connect()
                if not await cl.is_user_authorized():
                    print(f"❌ {acc['name']} — session invalid!")
                    clients.append(None)
                    continue
                me = await cl.get_me()
                clients.append(cl)
                if first_client is None:
                    first_client = cl
                make_handler(cl, acc)
                try:
                    await cl.get_entity(TARGET_GROUP)
                    await cl.send_message(TARGET_GROUP, ".")
                    async for msg in cl.iter_messages(TARGET_GROUP, limit=1):
                        if msg.text == "." and msg.sender_id == me.id:
                            await msg.delete()
                    print(f"✅ [{i+1}] {acc['name']} — {me.first_name} | Group: OK")
                except Exception:
                    try:
                        await cl(JoinChannelRequest(TARGET_GROUP))
                        print(f"✅ [{i+1}] {acc['name']} — Joined group")
                    except Exception as je:
                        print(f"⚠️  [{i+1}] {acc['name']} — Group join failed: {je}")
                        acc['blacklisted'] = True
                        acc['blacklisted_at'] = datetime.now().isoformat()
            except Exception as e:
                print(f"❌ {acc['name']} error: {e}")
                clients.append(None)

        print("="*60)
        print(f"🔥 {sum(1 for c in clients if c)} / {len(ACCOUNTS)} connected")
        print("="*60)

        global _channel_client_ref
        if first_client:
            _channel_client_ref = first_client
            loaded = await load_data_channel(first_client)
            if not loaded:
                load_data_local()
        else:
            load_data_local()

        # Auto-reconnect task
        asyncio.ensure_future(auto_reconnect_loop())

        tasks = [cl.run_until_disconnected() for cl in clients if cl]
        if tasks:
            await asyncio.gather(*tasks)

    loop.run_until_complete(start())

def run_api():
    port = int(os.environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# ==================== MAIN ====================
if __name__ == '__main__':
    # Auto-save thread
    threading.Thread(target=auto_save_loop, daemon=True).start()
    # Expiry notification thread
    threading.Thread(target=expiry_notification_loop, daemon=True).start()
    # Flask API thread
    threading.Thread(target=run_api, daemon=True).start()
    try:
        start_telegram_sync()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        save_data()
        print("💾 Final save done.")
        loop.call_soon_threadsafe(loop.stop)
