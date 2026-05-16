from flask import Flask, request, jsonify
from telethon import TelegramClient, events
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

# ==================== CONFIG ====================
API_ID = int(os.environ.get('API_ID', 34635054))
API_HASH = os.environ.get('API_HASH', 'b8e93ca4f3abdcba65cc020504f82f08')
SESSION_NAME = "felix_session"
STRING_SESSION = os.environ.get('STRING_SESSION', '1BVtsOKwBu53YjiV0ZwWn3RZtDqzm5GKYl2jmN3PT_TXOjkU27Qs84s1yRxQ-ZaFQpz9bMg4g7R74Rdhi2SHyBZnpExMOXcKj6y21Gsb-9zkJWr7FanS7JsLzNcRP6CPcZqyBmCYkMI3q2rYsGyWpEgRudmfrgkyPSqTHOzPoPcYZyKdxzDCRwVvnfVZa1XzkU7YqV6sXjSzyNtGghsT6pcKy1QoLWgQJisnIpwDxi9LL71Tq3Hg5hIlIewgsu85vCofRLKtAQieuf0A9PGM49SLAtF1w6Klqf-6V5saGm0dlC-ibjImp-HCU7z8MLJtlKUuPfNdP5E1z1m8PdD-Qf8R4CPJEeas=')

# 🔥 SHADOW BYPASS GROUP
TARGET_GROUP_ID = -1003512490056
BOT_COMMAND = '/b'
SAVE_CHANNEL = "@savelinkssfelix"

# API Details
API_NAME = "FELIX BYPASS API"
API_BOT = "@felixbypass_bot"
API_OWNER = "@mikey_bhai1"
API_VERSION = "3.0"

# Permanent Keys
PERMANENT_KEYS = {
    "daddyfelix": {
        "key": "daddyfelix",
        "type": "permanent",
        "created_at": datetime.now().isoformat(),
        "total_used": 0,
        "status": "active"
    }
}

CACHE_FILE = "bypassed_cache.json"
temp_keys_db = {}
total_requests = 0
successful_requests = 0
failed_requests = 0
active_requests = {}
completed_requests = {}
ADMIN_SECRET = "felixadmin2026"

logging.getLogger('telethon').setLevel(logging.WARNING)

app = Flask(__name__)

# Global variables
client = None
group_entity = None
save_channel_entity = None
loop = None

# ==================== CACHE FUNCTIONS ====================
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_cached_result(original_link):
    cache = load_cache()
    return cache.get(original_link)

def save_to_cache(original_link, bypassed_link):
    cache = load_cache()
    cache[original_link] = {
        "bypassed": bypassed_link,
        "timestamp": datetime.now().isoformat()
    }
    save_cache(cache)

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

# ==================== RESPONSE FORMAT ====================
def format_response(original_link, bypassed_link, key):
    success_rate = round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
    
    return {
        "status": True,
        "message": "Link Bypassed Successfully ✅",
        "branding": {
            "service": API_NAME,
            "bot": API_BOT,
            "developer": API_OWNER
        },
        "request": {
            "original_url": original_link
        },
        "result": {
            "bypassed_url": bypassed_link
        },
        "statistics": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": f"{success_rate}%"
        },
        "api_usage": {
            "endpoint": "/bypass?key=YOUR_KEY&link=URL",
            "example": f"/bypass?key={key}&link=https://alpha-links.in/xxxxx"
        },
        "powered_by": "Felix Bypass System"
    }

def format_error_response(error, key, link=None):
    success_rate = round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
    
    return {
        "status": False,
        "message": "Link Bypass Failed ❌",
        "branding": {
            "service": API_NAME,
            "bot": API_BOT,
            "developer": API_OWNER
        },
        "error": error,
        "request": {
            "original_url": link if link else None
        },
        "statistics": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": f"{success_rate}%"
        },
        "api_usage": {
            "endpoint": "/bypass?key=YOUR_KEY&link=URL",
            "example": f"/bypass?key={key}&link=https://alpha-links.in/xxxxx"
        },
        "powered_by": "Felix Bypass System"
    }

# ==================== API ENDPOINTS ====================
@app.route('/')
def index():
    return jsonify({
        "service": API_NAME,
        "bot": API_BOT,
        "developer": API_OWNER,
        "version": API_VERSION,
        "status": "online",
        "endpoints": {
            "bypass": "/bypass?key=KEY&link=URL",
            "generate_key": "/key/felixgenerate?days=1",
            "expire_key": "/expirekey/KEY_HERE",
            "stats": "/stats",
            "health": "/health"
        }
    })

@app.route('/bypass', methods=['GET', 'POST'])
def bypass():
    global active_requests, client, loop
    
    if client is None:
        return jsonify(format_error_response("Telegram client not ready", "None")), 500
    
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
    
    # Check cache
    cached = get_cached_result(link)
    if cached:
        log_usage(key, True, link)
        print(f"⚡ Instant result from cache: {link[:50]}...")
        return jsonify(format_response(link, cached['bypassed'], key))
    
    key_check = validate_key(key)
    if not key_check['valid']:
        return jsonify(format_error_response(f"Invalid or expired key: {key_check.get('reason', 'UNKNOWN')}", key, link)), 401
    
    req_id = str(uuid.uuid4())
    
    active_requests[req_id] = {
        'id': req_id,
        'key': key,
        'original_link': link,
        'timestamp': time.time(),
        'complete': False,
        'result': None
    }
    
    # Run async function
    future = asyncio.run_coroutine_threadsafe(send_to_bot(link), loop)
    
    try:
        future.result(timeout=10)
        print(f"\n📤 [{key[:8]}...] Bypassing: {link[:60]}...")
        
        start_time = time.time()
        timeout = 30
        
        while time.time() - start_time < timeout:
            time.sleep(0.5)
            
            if req_id in completed_requests:
                result = completed_requests[req_id]['result']
                del completed_requests[req_id]
                log_usage(key, True, link)
                return jsonify(format_response(result['original_link'], result['bypassed_link'], key))
            
            if req_id in active_requests and active_requests[req_id].get('complete', False):
                result = active_requests[req_id]['result']
                del active_requests[req_id]
                log_usage(key, True, link)
                return jsonify(format_response(result['original_link'], result['bypassed_link'], key))
        
        if req_id in active_requests:
            del active_requests[req_id]
        if req_id in completed_requests:
            del completed_requests[req_id]
        log_usage(key, False, link)
        return jsonify(format_error_response("Timeout: Bot did not respond within 30 seconds.", key, link)), 504
        
    except Exception as e:
        if req_id in active_requests:
            del active_requests[req_id]
        if req_id in completed_requests:
            del completed_requests[req_id]
        log_usage(key, False, link)
        return jsonify(format_error_response(f"Internal error: {str(e)}", key, link)), 500

# ==================== OTHER ENDPOINTS ====================
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
        "expires_at": expires_at.isoformat()
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
            "expired_at": datetime.now().isoformat()
        })
    elif key in PERMANENT_KEYS:
        return jsonify({"status": False, "error": "Cannot expire permanent keys"}), 403
    else:
        return jsonify({"status": False, "error": "Key not found"}), 404

@app.route('/stats', methods=['GET'])
def stats():
    success_rate = round((successful_requests / total_requests * 100) if total_requests > 0 else 0, 2)
    return jsonify({
        "service": API_NAME,
        "bot": API_BOT,
        "developer": API_OWNER,
        "status": "online",
        "statistics": {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": f"{success_rate}%"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": API_NAME,
        "timestamp": datetime.now().isoformat()
    })

# ==================== TELEGRAM FUNCTIONS ====================
async def delete_my_messages():
    try:
        async for msg in client.iter_messages(TARGET_GROUP_ID, from_user='me', limit=5):
            await msg.delete()
            await asyncio.sleep(0.3)
    except:
        pass

def extract_links_from_response(message_text):
    original_link = None
    bypassed_link = None
    
    orig_match = re.search(r'Original Link:\s*(https?://[^\s\n]+)', message_text, re.IGNORECASE)
    if orig_match:
        original_link = orig_match.group(1).strip()
    
    bypass_match = re.search(r'Bypassed Link:\s*(https?://[^\s\n]+)', message_text, re.IGNORECASE)
    if bypass_match:
        bypassed_link = bypass_match.group(1).strip()
    
    if not original_link or not bypassed_link:
        urls = re.findall(r'https?://[^\s\n]+', message_text)
        if len(urls) >= 1:
            original_link = urls[0] if not original_link else original_link
        if len(urls) >= 2:
            bypassed_link = urls[1] if not bypassed_link else bypassed_link
    
    if original_link:
        original_link = re.sub(r'[✔️✅*]', '', original_link).strip()
    if bypassed_link:
        bypassed_link = re.sub(r'[✔️✅*]', '', bypassed_link).strip()
    
    return original_link, bypassed_link

async def send_to_bot(link):
    global group_entity
    
    if group_entity is None:
        group_entity = await client.get_entity(TARGET_GROUP_ID)
        print(f"📌 Group: {group_entity.title}")
    
    command = f"{BOT_COMMAND} {link}"
    await client.send_message(group_entity, command)
    print(f"📤 Sent: {command[:60]}...")
    
    await asyncio.sleep(2)
    await delete_my_messages()

async def save_to_channel(original_link, bypassed_link):
    try:
        global save_channel_entity
        if save_channel_entity is None:
            save_channel_entity = await client.get_entity(SAVE_CHANNEL)
        
        message = f"🔗 **Link Bypassed & Saved**\n\n📌 **Original:** {original_link}\n✅ **Bypassed:** {bypassed_link}\n⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n👑 **By:** FELIX BYPASS SYSTEM"
        await client.send_message(save_channel_entity, message)
        print(f"💾 Saved to channel: {original_link[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Failed to save to channel: {e}")
        return False

# ==================== EVENT HANDLER (Registered AFTER client is ready) ====================
async def register_handlers():
    @client.on(events.NewMessage(chats=TARGET_GROUP_ID))
    async def group_handler(event):
        message_text = event.message.text or ""
        
        if 'Original Link' in message_text or 'Bypassed Link' in message_text:
            original_link, bypassed_link = extract_links_from_response(message_text)
            
            if bypassed_link:
                print(f"\n📥 Bot response received")
                print(f"   ✅ Bypassed: {bypassed_link[:50]}...")
                
                if original_link:
                    save_to_cache(original_link, bypassed_link)
                    await save_to_channel(original_link, bypassed_link)
                
                for req_id, req_data in list(active_requests.items()):
                    request_link = req_data.get('original_link', '')
                    if request_link and (request_link in message_text or (original_link and request_link == original_link)):
                        active_requests[req_id]['result'] = {
                            'original_link': original_link or request_link,
                            'bypassed_link': bypassed_link
                        }
                        active_requests[req_id]['complete'] = True
                        completed_requests[req_id] = active_requests[req_id]
                        del active_requests[req_id]
                        print(f"✅ Request {req_id[:8]} completed!")
                        break

# ==================== TELEGRAM LOGIN ====================
async def login_with_phone():
    print("\n" + "="*60)
    print("🔐 TELEGRAM LOGIN (Local Mode)")
    print("="*60)
    
    if not await client.is_user_authorized():
        phone = input("📱 Enter phone number (with +91): ")
        await client.send_code_request(phone)
        code = input("📲 Enter OTP: ")
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "two-steps" in str(e).lower() or "password" in str(e).lower():
                password = input("🔑 Enter 2FA password: ")
                await client.sign_in(password=password)
            else:
                raise e
    
    me = await client.get_me()
    print(f"\n✅ Logged in: {me.first_name} (@{me.username})")
    
    # ✅ Session string print karo — Render ke liye copy karo
    session_str = client.session.save()
    print("\n" + "="*60)
    print("🔑 SESSION STRING (Render pe STRING_SESSION env me paste karo):")
    print("="*60)
    print(session_str)
    print("="*60)
    print("⚠️  Yeh string safe rakhna — kisi ko mat dena!\n")
    
    return me

async def init_group():
    global group_entity, save_channel_entity
    try:
        group_entity = await client.get_entity(TARGET_GROUP_ID)
        print(f"✅ Group: {group_entity.title} (ID: {TARGET_GROUP_ID})")
        
        save_channel_entity = await client.get_entity(SAVE_CHANNEL)
        print(f"✅ Channel: {SAVE_CHANNEL}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# ==================== MAIN ====================
async def main():
    global client, loop
    
    print("="*60)
    print("🚀 FELIX BYPASS API - SHADOW BYPASS GROUP")
    print("👑 @mikey_bhai1")
    print(f"📌 Group ID: {TARGET_GROUP_ID}")
    print("="*60)
    
    loop = asyncio.get_event_loop()
    
    if STRING_SESSION:
        # ✅ RENDER MODE — String session se login (no OTP needed)
        print("☁️  Render Mode: String session se login ho raha hai...")
        client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ String session invalid hai! Naya session generate karo.")
            return
        
        me = await client.get_me()
        print(f"✅ Logged in: {me.first_name} (@{me.username})")
    else:
        # ✅ LOCAL/TERMUX MODE — Phone + OTP se login
        print("📱 Local Mode: Phone login ho raha hai...")
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.connect()
        await login_with_phone()
    
    # Initialize group and channel
    await init_group()
    
    # Register event handlers AFTER client is ready
    await register_handlers()
    
    # Load cache
    cache = load_cache()
    print(f"📊 Cached links: {len(cache)}")
    
    port = int(os.environ.get('PORT', 5010))
    print(f"\n✅ API Ready!")
    print(f"📍 http://localhost:{port}")
    print(f"📍 /bypass?key=daddyfelix&link=https://alpha-links.in/jhBV")
    print("="*60)
    
    await client.run_until_disconnected()

def run_api():
    port = int(os.environ.get('PORT', 5010))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

if __name__ == '__main__':
    # Start API in thread
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    
    # Run Telegram client
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")