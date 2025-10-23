import telebot
import requests
import time
import psutil
import os
from datetime import datetime
from typing import Dict, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request
from threading import Thread

# ==================== Configuration ====================
BOT_TOKEN = "8377073485:AAFEON1BT-j138BN5HDKiqpGKnlI1mQIZjE"
WEBHOOK_URL = "https://botu-info.onrender.com"
API_URL = "https://demon.taitanx.workers.dev/?mobile={}"
DEVELOPER = "@aadi_io"
ADMIN_ID = 8175884349

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Flask app
app = Flask(__name__)

# Statistics
stats = {
    'total_requests': 0,
    'successful_searches': 0,
    'failed_searches': 0,
    'total_users': set(),
    'start_time': time.time()
}

# Cache & States
cache: Dict[str, tuple] = {}
CACHE_DURATION = 300
user_states = {}

# ==================== Utility Functions ====================
def get_from_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        else:
            del cache[key]
    return None

def save_to_cache(key: str, data: dict):
    cache[key] = (data, time.time())

def format_phone(phone: str) -> str:
    if phone and phone.startswith('91'):
        return f"+91 {phone[2:7]} {phone[7:]}"
    return phone

def format_address(address: str) -> str:
    if not address:
        return "Not Available"
    parts = address.replace("!!", "!").split("!")
    formatted_parts = [f"  • {part.strip()}" for part in parts if part.strip() and part.strip() != "null"]
    return "\n".join(formatted_parts) if formatted_parts else "Not Available"

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_uptime() -> str:
    uptime = time.time() - stats['start_time']
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_system_stats() -> dict:
    try:
        return {
            'cpu': psutil.cpu_percent(interval=1),
            'memory': psutil.virtual_memory().percent,
            'disk': psutil.disk_usage('/').percent
        }
    except:
        return {'cpu': 0, 'memory': 0, 'disk': 0}

# ==================== Keyboards ====================
def create_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔍 Search", callback_data="new_search"),
        InlineKeyboardButton("📖 Help", callback_data="help")
    )
    markup.add(InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER[1:]}"))
    return markup

def create_admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        InlineKeyboardButton("🏓 Ping", callback_data="admin_ping")
    )
    markup.add(
        InlineKeyboardButton("ℹ️ About", callback_data="admin_about"),
        InlineKeyboardButton("💾 System", callback_data="admin_system")
    )
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
    return markup

def create_back_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("◀️ Back", callback_data="main_menu"))
    return markup

def create_search_again_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 New", callback_data="new_search"),
        InlineKeyboardButton("🏠 Menu", callback_data="main_menu")
    )
    return markup

# ==================== API Function ====================
def fetch_mobile_info(mobile: str) -> Optional[dict]:
    cached_data = get_from_cache(mobile)
    if cached_data:
        return cached_data
    
    try:
        stats['total_requests'] += 1
        response = requests.get(API_URL.format(mobile), timeout=10)
        if response.status_code == 200:
            data = response.json()
            save_to_cache(mobile, data)
            stats['successful_searches'] += 1
            return data
        stats['failed_searches'] += 1
    except Exception as e:
        print(f"API Error: {e}")
        stats['failed_searches'] += 1
    return None

# ==================== Messages ====================
def get_welcome_message(user_name: str, user_id: int) -> str:
    admin_text = "\n\n🔐 <b>Admin Access</b>" if is_admin(user_id) else ""
    return f"""
<b>👋 Welcome, {user_name}!</b>

<b>📱 Mobile Info Lookup Bot</b>

<b>✨ Features:</b>
✓ Fast & Accurate
✓ Smart Caching
✓ Professional UI
✓ Detailed Info

<b>🚀 Quick Start:</b>
• Click "🔍 Search"
• Or send 10-digit number{admin_text}

<i>Dev: {DEVELOPER}</i>
"""

def get_help_message() -> str:
    return f"""
<b>📖 User Guide</b>

<b>🔍 How to Search:</b>
1. Click "🔍 Search"
2. Enter 10-digit number
3. Get instant results

<b>💡 Tips:</b>
• No +91 prefix needed
• Example: <code>8789793154</code>
• Direct input supported

<b>📋 Info Provided:</b>
✓ Name & Father's Name
✓ Complete Address
✓ Alternate Number
✓ Telecom Circle

<i>Dev: {DEVELOPER}</i>
"""

def get_admin_stats() -> str:
    return f"""
<b>📊 Bot Statistics</b>

<b>📈 Usage:</b>
• Total Requests: <code>{stats['total_requests']}</code>
• Successful: <code>{stats['successful_searches']}</code>
• Failed: <code>{stats['failed_searches']}</code>
• Users: <code>{len(stats['total_users'])}</code>
• Cache: <code>{len(cache)}</code>

<b>⏱ Uptime:</b>
<code>{get_uptime()}</code>

<b>📅 Started:</b>
<code>{datetime.fromtimestamp(stats['start_time']).strftime('%Y-%m-%d %H:%M')}</code>

<i>Admin: {DEVELOPER}</i>
"""

def get_admin_about() -> str:
    return f"""
<b>ℹ️ About Bot</b>

<b>📱 Information:</b>
• Name: Mobile Info Bot
• Version: 2.0 Pro
• Dev: {DEVELOPER}
• Language: Python 3.13
• Mode: Webhook

<b>🔧 Features:</b>
• Advanced Caching
• Admin Dashboard
• Real-time Stats
• Auto Error Handling

<b>🌐 Integration:</b>
• API: Demon TaitanX
• Timeout: 10s
• Cache: 5 minutes

<i>Built with ❤️</i>
"""

def get_system_info() -> str:
    try:
        sys_stats = get_system_stats()
        return f"""
<b>💾 System Info</b>

<b>⚙️ Resources:</b>
• CPU: <code>{sys_stats['cpu']:.1f}%</code>
• Memory: <code>{sys_stats['memory']:.1f}%</code>
• Disk: <code>{sys_stats['disk']:.1f}%</code>

<b>🔄 Uptime:</b>
<code>{get_uptime()}</code>

<b>🌐 Webhook:</b>
<code>{WEBHOOK_URL}</code>

<i>Status: ✅ Healthy</i>
"""
    except:
        return "<b>⚠️ Info unavailable</b>"

def format_result_message(data: dict, mobile: str) -> list:
    if not data.get('data') or len(data['data']) == 0:
        return [f"""
<b>❌ No Results</b>

No info for: <code>{mobile}</code>

<i>Verify and try again.</i>
<i>Dev: {DEVELOPER}</i>
"""]
    
    unique_records = []
    seen = set()
    for record in data['data']:
        record_tuple = tuple(sorted(record.items()))
        if record_tuple not in seen:
            seen.add(record_tuple)
            unique_records.append(record)
    
    messages = []
    for i, record in enumerate(unique_records[:3], 1):
        name = record.get('name', 'N/A')
        fname = record.get('fname', 'N/A')
        mobile_num = record.get('mobile', 'N/A')
        alt = record.get('alt', '')
        circle = record.get('circle', 'N/A')
        uid = record.get('id', 'N/A')
        address = format_address(record.get('address', ''))
        
        alt_formatted = format_phone(alt) if alt and alt != 'null' else 'Not Available'
        
        message = f"""
<b>📱 Result #{i}</b>

<b>👤 Personal</b>
• Name: <code>{name}</code>
• Father: <code>{fname}</code>

<b>📞 Contact</b>
• Primary: <code>{mobile_num}</code>
• Alternate: <code>{alt_formatted}</code>

<b>🌐 Network</b>
• Circle: <code>{circle}</code>
• ID: <code>{uid}</code>

<b>📍 Address</b>
{address}

<i>Dev: {DEVELOPER}</i>
"""
        messages.append(message)
    
    return messages

# ==================== Bot Handlers ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_name = message.from_user.first_name or "User"
    user_id = message.from_user.id
    stats['total_users'].add(user_id)
    
    bot.send_message(
        message.chat.id,
        get_welcome_message(user_name, user_id),
        parse_mode='HTML',
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔️ Access Denied")
        return
    
    bot.send_message(
        message.chat.id,
        "<b>🔐 Admin Panel</b>\n\nSelect option:",
        parse_mode='HTML',
        reply_markup=create_admin_keyboard()
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.send_message(
        message.chat.id,
        get_help_message(),
        parse_mode='HTML',
        reply_markup=create_back_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        if call.data == "main_menu":
            user_name = call.from_user.first_name or "User"
            user_id = call.from_user.id
            bot.edit_message_text(
                get_welcome_message(user_name, user_id),
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_main_keyboard()
            )
            user_states.pop(call.message.chat.id, None)
        
        elif call.data == "help":
            bot.edit_message_text(
                get_help_message(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_back_keyboard()
            )
        
        elif call.data == "new_search":
            user_states[call.message.chat.id] = 'waiting_for_number'
            bot.edit_message_text(
                "<b>🔍 Mobile Search</b>\n\nEnter 10-digit number:\n<i>Example: 8789793154</i>",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML'
            )
        
        elif call.data == "admin_stats" and is_admin(call.from_user.id):
            bot.edit_message_text(
                get_admin_stats(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        elif call.data == "admin_ping" and is_admin(call.from_user.id):
            start = time.time()
            ping = round((time.time() - start) * 1000, 2)
            bot.answer_callback_query(call.id, f"🏓 Pong! {ping}ms", show_alert=True)
        
        elif call.data == "admin_about" and is_admin(call.from_user.id):
            bot.edit_message_text(
                get_admin_about(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        elif call.data == "admin_system" and is_admin(call.from_user.id):
            bot.edit_message_text(
                get_system_info(),
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Callback error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    stats['total_users'].add(message.from_user.id)
    text = message.text.strip().replace(" ", "").replace("-", "").replace("+91", "")
    
    if message.chat.id in user_states or (text.isdigit() and len(text) == 10):
        if not text.isdigit() or len(text) != 10:
            bot.reply_to(message, "❌ Invalid. Send 10 digits.\n<i>Ex: 8789793154</i>", parse_mode='HTML')
            return
        
        searching_msg = bot.send_message(message.chat.id, "🔍 <b>Searching...</b>", parse_mode='HTML')
        
        data = fetch_mobile_info(text)
        
        if data:
            messages = format_result_message(data, text)
            try:
                bot.delete_message(message.chat.id, searching_msg.message_id)
            except:
                pass
            
            for msg in messages:
                bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=create_search_again_keyboard())
        else:
            bot.edit_message_text(
                f"<b>⚠️ Service Unavailable</b>\n\nTry again later.\n\n<i>Contact: {DEVELOPER}</i>",
                message.chat.id,
                searching_msg.message_id,
                parse_mode='HTML',
                reply_markup=create_search_again_keyboard()
            )
        
        user_states.pop(message.chat.id, None)
    else:
        bot.send_message(
            message.chat.id,
            f"ℹ️ <b>How can I help?</b>\n\n• Click '🔍 Search'\n• Or send 10-digit number\n\n<i>Dev: {DEVELOPER}</i>",
            parse_mode='HTML',
            reply_markup=create_main_keyboard()
        )

# ==================== Flask Routes ====================
@app.route('/', methods=['GET'])
def index():
    uptime = time.time() - stats['start_time']
    return {
        'status': 'running',
        'bot': 'Mobile Info Bot',
        'developer': DEVELOPER,
        'mode': 'webhook',
        'uptime_seconds': int(uptime),
        'total_requests': stats['total_requests'],
        'webhook_url': WEBHOOK_URL
    }

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok', 'uptime': get_uptime()}

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return '', 403

# ==================== Main ====================
def set_webhook():
    """Set webhook on Telegram"""
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        result = bot.set_webhook(url=webhook_url)
        if result:
            print(f"✅ Webhook set: {webhook_url}")
            return True
        else:
            print("❌ Webhook setup failed")
            return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════╗
║   Mobile Info Bot - Professional v2.0  ║
║   Developer: @aadi_io                  ║
║   Mode: Webhook                        ║
╚════════════════════════════════════════╝
    """)
    
    # Set webhook
    if set_webhook():
        print(f"✅ Admin ID: {ADMIN_ID}")
        print(f"✅ Webhook URL: {WEBHOOK_URL}")
        
        # Start Flask server
        port = int(os.environ.get('PORT', 10000))
        print(f"✅ Starting server on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("❌ Failed to start bot")
