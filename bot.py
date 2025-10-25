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

# 🔒 Blacklisted Numbers
BLACKLIST = ['9161636853', '9451180555', '6306791897']

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Stats
stats = {
    'total_requests': 0,
    'successful_searches': 0,
    'failed_searches': 0,
    'blacklist_hits': 0,
    'total_users': set(),
    'start_time': time.time()
}

cache: Dict[str, tuple] = {}
CACHE_DURATION = 300
user_states = {}

# ==================== Utilities ====================
def clean_number(number: str) -> str:
    cleaned = ''.join(filter(str.isdigit, number))
    if cleaned.startswith('91') and len(cleaned) > 10:
        cleaned = cleaned[2:]
    if cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if len(cleaned) > 10:
        cleaned = cleaned[-10:]
    return cleaned

def format_phone(phone: str) -> str:
    if not phone:
        return "Not Available"
    cleaned = clean_number(phone)
    if len(cleaned) == 10:
        return f"+91 {cleaned[:5]} {cleaned[5:]}"
    return phone

def format_address(address: str) -> str:
    if not address or address == "null":
        return "Not Available"
    parts = address.replace("!!", "!").split("!")
    cleaned_parts = [part.strip() for part in parts if part.strip() and part.strip() != "null" and len(part.strip()) > 2]
    if not cleaned_parts:
        return "Not Available"
    return "\n".join(cleaned_parts[:4])

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def is_blacklisted(number: str) -> bool:
    cleaned = clean_number(number)
    is_blocked = cleaned in BLACKLIST
    if is_blocked:
        stats['blacklist_hits'] += 1
    return is_blocked

def get_uptime() -> str:
    uptime = time.time() - stats['start_time']
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_from_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        del cache[key]
    return None

def save_to_cache(key: str, data: dict):
    cache[key] = (data, time.time())

# ==================== Keyboards ====================
def create_main_keyboard(is_admin_user=False):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔍 Search Number", callback_data="new_search"))
    if is_admin_user:
        markup.add(InlineKeyboardButton("⚙️ Admin", callback_data="admin_panel"))
    return markup

def create_admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
        InlineKeyboardButton("🏓 Ping", callback_data="admin_ping")
    )
    markup.add(
        InlineKeyboardButton("💾 System", callback_data="admin_system"),
        InlineKeyboardButton("ℹ️ Info", callback_data="admin_about")
    )
    markup.add(InlineKeyboardButton("← Back", callback_data="main_menu"))
    return markup

def create_result_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 New", callback_data="new_search"),
        InlineKeyboardButton("🏠 Home", callback_data="main_menu")
    )
    return markup

# ==================== API ====================
def fetch_mobile_info(mobile: str) -> Optional[dict]:
    if is_blacklisted(mobile):
        return {'blacklisted': True}
    
    cached_data = get_from_cache(mobile)
    if cached_data:
        return cached_data
    
    try:
        stats['total_requests'] += 1
        response = requests.get(API_URL.format(mobile), timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data and isinstance(data, dict):
                    save_to_cache(mobile, data)
                    stats['successful_searches'] += 1
                    return data
                else:
                    stats['failed_searches'] += 1
                    return None
            except:
                stats['failed_searches'] += 1
                return None
        else:
            stats['failed_searches'] += 1
            return None
    except:
        stats['failed_searches'] += 1
        return None

# ==================== Messages ====================
def get_welcome_message(user_name: str, is_admin_user: bool) -> str:
    admin_text = "\n\n🔐 <b>Admin Mode</b>" if is_admin_user else ""
    
    return f"""
<b>Mobile Info Lookup</b>

Hi <b>{user_name}</b> 👋

Fast and accurate mobile number information lookup.{admin_text}

<i>{DEVELOPER}</i>
"""

def get_blacklist_message(number: str) -> str:
    return f"""
<b>🚫 Access Denied</b>

Number: <code>{format_phone(number)}</code>

BKL MERA INFO NIKAL RHA HAI 🤡

<i>{DEVELOPER}</i>
"""

def get_admin_stats() -> str:
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_searches'] / stats['total_requests']) * 100
    
    return f"""
<b>📊 Statistics</b>

<b>Requests</b>
Total: <code>{stats['total_requests']}</code>
Success: <code>{stats['successful_searches']}</code> ({success_rate:.0f}%)
Failed: <code>{stats['failed_searches']}</code>
Blocked: <code>{stats['blacklist_hits']}</code>

<b>Users</b>
Active: <code>{len(stats['total_users'])}</code>
Cache: <code>{len(cache)}</code>

<b>Uptime</b>
{get_uptime()}

<i>{DEVELOPER}</i>
"""

def get_admin_about() -> str:
    return f"""
<b>ℹ️ Bot Info</b>

<b>Mobile Info Lookup</b>
Version 3.5 Premium

<b>Features</b>
• Real-time search
• Smart caching
• Blacklist protection
• Admin dashboard

<b>Stack</b>
Python 3.13 • Flask • Webhook

<i>{DEVELOPER}</i>
"""

def get_system_info() -> str:
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        return f"""
<b>💾 System</b>

<b>Resources</b>
CPU: <code>{cpu:.0f}%</code>
RAM: <code>{mem:.0f}%</code>
Disk: <code>{disk:.0f}%</code>

<b>Status</b>
Uptime: {get_uptime()}
Protected: {len(BLACKLIST)} numbers

✅ All systems operational

<i>{DEVELOPER}</i>
"""
    except:
        return f"<b>💾 System</b>\n\nMonitoring unavailable\n\n<i>{DEVELOPER}</i>"

def format_result_message(data: dict, searched_number: str) -> list:
    # Blacklist check
    if data.get('blacklisted'):
        return [get_blacklist_message(searched_number)]
    
    # Validate data
    if not data or not isinstance(data, dict):
        return [f"<b>No Results</b>\n\nNumber: <code>{format_phone(searched_number)}</code>\n\nNo information available.\n\n<i>{DEVELOPER}</i>"]
    
    data_array = data.get('data', [])
    
    if not data_array or not isinstance(data_array, list) or len(data_array) == 0:
        return [f"<b>No Results</b>\n\nNumber: <code>{format_phone(searched_number)}</code>\n\nNo information available.\n\n<i>{DEVELOPER}</i>"]
    
    # Remove duplicates
    unique_records = []
    seen = set()
    
    for record in data_array:
        if not isinstance(record, dict):
            continue
        record_tuple = tuple(sorted(record.items()))
        if record_tuple not in seen:
            seen.add(record_tuple)
            unique_records.append(record)
    
    if not unique_records:
        return [f"<b>No Results</b>\n\nNumber: <code>{format_phone(searched_number)}</code>\n\nNo information available.\n\n<i>{DEVELOPER}</i>"]
    
    messages = []
    
    for i, record in enumerate(unique_records[:3], 1):
        name = record.get('name', 'N/A')
        fname = record.get('fname', 'N/A')
        mobile_num = record.get('mobile', searched_number)
        alt = record.get('alt', '')
        circle = record.get('circle', 'N/A')
        uid = record.get('id', 'N/A')
        address = record.get('address', '')
        
        mobile_formatted = format_phone(mobile_num)
        alt_formatted = format_phone(alt) if alt and alt != 'null' else 'Not Available'
        address_formatted = format_address(address)
        
        message = f"""
<b>{name}</b>

<b>Personal</b>
Father: {fname}

<b>Contact</b>
Primary: <code>{mobile_formatted}</code>
Alternate: <code>{alt_formatted}</code>

<b>Network</b>
Circle: {circle}
ID: <code>{uid}</code>

<b>Address</b>
{address_formatted}

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
        "<b>⚙️ Admin Panel</b>\n\nSelect option:",
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
                "<b>🔍 Search</b>\n\nEnter 10-digit number\n\nExample: <code>9876543210</code>",
                chat_id, msg_id,
                parse_mode='HTML'
            )
        
        elif call.data == "admin_panel" and is_admin(user_id):
            bot.edit_message_text(
                "<b>⚙️ Admin Panel</b>\n\nSelect option:",
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
        print(f"Error: {e}")
        try:
            bot.answer_callback_query(call.id)
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    stats['total_users'].add(message.from_user.id)
    
    text = clean_number(message.text)
    is_waiting = message.chat.id in user_states
    is_valid_number = text.isdigit() and len(text) == 10
    
    if is_waiting or is_valid_number:
        if not text.isdigit() or len(text) != 10:
            bot.reply_to(
                message, 
                "<b>Invalid Number</b>\n\nSend 10 digits\nExample: <code>9876543210</code>", 
                parse_mode='HTML'
            )
            return
        
        searching_msg = bot.send_message(
            message.chat.id, 
            "🔍 <b>Searching...</b>", 
            parse_mode='HTML'
        )
        
        data = fetch_mobile_info(text)
        
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
                f"<b>Service Unavailable</b>\n\nTry again later.\n\n<i>{DEVELOPER}</i>",
                parse_mode='HTML',
                reply_markup=create_result_keyboard()
            )
        
        user_states.pop(message.chat.id, None)
    
    else:
        is_admin_user = is_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "Send a 10-digit number to search",
            parse_mode='HTML',
            reply_markup=create_main_keyboard(is_admin_user)
        )

# ==================== Flask ====================
@app.route('/', methods=['GET'])
def index():
    return {
        'status': 'running',
        'bot': 'Mobile Info Lookup',
        'version': '3.5',
        'developer': DEVELOPER,
        'uptime': get_uptime()
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
            print(f"✅ Webhook set: {webhook_url}")
            return True
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("Mobile Info Bot v3.5")
    print(f"Developer: {DEVELOPER}")
    print(f"Protected: {len(BLACKLIST)} numbers\n")
    
    if set_webhook():
        print(f"Admin ID: {ADMIN_ID}")
        port = int(os.environ.get('PORT', 10000))
        print(f"Port: {port}")
        print("Status: Ready\n")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("Failed to start")
