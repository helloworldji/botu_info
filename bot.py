import telebot
import requests
import time
import psutil
import os
from datetime import datetime
from typing import Dict, Optional, List
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from flask import Flask, request
from collections import deque

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

# Advanced Stats & Tracking
stats = {
    'total_requests': 0,
    'successful_searches': 0,
    'failed_searches': 0,
    'blacklist_hits': 0,
    'total_users': set(),
    'start_time': time.time()
}

# 📊 Search History (last 50 searches)
search_history: deque = deque(maxlen=50)

# User activity tracking
user_activity = {}

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
    days = hours // 24
    hours = hours % 24
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m {seconds}s"

def log_search(user_id: int, user_name: str, number: str, status: str):
    """Log search activity"""
    search_entry = {
        'timestamp': datetime.now(),
        'user_id': user_id,
        'user_name': user_name,
        'number': number,
        'status': status
    }
    search_history.append(search_entry)
    
    # Track user activity
    if user_id not in user_activity:
        user_activity[user_id] = {'name': user_name, 'searches': 0, 'last_search': None}
    
    user_activity[user_id]['searches'] += 1
    user_activity[user_id]['last_search'] = datetime.now()

def get_from_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        del cache[key]
    return None

def save_to_cache(key: str, data: dict):
    cache[key] = (data, time.time())

def calculate_ping() -> float:
    """Calculate real API ping"""
    try:
        start = time.time()
        requests.get("https://api.telegram.org", timeout=5)
        end = time.time()
        return round((end - start) * 1000, 2)
    except:
        return 0.0

# ==================== Advanced Keyboards ====================
def create_main_keyboard(is_admin_user=False):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔍 Search Number", callback_data="new_search")
    )
    if is_admin_user:
        markup.add(
            InlineKeyboardButton("⚙️ Admin Dashboard", callback_data="admin_panel")
        )
    markup.add(
        InlineKeyboardButton("💬 Contact Developer", url=f"https://t.me/{DEVELOPER[1:]}")
    )
    return markup

def create_admin_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
        InlineKeyboardButton("🏓 Test Ping", callback_data="admin_ping")
    )
    markup.add(
        InlineKeyboardButton("📜 Search History", callback_data="admin_history"),
        InlineKeyboardButton("👥 User Activity", callback_data="admin_users")
    )
    markup.add(
        InlineKeyboardButton("💾 System Info", callback_data="admin_system"),
        InlineKeyboardButton("ℹ️ Bot Info", callback_data="admin_about")
    )
    markup.add(
        InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")
    )
    return markup

def create_result_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Search Again", callback_data="new_search"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
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

# ==================== Advanced Messages ====================
def get_welcome_message(user_name: str, is_admin_user: bool) -> str:
    admin_badge = "\n\n🔐 <b>Admin Access Enabled</b>" if is_admin_user else ""
    
    return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│  📱 <b>Mobile Info Lookup</b>  │
╰━━━━━━━━━━━━━━━━━━━━━╯

👋 Welcome <b>{user_name}</b>!

🎯 <b>What I Do:</b>
   ⚡️ Fast mobile number lookup
   🎯 Accurate information
   🔒 Secure & private
   💾 Smart caching{admin_badge}

━━━━━━━━━━━━━━━━━━━━━
<i>Powered by {DEVELOPER}</i>
"""

def get_blacklist_message(number: str) -> str:
    return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│    🚫 <b>Access Denied</b>    │
╰━━━━━━━━━━━━━━━━━━━━━╯

📱 Number: <code>{format_phone(number)}</code>

⛔️ <b>This number is protected</b>

<b>BKL MERA INFO NIKAL RHA HAI</b> 🤡

━━━━━━━━━━━━━━━━━━━━━
<i>Nice try! • {DEVELOPER}</i>
"""

def get_admin_stats() -> str:
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_searches'] / stats['total_requests']) * 100
    
    return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│   📊 <b>Bot Statistics</b>    │
╰━━━━━━━━━━━━━━━━━━━━━╯

📈 <b>Request Metrics</b>
├─ Total: <code>{stats['total_requests']}</code>
├─ Success: <code>{stats['successful_searches']}</code>
├─ Failed: <code>{stats['failed_searches']}</code>
└─ Success Rate: <code>{success_rate:.1f}%</code>

🔒 <b>Security</b>
├─ Blocked: <code>{stats['blacklist_hits']}</code>
└─ Protected: <code>{len(BLACKLIST)}</code> numbers

👥 <b>Users</b>
├─ Total: <code>{len(stats['total_users'])}</code>
├─ Active: <code>{len(user_activity)}</code>
└─ Cache: <code>{len(cache)}</code> items

⏱ <b>System</b>
├─ Uptime: <code>{get_uptime()}</code>
└─ Started: <code>{datetime.fromtimestamp(stats['start_time']).strftime('%d %b, %H:%M')}</code>

━━━━━━━━━━━━━━━━━━━━━
<i>Admin Panel • {DEVELOPER}</i>
"""

def get_search_history() -> str:
    if not search_history:
        return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│  📜 <b>Search History</b>     │
╰━━━━━━━━━━━━━━━━━━━━━╯

No searches recorded yet.

━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""
    
    history_text = "╭━━━━━━━━━━━━━━━━━━━━━╮\n│  📜 <b>Search History</b>     │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    history_text += f"<b>Last {min(10, len(search_history))} Searches:</b>\n\n"
    
    for i, entry in enumerate(list(search_history)[-10:][::-1], 1):
        timestamp = entry['timestamp'].strftime('%H:%M:%S')
        user_name = entry['user_name']
        number = format_phone(entry['number'])
        status = entry['status']
        
        status_emoji = {
            'success': '✅',
            'failed': '❌',
            'blacklist': '🚫'
        }.get(status, '⚪️')
        
        history_text += f"{i}. {status_emoji} <code>{number}</code>\n"
        history_text += f"   👤 {user_name} • ⏰ {timestamp}\n\n"
    
    history_text += f"━━━━━━━━━━━━━━━━━━━━━\n<i>Total: {len(search_history)} searches • {DEVELOPER}</i>"
    
    return history_text

def get_user_activity() -> str:
    if not user_activity:
        return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│  👥 <b>User Activity</b>      │
╰━━━━━━━━━━━━━━━━━━━━━╯

No user activity recorded yet.

━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""
    
    # Sort by search count
    sorted_users = sorted(user_activity.items(), key=lambda x: x[1]['searches'], reverse=True)
    
    activity_text = "╭━━━━━━━━━━━━━━━━━━━━━╮\n│  👥 <b>User Activity</b>      │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    activity_text += f"<b>Top {min(10, len(sorted_users))} Active Users:</b>\n\n"
    
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        name = data['name']
        searches = data['searches']
        last = data['last_search'].strftime('%d %b, %H:%M') if data['last_search'] else 'Never'
        
        activity_text += f"{i}. 👤 <b>{name}</b>\n"
        activity_text += f"   🔍 {searches} searches • 🕐 {last}\n\n"
    
    activity_text += f"━━━━━━━━━━━━━━━━━━━━━\n<i>Total: {len(user_activity)} users • {DEVELOPER}</i>"
    
    return activity_text

def get_admin_about() -> str:
    return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│   ℹ️ <b>Bot Information</b>   │
╰━━━━━━━━━━━━━━━━━━━━━╯

📱 <b>Mobile Info Lookup Bot</b>
Version 4.0 Advanced

✨ <b>Features</b>
├─ 🔍 Real-time search
├─ 💾 Smart caching (5min)
├─ 🔒 Blacklist protection
├─ 📊 Advanced analytics
├─ 📜 Search history
└─ 👥 User tracking

🛠 <b>Tech Stack</b>
├─ Python 3.13
├─ pyTelegramBotAPI
├─ Flask Webhook
├─ psutil Monitoring
└─ REST API Integration

🔧 <b>Admin Tools</b>
├─ Real-time stats
├─ User activity logs
├─ Search history
└─ System monitoring

━━━━━━━━━━━━━━━━━━━━━
<i>Built with ❤️ by {DEVELOPER}</i>
"""

def get_system_info() -> str:
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        # Create visual bars
        def create_bar(percent):
            filled = int(percent / 10)
            return "█" * filled + "░" * (10 - filled)
        
        return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│  💾 <b>System Resources</b>   │
╰━━━━━━━━━━━━━━━━━━━━━╯

⚙️ <b>CPU Usage</b>
{create_bar(cpu)}
<code>{cpu:.1f}%</code>

🧠 <b>Memory Usage</b>
{create_bar(mem)}
<code>{mem:.1f}%</code>

💿 <b>Disk Usage</b>
{create_bar(disk)}
<code>{disk:.1f}%</code>

━━━━━━━━━━━━━━━━━━━━━

📊 <b>Performance</b>
├─ Uptime: <code>{get_uptime()}</code>
├─ Cache: <code>{len(cache)}</code> items
└─ Protected: <code>{len(BLACKLIST)}</code> numbers

🌐 <b>Status</b>
✅ All systems operational

━━━━━━━━━━━━━━━━━━━━━
<i>System Monitor • {DEVELOPER}</i>
"""
    except Exception as e:
        return f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│  💾 <b>System Resources</b>   │
╰━━━━━━━━━━━━━━━━━━━━━╯

⚠️ Monitoring unavailable

{str(e)}

━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""

def format_result_message(data: dict, searched_number: str) -> list:
    # Blacklist check
    if data.get('blacklisted'):
        return [get_blacklist_message(searched_number)]
    
    # Validate data
    if not data or not isinstance(data, dict):
        return [f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│   ❌ <b>No Results</b>        │
╰━━━━━━━━━━━━━━━━━━━━━╯

📱 Number: <code>{format_phone(searched_number)}</code>

No information available for this number.

━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""]
    
    data_array = data.get('data', [])
    
    if not data_array or not isinstance(data_array, list) or len(data_array) == 0:
        return [f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│   ❌ <b>No Results</b>        │
╰━━━━━━━━━━━━━━━━━━━━━╯

📱 Number: <code>{format_phone(searched_number)}</code>

No information available.

━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""]
    
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
        return [f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│   ❌ <b>No Results</b>        │
╰━━━━━━━━━━━━━━━━━━━━━╯

📱 Number: <code>{format_phone(searched_number)}</code>

━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""]
    
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
        
        result_header = f"Result {i}" if len(unique_records) > 1 else "Search Result"
        
        message = f"""
╭━━━━━━━━━━━━━━━━━━━━━╮
│   ✅ <b>{result_header}</b>      │
╰━━━━━━━━━━━━━━━━━━━━━╯

👤 <b>{name}</b>
👨 Father: {fname}

📱 <b>Contact Information</b>
├─ Primary: <code>{mobile_formatted}</code>
└─ Alternate: <code>{alt_formatted}</code>

🌐 <b>Network Details</b>
├─ Circle: {circle}
└─ ID: <code>{uid}</code>

📍 <b>Address</b>
{address_formatted}

━━━━━━━━━━━━━━━━━━━━━
<i>Provided by {DEVELOPER}</i>
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
        bot.reply_to(message, "⛔️ <b>Access Denied</b>\n\nAdmin privileges required.", parse_mode='HTML')
        return
    
    bot.send_message(
        message.chat.id,
        "╭━━━━━━━━━━━━━━━━━━━━━╮\n│  ⚙️ <b>Admin Dashboard</b>   │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\nSelect an option:",
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
                "╭━━━━━━━━━━━━━━━━━━━━━╮\n│   🔍 <b>Number Search</b>    │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n<b>Enter 10-digit mobile number</b>\n\n💡 Example: <code>9876543210</code>\n\n━━━━━━━━━━━━━━━━━━━━━\n<i>No +91 prefix needed</i>",
                chat_id, msg_id,
                parse_mode='HTML'
            )
        
        elif call.data == "admin_panel" and is_admin(user_id):
            bot.edit_message_text(
                "╭━━━━━━━━━━━━━━━━━━━━━╮\n│  ⚙️ <b>Admin Dashboard</b>   │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\nSelect an option:",
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
            # Show calculating message
            bot.answer_callback_query(call.id, "🏓 Calculating real ping...", show_alert=False)
            
            # Calculate real ping
            ping = calculate_ping()
            
            # Show real ping
            bot.answer_callback_query(
                call.id, 
                f"🏓 Pong!\n\nAPI Response Time: {ping}ms", 
                show_alert=True
            )
        
        elif call.data == "admin_history" and is_admin(user_id):
            bot.edit_message_text(
                get_search_history(),
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
        elif call.data == "admin_users" and is_admin(user_id):
            bot.edit_message_text(
                get_user_activity(),
                chat_id, msg_id,
                parse_mode='HTML',
                reply_markup=create_admin_keyboard()
            )
        
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
        print(f"❌ Callback error: {e}")
        try:
            bot.answer_callback_query(call.id)
        except:
            pass

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "User"
    stats['total_users'].add(user_id)
    
    text = clean_number(message.text)
    is_waiting = message.chat.id in user_states
    is_valid_number = text.isdigit() and len(text) == 10
    
    if is_waiting or is_valid_number:
        if not text.isdigit() or len(text) != 10:
            bot.reply_to(
                message, 
                "╭━━━━━━━━━━━━━━━━━━━━━╮\n│  ❌ <b>Invalid Number</b>    │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n<b>Send a valid 10-digit number</b>\n\n💡 Example: <code>9876543210</code>", 
                parse_mode='HTML'
            )
            return
        
        # Log search attempt
        searching_msg = bot.send_message(
            message.chat.id, 
            "╭━━━━━━━━━━━━━━━━━━━━━╮\n│  🔍 <b>Searching...</b>      │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n<i>Fetching information...</i>", 
            parse_mode='HTML'
        )
        
        # Fetch data
        data = fetch_mobile_info(text)
        
        # Determine status
        if data:
            if data.get('blacklisted'):
                status = 'blacklist'
            else:
                status = 'success'
        else:
            status = 'failed'
        
        # Log the search
        log_search(user_id, user_name, text, status)
        
        # Delete searching message
        try:
            bot.delete_message(message.chat.id, searching_msg.message_id)
        except:
            pass
        
        # Send results
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
                f"╭━━━━━━━━━━━━━━━━━━━━━╮\n│ ⚠️ <b>Service Error</b>      │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n<b>Unable to fetch data</b>\n\nPlease try again later.\n\n━━━━━━━━━━━━━━━━━━━━━\n<i>Contact: {DEVELOPER}</i>",
                parse_mode='HTML',
                reply_markup=create_result_keyboard()
            )
        
        user_states.pop(message.chat.id, None)
    
    else:
        is_admin_user = is_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "╭━━━━━━━━━━━━━━━━━━━━━╮\n│   💡 <b>Quick Tip</b>        │\n╰━━━━━━━━━━━━━━━━━━━━━╯\n\n<b>Send a 10-digit number</b>\nto search for information\n\n━━━━━━━━━━━━━━━━━━━━━\n<i>or use the button below</i>",
            parse_mode='HTML',
            reply_markup=create_main_keyboard(is_admin_user)
        )

# ==================== Flask ====================
@app.route('/', methods=['GET'])
def index():
    return {
        'status': 'running',
        'bot': 'Mobile Info Lookup Advanced',
        'version': '4.0',
        'developer': DEVELOPER,
        'features': {
            'search_tracking': True,
            'user_analytics': True,
            'real_ping': True
        },
        'stats': {
            'uptime': get_uptime(),
            'total_requests': stats['total_requests'],
            'total_users': len(stats['total_users']),
            'searches_tracked': len(search_history)
        }
    }

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'healthy', 'uptime': get_uptime()}

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
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("""
╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
│  Mobile Info Bot v4.0 Advanced   │
│  Developer: @aadi_io              │
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯
    """)
    
    print(f"\n🔒 Blacklist: {len(BLACKLIST)} numbers protected")
    print(f"📊 Search tracking: Enabled")
    print(f"👥 User analytics: Enabled")
    print(f"🏓 Real ping: Enabled\n")
    
    if set_webhook():
        print(f"✅ Admin ID: {ADMIN_ID}")
        port = int(os.environ.get('PORT', 10000))
        print(f"✅ Port: {port}")
        print("✅ Status: Ready to serve\n")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("❌ Failed to start webhook")
