from flask import Flask, request, jsonify
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio
import threading
import re
import json
import logging
import time
import os
from datetime import datetime

# ==================== CONFIG ====================
API_ID = 35240692
API_HASH = "8e95febf3563b0da51e9cbb72640c541"

STRING_SESSION = "1BVtsOJ8Bu4FcdLwR5ojpHU82Qb3JECVOja50XlUSdF5tD10nC_9-TMRIM-x8L_6ARWCdYFU7lgkgNY_hrIuorou4qFjAKElSZXa1TYz-vONwWfRZ3cooAA7msq3N1geuSAz7MEnS7nMYf6859rTEYW6YuLtoMpgr2Tz-2JSouznTXn_duEOGWx1V4e5gmGCMGut7ovr7ohYmodlj5NR_wJqdNGN0_e6669MSxLaqnWajkm0tqqrJWLUlcQ11mi33QIxV6KDoeYYk7vzqChyz260iQthOK02Dgd8i38U3g1SQ-KuuaH6m250-1IKqxoaxZ06DDeSOfDEAwPeRGyZ8c29zKQSdWRk="

# Groups
GROUP1 = "https://t.me/louraby"
GROUP2 = -1003877631708

PERMANENT_KEY = "daddyfelix"
AUTO_DELETE_SECONDS = 20

# Silent logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger('telethon').setLevel(logging.WARNING)

app = Flask(__name__)
client = None
loop = None
pending = {}
counter = 0
stats = {"total": 0, "success": 0, "failed": 0}

# ==================== COMMANDS WITH GROUP ASSIGNMENT ====================
COMMANDS = {
    # GROUP 1 (@louraby)
    "num": GROUP1, "vnum": GROUP1, "veh": GROUP1,
    "insta": GROUP1, "ip": GROUP1, "email": GROUP1,
    "ifsc": GROUP1, "adhar": GROUP1, "imei": GROUP1,
    "pak": GROUP1, "gst": GROUP1, "bomber": GROUP1,
    
    # GROUP 2 (Users X Info group)
    "upiinfo": GROUP2, "fam": GROUP2, "tg": GROUP2,
    "pan": GROUP2, "leak": GROUP2, "family": GROUP2,
}

# ==================== JSON EXTRACTOR ====================
def extract_json_objects(text):
    objects = []
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
                    try:
                        objects.append(json.loads(text[start:i+1]))
                    except:
                        pass
    return objects

def extract_records_from_malformed(text):
    records = []
    blocks = re.split(r'"ADDRESS"\s*:\s*"', text)
    
    for block in blocks[1:]:
        record = {}
        
        addr_end = block.find('"')
        if addr_end != -1:
            record["ADDRESS"] = block[:addr_end].replace('!', ', ')
        
        mobile_match = re.search(r'"MOBILE"\s*:\s*"(\d+)"', block)
        if mobile_match:
            record["MOBILE"] = mobile_match.group(1)
        
        name_match = re.search(r'"NAME"\s*:\s*"([^"]+)"', block)
        if name_match:
            record["NAME"] = name_match.group(1).strip()
        
        alt_match = re.search(r'"alt"\s*:\s*"([^"]+)"', block)
        if alt_match and alt_match.group(1) not in ['null', 'None', '']:
            record["alt"] = alt_match.group(1)
        
        circle_match = re.search(r'"circle"\s*:\s*"([^"]+)"', block)
        if circle_match:
            record["circle"] = circle_match.group(1)
        
        fname_match = re.search(r'"fname"\s*:\s*"([^"]+)"', block)
        if fname_match:
            record["fname"] = fname_match.group(1).strip()
        
        id_match = re.search(r'"id"\s*:\s*"(\d+)"', block)
        if id_match:
            record["id"] = id_match.group(1)
        
        if record and "MOBILE" in record:
            records.append(record)
    
    return records

def merge_all_records(objects, raw_text=""):
    all_records = []
    total = 0
    success = True
    tag = "@Felix_bhai"
    developer = "@Mikey_bhai1"
    
    for obj in objects:
        if "result" in obj:
            if "data" in obj["result"]:
                data = obj["result"]["data"]
                if isinstance(data, list):
                    all_records.extend(data)
                else:
                    all_records.append(data)
            if "total_records" in obj["result"]:
                total = obj["result"]["total_records"]
        elif "data" in obj:
            data = obj["data"]
            if isinstance(data, list):
                all_records.extend(data)
            else:
                all_records.append(data)
        elif "ADDRESS" in obj or "MOBILE" in obj:
            all_records.append(obj)
        
        if "total_records" in obj:
            total = obj["total_records"]
        if "success" in obj:
            success = obj["success"]
        if "tag" in obj:
            tag = obj["tag"]
        if "developer" in obj:
            developer = obj["developer"]
    
    if not all_records and raw_text:
        malformed_records = extract_records_from_malformed(raw_text)
        all_records.extend(malformed_records)
    
    unique = []
    seen = set()
    for r in all_records:
        mobile = r.get("MOBILE")
        if mobile:
            key = mobile
        else:
            key = str(r.get("NAME", "")) + str(r.get("id", ""))
        
        if key not in seen:
            seen.add(key)
            cleaned = {k: v for k, v in r.items() if v not in [None, "", " ", "null"]}
            unique.append(cleaned)
    
    final_total = total if total >= len(unique) else len(unique)
    
    return {
        "result": {"data": unique, "total_records": final_total},
        "success": success,
        "tag": tag,
        "developer": developer
    }

def is_bot(sender, text):
    if not sender:
        return False
    username = str(getattr(sender, 'username', '')).lower()
    if "usersxinfo" in username:
        return True
    if '"developer":' in text and '@UsersXinfo_admin' in text:
        return True
    return False

# ==================== AUTO DELETE ====================
async def delete_message(chat_id, msg_id, delay=AUTO_DELETE_SECONDS):
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except:
        pass

# ==================== SEND COMMAND ====================
async def send_cmd(cmd, val, timeout=40):
    global counter, pending
    
    if cmd not in COMMANDS:
        return {"success": False, "error": f"Unknown command: {cmd}"}
    
    target = COMMANDS[cmd]
    msg = f"/{cmd} {val}"
    counter += 1
    rid = str(counter)
    event = asyncio.Event()
    
    pending[rid] = {
        "cmd": cmd, "val": val, "event": event,
        "texts": [], "objects": [], "single_json": None,
        "is_multi_part": False, "done": False,
        "part_count": 0
    }
    
    try:
        sent = await client.send_message(target, msg)
        print(f"📤 /{cmd} {val}")
        asyncio.create_task(delete_message(target, sent.id))
        
        start_time = time.time()
        last_activity = time.time()
        
        while time.time() - start_time < timeout:
            try:
                await asyncio.wait_for(event.wait(), timeout=4)
                event.clear()
                last_activity = time.time()
            except asyncio.TimeoutError:
                pass
            
            if pending[rid]['part_count'] >= 2:
                await asyncio.sleep(2)
                break
            
            if pending[rid]['part_count'] == 1 and time.time() - last_activity >= 4:
                break
        
        all_texts = pending[rid].get("texts", [])
        all_objects = pending[rid].get("objects", [])
        single_json = pending[rid].get("single_json")
        is_multi = pending[rid]['part_count'] >= 2
        
        if not is_multi and single_json:
            result = single_json
            records = result.get("result", {}).get("data", [])
            print(f"✅ {len(records)} records")
        else:
            full_text = "\n".join(all_texts)
            if not all_objects:
                all_objects = extract_json_objects(full_text)
            result = merge_all_records(all_objects, full_text)
            total_records = result.get("result", {}).get("total_records", 0)
            print(f"✅ Merged {total_records} records from {pending[rid]['part_count']} parts")
        
        if isinstance(result, dict):
            result["tag"] = "@Felix_bhai"
            result["developer"] = "@Mikey_bhai1"
            if "developer_credits" in result:
                result["developer_credits"] = {
                    "telegram_channel": "@felix_modz1",
                    "telegram_id": "felixRDX_bot"
                }
        
        return {
            "success": True,
            "command": cmd,
            "value": val,
            "timestamp": datetime.now().isoformat(),
            "result": result,
            "stats": stats
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        pending.pop(rid, None)

# ==================== MESSAGE HANDLER ====================
@events.register(events.NewMessage)
async def handler(event):
    msg = event.message
    if not msg or not msg.text:
        return
    
    sender = await event.get_sender()
    text = msg.text
    
    if not is_bot(sender, text):
        return
    
    json_objects = extract_json_objects(text)
    
    for rid, req in list(pending.items()):
        if req.get("done"):
            continue
        
        if req["val"] in text:
            req["texts"].append(text)
            req["part_count"] += 1
            
            if json_objects and len(json_objects) == 1:
                obj = json_objects[0]
                if "total_records" in obj or "data" in obj or "result" in obj:
                    req["single_json"] = obj
                    req["done"] = True
                    req["event"].set()
                    break
            
            for obj in json_objects:
                if obj not in req["objects"]:
                    req["objects"].append(obj)
            
            req["event"].set()
            
            if "Part 2" in text or "COPY CODE" in text:
                req["is_multi_part"] = True
                req["done"] = True
                req["event"].set()
            
            break

# ==================== API ====================
@app.route('/api', methods=['GET'])
def api():
    key = request.args.get('key', '')
    if key != PERMANENT_KEY:
        return jsonify({"success": False, "error": "Invalid API key"}), 401
    
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
    
    future = asyncio.run_coroutine_threadsafe(send_cmd(cmd, val), loop)
    result = future.result(timeout=55)
    
    if result.get("success"):
        stats["success"] += 1
        return jsonify({
            "success": True,
            "command": cmd,
            "value": val,
            "timestamp": datetime.now().isoformat(),
            "result": result.get("result"),
            "stats": stats
        })
    else:
        stats["failed"] += 1
        return jsonify({"success": False, "error": result.get("error"), "stats": stats}), 500

# Individual endpoints
@app.route('/api/num', methods=['GET'])
def num(): return api()
@app.route('/api/adhar', methods=['GET'])
def adhar(): return api()
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
    return jsonify({"status": "ok", "stats": stats, "commands": len(COMMANDS)})

@app.route('/')
def home():
    group1_cmds = [c for c, g in COMMANDS.items() if g == GROUP1]
    group2_cmds = [c for c, g in COMMANDS.items() if g == GROUP2]
    
    return jsonify({
        "api": "Userbot API - Multi Group",
        "endpoint": "/api?key=daddyfelix&{command}={value}",
        "commands": list(COMMANDS.keys()),
        "groups": {
            "Group1 (@louraby)": group1_cmds,
            "Group2 (Users X Info)": group2_cmds
        },
        "example": "/api?key=daddyfelix&num=9876543210"
    })

# ==================== MAIN ====================
def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def main():
    global loop, client
    loop = asyncio.get_running_loop()
    
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    me = await client.get_me()
    
    group1_cmds = [c for c, g in COMMANDS.items() if g == GROUP1]
    group2_cmds = [c for c, g in COMMANDS.items() if g == GROUP2]
    
    print("\n" + "="*60)
    print(f"✅ USERBOT READY!")
    print(f"👤 Account: {me.first_name}")
    print(f"🗑️ Auto-delete: {AUTO_DELETE_SECONDS}s")
    print("="*60)
    print(f"📡 GROUP 1 (@louraby):")
    print(f"   {', '.join(group1_cmds)}")
    print(f"\n📡 GROUP 2 (Users X Info):")
    print(f"   {', '.join(group2_cmds)}")
    print("="*60)
    print(f"\n🌐 API: http://localhost:5000/api?key=daddyfelix&num=9876543210")
    print("="*60 + "\n")
    
    client.add_event_handler(handler)
    await client.run_until_disconnected()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())