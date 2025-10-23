import telebot
import requests
import time
import psutil
import os
from datetime import datetime
from typing import Dict, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request

# ==================== Configuration ====================
BOT_TOKEN = "8377073485:AAFEON1BT-j138BN5HDKiqpGKnlI1mQIZjE"
WEBHOOK_URL = "https://botu-info.onrender.com"
API_URL = "https://demon.taitanx.workers.dev/?mobile={}"
DEVELOPER = "@aadi_io"
ADMIN_ID = 8175884349

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Stats
stats = {
    'total_requests': 0,
    'successful_searches': 0,
    'failed_searches': 0,
    'total_users': set(),
    'start_time': time.time()
}

cache: Dict[str, tuple] = {}
CACHE_DURATION = 300
user_states = {}

# ==================== Utilities ====================
def get_from_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        del cache[key]
    return None

def save_to_cache(key: str, data: dict):
    cache[key] = (data, time.time())

def format_phone(phone: str) -> str:
    """Format: +91 98765 43210"""
    if phone and len(phone) >= 10:
        clean = phone.replace('+', '').replace('-', '').replace(' ', '')
        if clean.startswith('91'):
            clean = clean[2:]
        return f"+91 {clean[:5]} {clean[5:]}"
    return phone

def format_address(address: str) -> str:
    """Clean address formatting"""
    if not address or address == "null":
        return "Not Available"
    
    # Split by !! and clean
    parts = [p.strip() for p in address.replace("!!", "!").split("!") if p.strip() and p.strip() != "null"]
    
    if not parts:
        return "Not Available"
    
    # Format cleanly
    formatted = []
    for part in parts[:4]:  # Limit to 4 lines
        if len(part) > 2:
            formatted.append(part)
    
    return "\n".join(formatted)

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_uptime() -> str:
    uptime = time.time() - stats['start_time']
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

# ==================== Keyboards ====================
def create_main_keyboard(is_admin_user=False):
    """Ultra-clean main keyboard"""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔍 Start Search", callback_data="new_search"))
    if is_admin_user:
        markup.add(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    markup.add(InlineKeyboardButton("💬 Contact Dev", url=f"https://t.me/{DEVELOPER[1:]}"))
    return markup

def create_admin_keyboard():
    """Clean admin keyboard"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        InlineKeyboardButton("🏓 Ping", callback_data="admin_ping")
    )
    markup.add(
        InlineKeyboardButton("💾 System", callback_data="admin_system"),
        InlineKeyboardButton("ℹ️ About", callback_data="admin_about")
    )
    markup.add(InlineKeyboardButton("⬅️ Back", callback_data="main_menu"))
    return markup

def create_result_keyboard():
    """Clean result keyboard"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 New Search", callback_data="new_search"),
        InlineKeyboardButton("🏠 Home", callback_data="main_menu")
    )
    return markup

# ==================== API ====================
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
def get_welcome_message(user_name: str, is_admin_user: bool) -> str:
    """Ultra-minimal welcome"""
    admin_badge = "\n\n🔐 <b>Admin Access Enabled</b>" if is_admin_user else ""
    
    return f"""
<b>Hello {user_name} 👋</b>

<b>Mobile Information Lookup</b>

Fast, accurate mobile number searches with detailed information.{admin_badge}

<i>Developed by {DEVELOPER}</i>
"""

def get_admin_stats() -> str:
    """Clean stats display"""
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_searches'] / stats['total_requests']) * 100
    
    return f"""
<b>📊 Statistics</b>

<b>Requests:</b> {stats['total_requests']}
<b>Success:</b> {stats['successful_searches']} ({success_rate:.1f}%)
<b>Failed:</b> {stats['failed_searches']}
<b>Users:</b> {len(stats['total_users'])}
<b>Cache:</b> {len(cache)} items

<b>Uptime:</b> {get_uptime()}
<b>Started:</b> {datetime.fromtimestamp(stats['start_time']).strftime('%d %b %Y, %H:%M')}
"""

def get_admin_about() -> str:
    """Clean about info"""
    return f"""
<b>ℹ️ Bot Information</b>

<b>Name:</b> Mobile Info Lookup Bot
<b>Version:</b> 2.5 Professional
<b>Developer:</b> {DEVELOPER}
<b>Mode:</b> Webhook

<b>Features:</b>
• Advanced caching system
• Real-time statistics
• Admin dashboard
• Clean minimalist UI

<b>Tech Stack:</b>
• Python 3.13
• pyTelegramBotAPI
• Flask + Webhook
"""

def get_system_info() -> str:
    """Clean system info"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        return f"""
<b>💾 System Resources</b>

<b>CPU:</b> {cpu:.1f}%
<b>Memory:</b> {mem:.1f}%
<b>Disk:</b> {disk:.1f}%

<b>Uptime:</b> {get_uptime()}

<b>Status:</b> ✅ Healthy
"""
    except:
        return "<b>💾 System Resources</b>\n\n<i>Information unavailable</i>"

def format_result_message(data: dict, mobile: str) -> list:
    """Ultra-clean result formatting"""
    if not data.get('data') or len(data['data']) == 0:
        return [f"""
<b>No Results Found</b>

Number: <code>{mobile}</code>

Please verify the number and try again.
"""]
    
    # Remove duplicates
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
        mobile_num = record.get('mobile', mobile)
        alt = record.get('alt', '')
        circle = record.get('circle', 'N/A')
        uid = record.get('id', 'N/A')
        address = format_address(record.get('address', ''))
        
        # Format alternate
        if alt and alt != 'null' and len(alt) >= 10:
            alt_formatted = format_phone(alt)
        else:
            alt_formatted = 'Not Available'
        
        # Clean mobile format
        mobile_formatted = format_phone(mobile_num)
        
        message = f"""
<b>Search Result</b>

<b>👤 {name}</b>
Father: {fname}

<b>📱 Contact</b>
Primary: <code>{mobile_formatted}</code>
Alternate: <code>{alt_formatted}</code>

<b>🌐 Network</b>
Circle: {circle}
ID: <code>{uid}</code>

<b>📍 Address</b>
{address}

<i>{DEVELOPER}</i>
"""
        messages.append(message.strip())
    
    return messages

# ==================== Handlers ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    user_name = message.from_user.first_name or "User"
    user_id = message.from_user.id
    stats['total_users'].add(user_id)
    is_admin_user = is_admin(user_id)
    
    bot.send_message(
        message.chat.id,
        get_welcome_message(user_name, is_admin_user),
        parse_mode='HTML',
        reply_markup=create_main_keyboard(is_admin_user)
    )

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "⛔️ Access Denied")
        return
    
    bot.send_message(
        message.chat.id,
        "<b>⚙️ Admin Panel</b>\n\nSelect an option below:",
        parse_mode='HTML',
        reply_markup=create_admin_keyboard()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    try:
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        user_id = call.from_user.id
        
        if call.data == "main_menu":
            user_name = call.from_user.first_name or "User"
            is_admin_user = is_admin(user_id)
            bot.edit_message_text(
                get_welcome_message(user_name, is_admin_user),
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_main_keyboard(is_admin_user)
            )
            user_states.pop(chat_id, None)
        
        elif call.data == "new_search":
            user_states[chat_id] = 'waiting_for_number'
            bot.edit_message_text(
                "<b>🔍 Number Search</b>\n\nEnter 10-digit mobile number\n\n<i>Example: 9876543210</i>",
                chat_id, msg_id,
                parse_mode='HTML'
            )
        
        elif call.data == "admin_panel" and is_admin(user_id):
            bot.edit_message_text(
                "<b>⚙️ Admin Panel</b>\n\nSelect an option below:",
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        elif call.data == "admin_stats" and is_admin(user_id):
            bot.edit_message_text(
                get_admin_stats(),
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        elif call.data == "admin_ping" and is_admin(user_id):
            start = time.time()
            ping = round((time.time() - start) * 1000, 2)
            bot.answer_callback_query(call.id, f"🏓 {ping}ms", show_alert=True)
        
        elif call.data == "admin_about" and is_admin(user_id):
            bot.edit_message_text(
                get_admin_about(),
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        elif call.data == "admin_system" and is_admin(user_id):
            bot.edit_message_text(
                get_system_info(),
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Callback error: {e}")
        try:
            bot.answer_callback_query(call.id)
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    stats['total_users'].add(message.from_user.id)
    text = message.text.strip().replace(" ", "").replace("-", "").replace("+", "").replace("91", "", 1)
    
    # Check if waiting for input or direct number
    if message.chat.id in user_states or (text.isdigit() and len(text) == 10):
        if not text.isdigit() or len(text) != 10:
            bot.reply_to(
                message, 
                "❌ Invalid number\n\nSend 10 digits only\nExample: <code>9876543210</code>", 
                parse_mode='HTML'
            )
            return
        
        # Show searching
        searching_msg = bot.send_message(
            message.chat.id, 
            "🔍 <b>Searching...</b>", 
            parse_mode='HTML'
        )
        
        # Fetch data
        data = fetch_mobile_info(text)
        
        # Delete searching message
        try:
            bot.delete_message(message.chat.id, searching_msg.message_id)
        except:
            pass
        
        if data:
            messages = format_result_message(data, text)
            for msg in messages:
                bot.send_message(
                    message.chat.id, 
                    msg, 
                    parse_mode='HTML', 
                    reply_markup=create_result_keyboard()
                )
        else:
            bot.send_message(
                message.chat.id,
                f"<b>⚠️ Service Unavailable</b>\n\nPlease try again later\n\n<i>{DEVELOPER}</i>",
                parse_mode='HTML',
                reply_markup=create_result_keyboard()
            )
        
        user_states.pop(message.chat.id, None)
    else:
        is_admin_user = is_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "Send a 10-digit mobile number to search\n\nor use the button below",
            parse_mode='HTML',
            reply_markup=create_main_keyboard(is_admin_user)
        )

# ==================== Flask ====================
@app.route('/', methods=['GET'])
def index():
    return {
        'status': 'running',
        'bot': 'Mobile Info Bot',
        'version': '2.5',
        'developer': DEVELOPER,
        'uptime': get_uptime(),
        'requests': stats['total_requests']
    }

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok'}

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return '', 403

# ==================== Main ====================
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(1)
        webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        result = bot.set_webhook(url=webhook_url)
        if result:
            print(f"✅ Webhook: {webhook_url}")
            return True
        return False
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        return False

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════╗
║  Mobile Info Bot v2.5 Professional ║
║  Developer: @aadi_io               ║
╚═══════════════════════════════════╝
    """)
    
    if set_webhook():
        print(f"✅ Admin: {ADMIN_ID}")
        port = int(os.environ.get('PORT', 10000))
        print(f"✅ Port: {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("❌ Failed to start")
