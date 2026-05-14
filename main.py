from flask import Flask, request, jsonify
from telethon import TelegramClient, events
import asyncio
import threading
import time
import re
import logging
from datetime import datetime, timedelta
import uuid
import secrets

# ==================== CONFIG ====================
API_ID = 34635054
API_HASH = 'b8e93ca4f3abdcba65cc020504f82f08'
BOT_USERNAME = '@Nick_Bypass_Bot'

# API Details
API_NAME = "FELIX BYPASS API"
API_OWNER = "@Felix_bhai"
API_VERSION = "3.0"

# Permanent Keys (Only for YOU — Never Share)
PERMANENT_KEYS = {
    "daddyfelix": {
        "key": "daddyfelix",
        "type": "permanent",
        "created_at": datetime.now().isoformat(),
        "total_used": 0,
        "status": "active"
    }
}

# Temporary keys database
temp_keys_db = {}

# Global stats
total_requests = 0
successful_requests = 0
failed_requests = 0

# Track active requests
active_requests = {}
completed_requests = {}

# Admin only endpoints (for security)
ADMIN_SECRET = "felixadmin2026"

logging.getLogger('telethon').setLevel(logging.WARNING)

app = Flask(__name__)

# Global event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Telegram Client
client = TelegramClient('felix_session', API_ID, API_HASH, loop=loop)

# ==================== KEY FUNCTIONS ====================
def validate_key(key):
    if key in PERMANENT_KEYS:
        return {'valid': True, 'data': PERMANENT_KEYS[key], 'type': 'permanent'}
    if key in temp_keys_db:
        key_data = temp_keys_db[key]
        if datetime.now() > datetime.fromisoformat(key_data['expires_at']):
            return {'valid': False, 'reason': 'EXPIRED'}
        return {'valid': True, 'data': key_data, 'type': 'temporary'}
    return {'valid': False, 'reason': 'INVALID_KEY'}

def generate_temp_key(days=1):
    key = secrets.token_hex(16)
    expires_at = datetime.now() + timedelta(days=days)
    temp_keys_db[key] = {
        "key": key,
        "type": "temporary",
        "created_at": datetime.now().isoformat(),
        "expires_at": expires_at.isoformat(),
        "total_used": 0,
        "status": "active",
        "days": days
    }
    return key, expires_at

def expire_key(key):
    if key in temp_keys_db:
        temp_keys_db[key]['expires_at'] = datetime.now().isoformat()
        temp_keys_db[key]['status'] = 'expired'
        return True
    return False

def log_usage(key, success, link=None):
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

# ==================== LINK EXTRACTION ====================
def extract_links_from_response(message_text):
    original_link = None
    bypassed_link = None
    
    orig_match = re.search(r'Original\s*Link\s*:?\s*[✔️✅]*\s*(https?://[^\s\n]+)', message_text, re.IGNORECASE)
    if orig_match:
        original_link = orig_match.group(1).strip()
    
    bypass_match = re.search(r'Bypassed\s*Link\s*:?\s*[✔️✅]*\s*(https?://[^\s\n]+)', message_text, re.IGNORECASE)
    if bypass_match:
        bypassed_link = bypass_match.group(1).strip()
    
    if not original_link or not bypassed_link:
        lines = message_text.split('\n')
        for line in lines:
            if 'Original' in line and 'http' in line:
                urls = re.findall(r'https?://[^\s]+', line)
                if urls:
                    original_link = urls[0]
            if 'Bypassed' in line and 'http' in line:
                urls = re.findall(r'https?://[^\s]+', line)
                if urls:
                    bypassed_link = urls[0]
    
    if original_link:
        original_link = re.sub(r'[✔️✅*]', '', original_link).strip()
    if bypassed_link:
        bypassed_link = re.sub(r'[✔️✅*]', '', bypassed_link).strip()
    
    return original_link, bypassed_link

# ==================== BOT HANDLER ====================
@client.on(events.NewMessage(chats=BOT_USERNAME))
async def handler(event):
    message_text = event.message.text
    if 'Bypassed Link' not in message_text:
        return
    
    original_link, bypassed_link = extract_links_from_response(message_text)
    
    if bypassed_link:
        print(f"📥 Bot Response Received")
        for req_id, req_data in list(active_requests.items()):
            if req_data['original_link'] in message_text or (original_link and req_data['original_link'] == original_link):
                active_requests[req_id]['result'] = {
                    'original_link': original_link or req_data['original_link'],
                    'bypassed_link': bypassed_link
                }
                active_requests[req_id]['complete'] = True
                active_requests[req_id]['completed_at'] = time.time()
                completed_requests[req_id] = active_requests[req_id]
                del active_requests[req_id]
                print(f"✅ Request completed")
                break

# ==================== SEND TO BOT ====================
async def send_to_bot(link):
    await client.send_message(BOT_USERNAME, link)

# ==================== RESPONSE FORMAT ====================
def format_response(original_link, bypassed_link, key, key_type):
    return {
        "status": True,
        "message": "API Request Successful",
        "developer": API_OWNER,
        "request": {"original_link": original_link},
        "response": {"bypassed_link": bypassed_link},
        "usage": {
            "endpoint": "/bypass?key=YOUR_KEY&link=URL",
            "example": "/bypass?key=YOUR_API_KEY_HERE&link=https://adsfly.in/AS79Oo0"
        },
        "stats": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
        },
        "note": "Link bypassed successfully."
    }

def format_error_response(error, key, link=None, key_type=None):
    return {
        "status": False,
        "message": "API Request Failed",
        "developer": API_OWNER,
        "error": error,
        "request": {"original_link": link if link else None},
        "usage": {
            "endpoint": "/bypass?key=YOUR_KEY&link=URL",
            "example": "/bypass?key=YOUR_API_KEY_HERE&link=https://adsfly.in/AS79Oo0"
        },
        "stats": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
        },
        "note": "Please check your key or link and try again."
    }

# ==================== API ENDPOINTS ====================
@app.route('/')
def index():
    example_key = "YOUR_API_KEY_HERE"
    return jsonify({
        "api_name": API_NAME,
        "version": API_VERSION,
        "developer": API_OWNER,
        "status": "online",
        "endpoints": {
            "bypass": "/bypass?key=KEY&link=URL",
            "generate_key": "/key/felixgenerate?days=1",
            "expire_key": "/expirekey/KEY_HERE",
            "stats": "/stats",
            "health": "/health"
        },
        "example": f"/bypass?key={example_key}&link=https://adsfly.in/AS79Oo0"
    })

@app.route('/bypass', methods=['GET', 'POST'])
def bypass():
    global active_requests
    if request.method == 'GET':
        key = request.args.get('key')
        link = request.args.get('link')
    else:
        data = request.json or {}
        key = data.get('key')
        link = data.get('link')
    
    if not key:
        return jsonify(format_error_response("Missing 'key' parameter", "None")), 400
    if not link:
        return jsonify(format_error_response("Missing 'link' parameter", key)), 400
    
    if not link.startswith(('http://', 'https://')):
        link = 'https://' + link
    
    key_check = validate_key(key)
    if not key_check['valid']:
        return jsonify(format_error_response(
            f"Invalid or expired key: {key_check.get('reason', 'UNKNOWN')}", key, link
        )), 401
    
    key_type = key_check['type']
    req_id = str(uuid.uuid4())
    
    active_requests[req_id] = {
        'id': req_id,
        'key': key,
        'original_link': link,
        'timestamp': time.time(),
        'complete': False,
        'result': None
    }
    
    try:
        future = asyncio.run_coroutine_threadsafe(send_to_bot(link), loop)
        future.result(timeout=5)
        print(f"📤 [{key[:8]}...] Bypassing: {link[:50]}...")
        
        start_time = time.time()
        timeout = 25
        
        while time.time() - start_time < timeout:
            time.sleep(0.3)
            if req_id in completed_requests:
                result = completed_requests[req_id]['result']
                del completed_requests[req_id]
                log_usage(key, True, link)
                return jsonify(format_response(result['original_link'], result['bypassed_link'], key, key_type))
            if req_id in active_requests and active_requests[req_id].get('complete', False):
                result = active_requests[req_id]['result']
                del active_requests[req_id]
                log_usage(key, True, link)
                return jsonify(format_response(result['original_link'], result['bypassed_link'], key, key_type))
        
        if req_id in active_requests:
            del active_requests[req_id]
        if req_id in completed_requests:
            del completed_requests[req_id]
        log_usage(key, False, link)
        return jsonify(format_error_response("Timeout: Bot did not respond within 25 seconds.", key, link)), 504
        
    except Exception as e:
        if req_id in active_requests:
            del active_requests[req_id]
        if req_id in completed_requests:
            del completed_requests[req_id]
        log_usage(key, False, link)
        return jsonify(format_error_response(f"Internal error: {str(e)}", key, link)), 500

@app.route('/key/felixgenerate', methods=['GET', 'POST'])
def felix_generate_key():
    if request.method == 'GET':
        days = request.args.get('days', 1)
    else:
        data = request.json or {}
        days = data.get('days', 1)
    
    try:
        days = int(days)
        if days <= 0: days = 1
        if days > 90: days = 90
    except:
        days = 1
    
    key, expires_at = generate_temp_key(days)
    return jsonify({
        "status": True,
        "message": "Temporary key generated successfully",
        "developer": API_OWNER,
        "key": key,
        "valid_days": days,
        "expires_at": expires_at.isoformat(),
        "note": "Share this key with your users. This key will expire automatically.",
        "stats": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
        }
    })

@app.route('/expirekey/<key>', methods=['GET'])
def expire_key_endpoint(key):
    if not key:
        return jsonify({"status": False, "error": "No key provided"}), 400
    if key in temp_keys_db:
        expire_key(key)
        return jsonify({
            "status": True,
            "message": "Key expired successfully",
            "developer": API_OWNER,
            "key": key[:8] + "..." + key[-4:],
            "expired_at": datetime.now().isoformat(),
            "note": "This key can no longer be used."
        })
    elif key in PERMANENT_KEYS:
        return jsonify({"status": False, "error": "Cannot expire permanent keys"}), 403
    else:
        return jsonify({"status": False, "error": "Key not found"}), 404

@app.route('/key/list', methods=['GET'])
def list_keys():
    admin_key = request.args.get('admin_secret')
    if admin_key != ADMIN_SECRET:
        return jsonify({"status": False, "error": "Unauthorized."}), 401
    
    keys_list = []
    for k, v in temp_keys_db.items():
        keys_list.append({
            "key": k[:8] + "..." + k[-4:],
            "full_key": k,
            "expires_at": v['expires_at'],
            "total_used": v['total_used'],
            "days": v.get('days', 1),
            "status": v['status']
        })
    return jsonify({
        "total_temp_keys": len(temp_keys_db),
        "permanent_keys": list(PERMANENT_KEYS.keys()),
        "temporary_keys": keys_list
    })

@app.route('/stats', methods=['GET'])
def stats():
    return jsonify({
        "api_name": API_NAME,
        "developer": API_OWNER,
        "version": API_VERSION,
        "status": "online",
        "statistics": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
        },
        "keys_info": {
            "permanent_keys": "Hidden",
            "active_temp_keys": len(temp_keys_db)
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "bot_connected": client.is_connected() if client else False,
        "timestamp": datetime.now().isoformat()
    })

# ==================== TELEGRAM START ====================
def start_telegram_sync():
    async def start():
        await client.start()
        print("\n" + "="*60)
        print(f"🔥 {API_NAME} v{API_VERSION}")
        print(f"👑 Developer: {API_OWNER}")
        print(f"🤖 Bot: {BOT_USERNAME}")
        print("="*60)
        print("📍 Generate Key: /key/felixgenerate?days=1")
        print("📍 Bypass: /bypass?key=KEY&link=URL")
        print("="*60 + "\n")
        await client.send_message(BOT_USERNAME, '/start')
        await client.run_until_disconnected()
    loop.run_until_complete(start())

def run_api():
    port = int(__import__('os').environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

# ==================== MAIN ====================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 STARTING FELIX BYPASS API...")
    print("="*60)
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    try:
        start_telegram_sync()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        loop.call_soon_threadsafe(loop.stop)
