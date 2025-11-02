import telebot
import requests
import time
import psutil
import os
from datetime import datetime
from typing import Dict, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request
from collections import deque

# ==================== Config ====================
BOT_TOKEN = "8377073485:AAE5qZVldUNyMPVIzLSQiVXnBrxvOYWyovo"
WEBHOOK_URL = "https://botu-info-xjjf.onrender.com"
API_URL = "https://demon.taitanx.workers.dev/?mobile={}"
DEV = "@aadi_io"
ADMIN_ID = 8175884349
BLACKLIST = ['9161636853', '9451180555', '6306791897']

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ==================== Data ====================
stats = {
    'total': 0, 'success': 0, 'failed': 0, 'blocked': 0,
    'users': set(), 'start': time.time()
}
history = deque(maxlen=50)
activity = {}
cache: Dict[str, tuple] = {}
states = {}

CACHE_TIME = 300

# ==================== Utils ====================
def clean_num(num: str) -> str:
    n = ''.join(filter(str.isdigit, num))
    if n.startswith('91') and len(n) > 10: n = n[2:]
    if n.startswith('0') and len(n) == 11: n = n[1:]
    return n[-10:] if len(n) > 10 else n

def fmt_phone(p: str) -> str:
    if not p: return "N/A"
    n = clean_num(p)
    return f"+91 {n[:5]} {n[5:]}" if len(n) == 10 else p

def fmt_addr(a: str) -> str:
    if not a or a == "null": return "N/A"
    parts = [p.strip() for p in a.replace("!!", "!").split("!") 
             if p.strip() and p.strip() != "null" and len(p.strip()) > 2]
    return "\n".join(parts[:4]) if parts else "N/A"

def uptime() -> str:
    t = int(time.time() - stats['start'])
    d, r = divmod(t, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    return f"{d}d {h}h {m}m" if d > 0 else f"{h}h {m}m {s}s"

def log_search(uid: int, name: str, num: str, status: str):
    history.append({
        'time': datetime.now(), 'uid': uid, 
        'name': name, 'num': num, 'status': status
    })
    if uid not in activity:
        activity[uid] = {'name': name, 'count': 0, 'last': None}
    activity[uid]['count'] += 1
    activity[uid]['last'] = datetime.now()

def get_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, ts = cache[key]
        if time.time() - ts < CACHE_TIME:
            return data
        del cache[key]
    return None

def set_cache(key: str, data: dict):
    cache[key] = (data, time.time())

def ping() -> float:
    try:
        start = time.time()
        requests.get("https://api.telegram.org", timeout=5)
        return round((time.time() - start) * 1000, 2)
    except:
        return 0.0

# ==================== Keyboards ====================
def main_kb(admin=False):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("🔍 Search", callback_data="search"))
    if admin:
        kb.add(InlineKeyboardButton("⚙️ Admin", callback_data="admin"))
    kb.add(InlineKeyboardButton("💬 Developer", url=f"https://t.me/{DEV[1:]}"))
    return kb

def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📊 Stats", callback_data="stats"),
        InlineKeyboardButton("🏓 Ping", callback_data="ping")
    )
    kb.add(
        InlineKeyboardButton("📜 History", callback_data="history"),
        InlineKeyboardButton("👥 Users", callback_data="users")
    )
    kb.add(
        InlineKeyboardButton("💾 System", callback_data="system"),
        InlineKeyboardButton("🔙 Back", callback_data="menu")
    )
    return kb

def result_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔄 Again", callback_data="search"),
        InlineKeyboardButton("🏠 Menu", callback_data="menu")
    )
    return kb

# ==================== API ====================
def fetch_info(mobile: str) -> Optional[dict]:
    if clean_num(mobile) in BLACKLIST:
        stats['blocked'] += 1
        return {'blocked': True}
    
    cached = get_cache(mobile)
    if cached: return cached
    
    try:
        stats['total'] += 1
        r = requests.get(API_URL.format(mobile), timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data and isinstance(data, dict):
                set_cache(mobile, data)
                stats['success'] += 1
                return data
        stats['failed'] += 1
        return None
    except:
        stats['failed'] += 1
        return None

# ==================== Messages ====================
def welcome_msg(name: str, admin: bool) -> str:
    badge = "\n\n🔐 <b>Admin Access</b>" if admin else ""
    return f"""
<b>📱 Mobile Info Lookup</b>

👋 Welcome <b>{name}</b>

⚡️ Fast & Accurate
🔒 Secure & Private
💾 Smart Caching{badge}

<i>by {DEV}</i>
"""

def blocked_msg(num: str) -> str:
    return f"""
<b>🚫 Access Denied</b>

📱 <code>{fmt_phone(num)}</code>

⛔️ This number is protected

<b>Nice try! 🤡</b>

<i>{DEV}</i>
"""

def stats_msg() -> str:
    rate = (stats['success'] / stats['total'] * 100) if stats['total'] > 0 else 0
    return f"""
<b>📊 Statistics</b>

<b>Requests</b>
Total: <code>{stats['total']}</code>
Success: <code>{stats['success']}</code> ({rate:.1f}%)
Failed: <code>{stats['failed']}</code>

<b>Security</b>
Blocked: <code>{stats['blocked']}</code>
Protected: <code>{len(BLACKLIST)}</code>

<b>System</b>
Users: <code>{len(stats['users'])}</code>
Active: <code>{len(activity)}</code>
Cache: <code>{len(cache)}</code>
Uptime: <code>{uptime()}</code>

<i>{DEV}</i>
"""

def history_msg() -> str:
    if not history:
        return f"<b>📜 History</b>\n\nNo searches yet.\n\n<i>{DEV}</i>"
    
    txt = f"<b>📜 Last {min(10, len(history))} Searches</b>\n\n"
    
    for i, e in enumerate(list(history)[-10:][::-1], 1):
        icons = {'success': '✅', 'failed': '❌', 'blacklist': '🚫'}
        icon = icons.get(e['status'], '⚪️')
        t = e['time'].strftime('%H:%M')
        txt += f"{i}. {icon} <code>{fmt_phone(e['num'])}</code>\n"
        txt += f"   {e['name']} • {t}\n\n"
    
    return txt + f"<i>Total: {len(history)} • {DEV}</i>"

def users_msg() -> str:
    if not activity:
        return f"<b>👥 Users</b>\n\nNo activity yet.\n\n<i>{DEV}</i>"
    
    sorted_users = sorted(activity.items(), key=lambda x: x[1]['count'], reverse=True)
    txt = f"<b>👥 Top {min(10, len(sorted_users))} Users</b>\n\n"
    
    for i, (uid, d) in enumerate(sorted_users[:10], 1):
        last = d['last'].strftime('%d %b') if d['last'] else 'Never'
        txt += f"{i}. <b>{d['name']}</b>\n"
        txt += f"   🔍 {d['count']} • 🕐 {last}\n\n"
    
    return txt + f"<i>Total: {len(activity)} • {DEV}</i>"

def system_msg() -> str:
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        def bar(p):
            f = int(p / 10)
            return "█" * f + "░" * (10 - f)
        
        return f"""
<b>💾 System Resources</b>

<b>CPU</b> {bar(cpu)} <code>{cpu:.1f}%</code>

<b>Memory</b> {bar(mem)} <code>{mem:.1f}%</code>

<b>Disk</b> {bar(disk)} <code>{disk:.1f}%</code>

<b>Info</b>
Uptime: <code>{uptime()}</code>
Cache: <code>{len(cache)}</code> items

✅ All systems operational

<i>{DEV}</i>
"""
    except Exception as e:
        return f"<b>💾 System</b>\n\n⚠️ Error: {str(e)}\n\n<i>{DEV}</i>"

def format_result(data: dict, num: str) -> list:
    if data.get('blocked'):
        return [blocked_msg(num)]
    
    if not data or not isinstance(data, dict):
        return [f"<b>❌ No Results</b>\n\n📱 <code>{fmt_phone(num)}</code>\n\n<i>{DEV}</i>"]
    
    arr = data.get('data', [])
    if not arr or not isinstance(arr, list):
        return [f"<b>❌ No Data</b>\n\n📱 <code>{fmt_phone(num)}</code>\n\n<i>{DEV}</i>"]
    
    # Remove duplicates
    unique = []
    seen = set()
    for r in arr:
        if isinstance(r, dict):
            key = tuple(sorted(r.items()))
            if key not in seen:
                seen.add(key)
                unique.append(r)
    
    if not unique:
        return [f"<b>❌ Empty</b>\n\n📱 <code>{fmt_phone(num)}</code>\n\n<i>{DEV}</i>"]
    
    msgs = []
    for i, r in enumerate(unique[:3], 1):
        name = r.get('name', 'N/A')
        fname = r.get('fname', 'N/A')
        mobile = fmt_phone(r.get('mobile', num))
        alt = r.get('alt', '')
        alt_fmt = fmt_phone(alt) if alt and alt != 'null' else 'N/A'
        circle = r.get('circle', 'N/A')
        uid = r.get('id', 'N/A')
        addr = fmt_addr(r.get('address', ''))
        
        header = f"Result {i}" if len(unique) > 1 else "Result"
        
        msg = f"""
<b>✅ {header}</b>

👤 <b>{name}</b>
👨 {fname}

<b>Contact</b>
Primary: <code>{mobile}</code>
Alternate: <code>{alt_fmt}</code>

<b>Network</b>
Circle: {circle}
ID: <code>{uid}</code>

<b>Address</b>
{addr}

<i>{DEV}</i>
"""
        msgs.append(msg.strip())
    
    return msgs

# ==================== Handlers ====================
@bot.message_handler(commands=['start'])
def start(msg):
    print(f"📨 /start from {msg.from_user.id}")
    name = msg.from_user.first_name or "User"
    uid = msg.from_user.id
    stats['users'].add(uid)
    admin = uid == ADMIN_ID
    
    bot.send_message(
        msg.chat.id,
        welcome_msg(name, admin),
        parse_mode='HTML',
        reply_markup=main_kb(admin)
    )

@bot.message_handler(commands=['admin'])
def admin_cmd(msg):
    print(f"📨 /admin from {msg.from_user.id}")
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔️ <b>Access Denied</b>", parse_mode='HTML')
        return
    
    bot.send_message(
        msg.chat.id,
        "<b>⚙️ Admin Panel</b>\n\nSelect option:",
        parse_mode='HTML',
        reply_markup=admin_kb()
    )

@bot.callback_query_handler(func=lambda c: True)
def callback(call):
    print(f"🔘 Callback: {call.data} from {call.from_user.id}")
    try:
        cid = call.message.chat.id
        mid = call.message.message_id
        uid = call.from_user.id
        
        if call.data == "menu":
            name = call.from_user.first_name or "User"
            admin = uid == ADMIN_ID
            bot.edit_message_text(
                welcome_msg(name, admin),
                cid, mid, parse_mode='HTML',
                reply_markup=main_kb(admin)
            )
            states.pop(cid, None)
        
        elif call.data == "search":
            states[cid] = 'waiting'
            bot.edit_message_text(
                "<b>🔍 Search</b>\n\nSend 10-digit number\n\n💡 Example: <code>9876543210</code>",
                cid, mid, parse_mode='HTML'
            )
        
        elif call.data == "admin" and uid == ADMIN_ID:
            bot.edit_message_text(
                "<b>⚙️ Admin Panel</b>\n\nSelect option:",
                cid, mid, parse_mode='HTML',
                reply_markup=admin_kb()
            )
        
        elif call.data == "stats" and uid == ADMIN_ID:
            bot.edit_message_text(
                stats_msg(), cid, mid,
                parse_mode='HTML',
                reply_markup=admin_kb()
            )
        
        elif call.data == "ping" and uid == ADMIN_ID:
            bot.answer_callback_query(call.id, "🏓 Calculating...", show_alert=False)
            p = ping()
            bot.answer_callback_query(
                call.id,
                f"🏓 Pong!\n\n{p}ms",
                show_alert=True
            )
        
        elif call.data == "history" and uid == ADMIN_ID:
            bot.edit_message_text(
                history_msg(), cid, mid,
                parse_mode='HTML',
                reply_markup=admin_kb()
            )
        
        elif call.data == "users" and uid == ADMIN_ID:
            bot.edit_message_text(
                users_msg(), cid, mid,
                parse_mode='HTML',
                reply_markup=admin_kb()
            )
        
        elif call.data == "system" and uid == ADMIN_ID:
            bot.edit_message_text(
                system_msg(), cid, mid,
                parse_mode='HTML',
                reply_markup=admin_kb()
            )
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"❌ Callback Error: {e}")
        try:
            bot.answer_callback_query(call.id)
        except:
            pass

@bot.message_handler(func=lambda m: True)
def handle(msg):
    print(f"📨 Message from {msg.from_user.id}: {msg.text}")
    uid = msg.from_user.id
    name = msg.from_user.first_name or "User"
    stats['users'].add(uid)
    
    num = clean_num(msg.text)
    waiting = msg.chat.id in states
    valid = num.isdigit() and len(num) == 10
    
    if waiting or valid:
        if not valid:
            bot.reply_to(
                msg,
                "<b>❌ Invalid</b>\n\nSend valid 10-digit number",
                parse_mode='HTML'
            )
            return
        
        search_msg = bot.send_message(
            msg.chat.id,
            "<b>🔍 Searching...</b>",
            parse_mode='HTML'
        )
        
        data = fetch_info(num)
        
        # Log
        if data:
            status = 'blacklist' if data.get('blocked') else 'success'
        else:
            status = 'failed'
        
        log_search(uid, name, num, status)
        
        try:
            bot.delete_message(msg.chat.id, search_msg.message_id)
        except:
            pass
        
        if data:
            for m in format_result(data, num):
                bot.send_message(
                    msg.chat.id, m,
                    parse_mode='HTML',
                    reply_markup=result_kb()
                )
        else:
            bot.send_message(
                msg.chat.id,
                f"<b>⚠️ Error</b>\n\nUnable to fetch data\n\n<i>{DEV}</i>",
                parse_mode='HTML',
                reply_markup=result_kb()
            )
        
        states.pop(msg.chat.id, None)
    
    else:
        admin = uid == ADMIN_ID
        bot.send_message(
            msg.chat.id,
            "<b>💡 Tip</b>\n\nSend 10-digit number to search\n\n<i>or use button below</i>",
            parse_mode='HTML',
            reply_markup=main_kb(admin)
        )

# ==================== Flask ====================
@app.route('/', methods=['GET'])
def index():
    return {
        'status': 'running',
        'bot': 'Mobile Info Lookup',
        'version': '4.2',
        'developer': DEV,
        'webhook': f"{WEBHOOK_URL}/{BOT_TOKEN}",
        'stats': {
            'uptime': uptime(),
            'requests': stats['total'],
            'users': len(stats['users']),
            'searches': len(history)
        }
    }

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'healthy', 'uptime': uptime()}

@app.route('/webhook-info', methods=['GET'])
def webhook_info():
    """Check webhook status"""
    try:
        info = bot.get_webhook_info()
        return {
            'url': info.url,
            'pending_count': info.pending_update_count,
            'last_error': info.last_error_message,
            'last_error_date': info.last_error_date,
            'max_connections': info.max_connections
        }
    except Exception as e:
        return {'error': str(e)}

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    print(f"📥 Webhook received at {datetime.now()}")
    if request.headers.get('content-type') == 'application/json':
        json_str = request.get_data().decode('utf-8')
        print(f"📄 Data: {json_str[:100]}...")
        update = Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    print("⚠️ Invalid content-type")
    return '', 403

# ==================== Main ====================
def setup_webhook():
    try:
        print("🔄 Removing old webhook...")
        bot.remove_webhook()
        time.sleep(2)
        
        url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        print(f"🔗 Setting webhook: {url}")
        
        result = bot.set_webhook(url=url)
        
        if result:
            print("✅ Webhook set successfully!")
            
            # Verify webhook
            time.sleep(1)
            info = bot.get_webhook_info()
            print(f"📍 Webhook URL: {info.url}")
            print(f"📊 Pending updates: {info.pending_update_count}")
            if info.last_error_message:
                print(f"⚠️ Last error: {info.last_error_message}")
            
            return True
        else:
            print("❌ Failed to set webhook")
            return False
            
    except Exception as e:
        print(f"❌ Webhook Error: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Mobile Info Bot v4.2")
    print(f"👤 Developer: {DEV}")
    print(f"🔒 Protected: {len(BLACKLIST)} numbers")
    print(f"🆔 Admin ID: {ADMIN_ID}")
    print(f"🌐 Webhook: {WEBHOOK_URL}")
    print("="*50 + "\n")
    
    if setup_webhook():
        port = int(os.environ.get('PORT', 10000))
        print(f"\n✅ Port: {port}")
        print("✅ Bot is ready!")
        print(f"🌐 Visit: {WEBHOOK_URL}")
        print(f"🔍 Check webhook: {WEBHOOK_URL}/webhook-info")
        print("\n" + "="*50 + "\n")
        
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("\n❌ Failed to start - webhook setup error\n")
