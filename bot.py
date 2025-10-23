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
BLACKLIST = [
    '9161636853',
    '9451180555',
    '6306791897'
]

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
def get_from_cache(key: str) -> Optional[dict]:
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        del cache[key]
    return None

def save_to_cache(key: str, data: dict):
    cache[key] = (data, time.time())

def clean_number(number: str) -> str:
    """Clean and normalize phone number"""
    cleaned = ''.join(filter(str.isdigit, number))
    if cleaned.startswith('91') and len(cleaned) > 10:
        cleaned = cleaned[2:]
    if cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    if len(cleaned) > 10:
        cleaned = cleaned[-10:]
    return cleaned

def format_phone(phone: str) -> str:
    """Format: +91 98765 43210"""
    if not phone:
        return "Not Available"
    cleaned = clean_number(phone)
    if len(cleaned) == 10:
        return f"+91 {cleaned[:5]} {cleaned[5:]}"
    return phone

def format_address(address: str) -> str:
    """Clean address formatting"""
    if not address or address == "null":
        return "Not Available"
    parts = address.replace("!!", "!").split("!")
    cleaned_parts = []
    for part in parts:
        part = part.strip()
        if part and part != "null" and len(part) > 2:
            cleaned_parts.append(part)
    if not cleaned_parts:
        return "Not Available"
    return "\n".join(cleaned_parts[:4])

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def is_blacklisted(number: str) -> bool:
    """Check if number is blacklisted"""
    cleaned = clean_number(number)
    is_blocked = cleaned in BLACKLIST
    if is_blocked:
        stats['blacklist_hits'] += 1
        print(f"🚫 Blacklist hit: {cleaned}")
    return is_blocked

def get_uptime() -> str:
    uptime = time.time() - stats['start_time']
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

# ==================== Premium Keyboards ====================
def create_main_keyboard(is_admin_user=False):
    """Premium main menu"""
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🔍  Start New Search", callback_data="new_search")
    )
    if is_admin_user:
        markup.add(
            InlineKeyboardButton("⚙️  Admin Dashboard", callback_data="admin_panel")
        )
    markup.add(
        InlineKeyboardButton("💬  Contact Developer", url=f"https://t.me/{DEVELOPER[1:]}")
    )
    return markup

def create_admin_keyboard():
    """Premium admin panel"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
        InlineKeyboardButton("🏓 Test Ping", callback_data="admin_ping")
    )
    markup.add(
        InlineKeyboardButton("💾 System Info", callback_data="admin_system"),
        InlineKeyboardButton("ℹ️ About Bot", callback_data="admin_about")
    )
    markup.add(
        InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")
    )
    return markup

def create_result_keyboard():
    """Premium result actions"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 Search Again", callback_data="new_search"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    )
    return markup

# ==================== API ====================
def fetch_mobile_info(mobile: str) -> Optional[dict]:
    """Fetch with blacklist protection"""
    
    # 🚫 BLACKLIST CHECK
    if is_blacklisted(mobile):
        return {'blacklisted': True}
    
    # Check cache
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
            
    except requests.Timeout:
        print(f"⏱ Timeout: {mobile}")
        stats['failed_searches'] += 1
        return None
    except Exception as e:
        print(f"❌ API Error: {e}")
        stats['failed_searches'] += 1
        return None

# ==================== Premium Messages ====================
def get_welcome_message(user_name: str, is_admin_user: bool) -> str:
    """Premium welcome screen"""
    admin_badge = "\n\n┌─────────────────┐\n│  🔐 ADMIN MODE  │\n└─────────────────┘" if is_admin_user else ""
    
    return f"""
╔══════════════════════════╗
║  📱 MOBILE INFO LOOKUP   ║
╚══════════════════════════╝

👋 <b>Welcome back, {user_name}!</b>

🎯 <b>What We Offer:</b>
   • Lightning-fast searches
   • Accurate information
   • Clean interface
   • Secure & private

💡 <b>How to Use:</b>
   Send any 10-digit number or
   click the button below to start!{admin_badge}

━━━━━━━━━━━━━━━━━━━━━━━
<i>Powered by {DEVELOPER}</i>
"""

def get_blacklist_message(number: str) -> str:
    """Custom blacklist response with personality"""
    return f"""
╔══════════════════════════╗
║    🚫 ACCESS DENIED      ║
╚══════════════════════════╝

<b>Number:</b> <code>{format_phone(number)}</code>

<b>⛔️ This number is protected</b>

<b>BKL MERA INFO NIKAL RHA HAI</b> 🤡

━━━━━━━━━━━━━━━━━━━━━━━
<i>Nice try buddy! • {DEVELOPER}</i>
"""

def get_admin_stats() -> str:
    """Premium stats display"""
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_searches'] / stats['total_requests']) * 100
    
    return f"""
╔══════════════════════════╗
║   📊 BOT STATISTICS      ║
╚══════════════════════════╝

📈 <b>Performance Metrics</b>
━━━━━━━━━━━━━━━━━━━━━━━
├ Total Requests: <code>{stats['total_requests']}</code>
├ Successful: <code>{stats['successful_searches']}</code>
├ Failed: <code>{stats['failed_searches']}</code>
├ Success Rate: <code>{success_rate:.1f}%</code>
└ Blacklist Hits: <code>{stats['blacklist_hits']}</code>

👥 <b>User Analytics</b>
━━━━━━━━━━━━━━━━━━━━━━━
├ Total Users: <code>{len(stats['total_users'])}</code>
└ Active Cache: <code>{len(cache)} items</code>

🔒 <b>Security</b>
━━━━━━━━━━━━━━━━━━━━━━━
└ Protected Numbers: <code>{len(BLACKLIST)}</code>

⏱ <b>System Uptime</b>
━━━━━━━━━━━━━━━━━━━━━━━
├ Running: <code>{get_uptime()}</code>
└ Since: <code>{datetime.fromtimestamp(stats['start_time']).strftime('%d %b %Y, %H:%M')}</code>

━━━━━━━━━━━━━━━━━━━━━━━
<i>Admin Panel • {DEVELOPER}</i>
"""

def get_admin_about() -> str:
    """Premium about section"""
    return f"""
╔══════════════════════════╗
║   ℹ️ ABOUT THIS BOT      ║
╚══════════════════════════╝

<b>📱 Bot Information</b>
━━━━━━━━━━━━━━━━━━━━━━━
├ Name: Mobile Info Lookup
├ Version: 3.0 Premium
├ Developer: {DEVELOPER}
└ Mode: Webhook (Production)

<b>✨ Key Features</b>
━━━━━━━━━━━━━━━━━━━━━━━
├ ⚡️ Lightning Fast Search
├ 🎨 Premium UI/UX Design
├ 🔒 Blacklist Protection
├ 💾 Smart Caching System
├ 📊 Real-time Statistics
├ 🛡 Enhanced Security
└ 🎯 Admin Dashboard

<b>🔧 Technology Stack</b>
━━━━━━━━━━━━━━━━━━━━━━━
├ Python 3.13
├ pyTelegramBotAPI
├ Flask + Gunicorn
├ psutil Monitoring
└ REST API Integration

━━━━━━━━━━━━━━━━━━━━━━━
<i>Built with ❤️ by {DEVELOPER}</i>
"""

def get_system_info() -> str:
    """Premium system info"""
    try:
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        cpu_bar = "█" * int(cpu/10) + "░" * (10 - int(cpu/10))
        mem_bar = "█" * int(mem/10) + "░" * (10 - int(mem/10))
        disk_bar = "█" * int(disk/10) + "░" * (10 - int(disk/10))
        
        return f"""
╔══════════════════════════╗
║   💾 SYSTEM RESOURCES    ║
╚══════════════════════════╝

<b>⚙️ CPU Usage</b>
{cpu_bar} <code>{cpu:.1f}%</code>

<b>🧠 Memory Usage</b>
{mem_bar} <code>{mem:.1f}%</code>

<b>💿 Disk Usage</b>
{disk_bar} <code>{disk:.1f}%</code>

━━━━━━━━━━━━━━━━━━━━━━━

<b>⏱ System Uptime</b>
<code>{get_uptime()}</code>

<b>🔒 Security Status</b>
<code>{len(BLACKLIST)} numbers protected</code>

<b>🌐 Server Status</b>
✅ All systems operational

━━━━━━━━━━━━━━━━━━━━━━━
<i>System Monitor • {DEVELOPER}</i>
"""
    except:
        return """
╔══════════════════════════╗
║   💾 SYSTEM RESOURCES    ║
╚══════════════════════════╝

<b>⚠️ Monitoring Unavailable</b>

System information could not be
retrieved at this time.

━━━━━━━━━━━━━━━━━━━━━━━
<i>System Monitor • {DEVELOPER}</i>
"""

def format_result_message(data: dict, searched_number: str) -> list:
    """Premium result formatting"""
    
    # 🚫 Blacklist check
    if data.get('blacklisted'):
        return [get_blacklist_message(searched_number)]
    
    # Validate data
    if not data or not isinstance(data, dict):
        return [f"""
╔══════════════════════════╗
║   ❌ NO RESULTS FOUND    ║
╚══════════════════════════╝

<b>Searched Number:</b>
<code>{format_phone(searched_number)}</code>

No information available for
this mobile number.

💡 <b>Suggestion:</b>
Please verify the number and
try again.

━━━━━━━━━━━━━━━━━━━━━━━
<i>{DEVELOPER}</i>
"""]
    
    data_array = data.get('data', [])
    
    if not data_array or not isinstance(data_array, list) or len(data_array) == 0:
        return [f"""
╔══════════════════════════╗
║   ❌ NO RESULTS FOUND    ║
╚══════════════════════════╝

<b>Searched Number:</b>
<code>{format_phone(searched_number)}</code>

No information available for
this mobile number.

━━━━━━━━━━━━━━━━━━━━━━━
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
╔══════════════════════════╗
║   ❌ NO RESULTS FOUND    ║
╚══════════════════════════╝

<b>Searched Number:</b>
<code>{format_phone(searched_number)}</code>

No information available.

━━━━━━━━━━━━━━━━━━━━━━━
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
        
        result_num = f" {i}" if len(unique_records) > 1 else ""
        
        message = f"""
╔══════════════════════════╗
║  ✅ SEARCH RESULT{result_num}      ║
╚══════════════════════════╝

<b>👤 Personal Information</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Name:</b> {name}
<b>Father:</b> {fname}

<b>📱 Contact Details</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Primary:</b> <code>{mobile_formatted}</code>
<b>Alternate:</b> <code>{alt_formatted}</code>

<b>🌐 Network Information</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Circle:</b> {circle}
<b>User ID:</b> <code>{uid}</code>

<b>📍 Address Details</b>
━━━━━━━━━━━━━━━━━━━━━━━
{address_formatted}

━━━━━━━━━━━━━━━━━━━━━━━
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
        bot.reply_to(message, "⛔️ <b>ACCESS DENIED</b>\n\nYou don't have admin privileges.", parse_mode='HTML')
        return
    
    bot.send_message(
        message.chat.id,
        "╔══════════════════════════╗\n║   ⚙️ ADMIN DASHBOARD     ║\n╚══════════════════════════╝\n\n<b>Select an option below:</b>",
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
                "╔══════════════════════════╗\n║   🔍 NUMBER SEARCH       ║\n╚══════════════════════════╝\n\n<b>Enter 10-digit mobile number</b>\n\n💡 Example: <code>9876543210</code>\n\n<i>No +91 prefix needed</i>",
                chat_id, msg_id,
                parse_mode='HTML'
            )
        
        elif call.data == "admin_panel" and is_admin(user_id):
            bot.edit_message_text(
                "╔══════════════════════════╗\n║   ⚙️ ADMIN DASHBOARD     ║\n╚══════════════════════════╝\n\n<b>Select an option below:</b>",
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
            bot.answer_callback_query(call.id, f"🏓 Pong! Response time: {ping}ms", show_alert=True)
        
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
    stats['total_users'].add(message.from_user.id)
    
    text = clean_number(message.text)
    is_waiting = message.chat.id in user_states
    is_valid_number = text.isdigit() and len(text) == 10
    
    if is_waiting or is_valid_number:
        if not text.isdigit() or len(text) != 10:
            bot.reply_to(
                message, 
                "╔══════════════════════════╗\n║   ❌ INVALID NUMBER      ║\n╚══════════════════════════╝\n\n<b>Please send a valid 10-digit number</b>\n\n💡 Example: <code>9876543210</code>", 
                parse_mode='HTML'
            )
            return
        
        searching_msg = bot.send_message(
            message.chat.id, 
            "╔══════════════════════════╗\n║   🔍 SEARCHING...        ║\n╚══════════════════════════╝\n\n<i>Please wait, fetching data...</i>", 
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
                f"╔══════════════════════════╗\n║  ⚠️ SERVICE UNAVAILABLE  ║\n╚══════════════════════════╝\n\n<b>Unable to fetch information</b>\n\nPlease try again later.\n\n━━━━━━━━━━━━━━━━━━━━━━━\n<i>Contact: {DEVELOPER}</i>",
                parse_mode='HTML',
                reply_markup=create_result_keyboard()
            )
        
        user_states.pop(message.chat.id, None)
    
    else:
        is_admin_user = is_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "╔══════════════════════════╗\n║   💬 QUICK TIP           ║\n╚══════════════════════════╝\n\n<b>Send a 10-digit mobile number</b>\nto search for information\n\n<i>or use the button below</i>",
            parse_mode='HTML',
            reply_markup=create_main_keyboard(is_admin_user)
        )

# ==================== Flask ====================
@app.route('/', methods=['GET'])
def index():
    return {
        'status': 'running',
        'bot': 'Mobile Info Bot Premium',
        'version': '3.0',
        'developer': DEVELOPER,
        'blacklist_protection': len(BLACKLIST),
        'uptime': get_uptime(),
        'total_requests': stats['total_requests'],
        'blacklist_hits': stats['blacklist_hits']
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
        print(f"❌ Webhook error: {e}")
        return False

if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════╗
║  📱 Mobile Info Bot v3.0 Premium      ║
║  🎨 Ultra Modern UI                   ║
║  🔒 Enhanced Security                 ║
║  Developer: @aadi_io                  ║
╚═══════════════════════════════════════╝
    """)
    
    print(f"\n🔒 Blacklist Protection Active:")
    for num in BLACKLIST:
        print(f"   🚫 {format_phone(num)}")
    
    if set_webhook():
        print(f"\n✅ Admin: {ADMIN_ID}")
        print(f"✅ Blacklist: {len(BLACKLIST)} numbers protected")
        port = int(os.environ.get('PORT', 10000))
        print(f"✅ Server Port: {port}")
        print(f"✅ Status: Ready to serve\n")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("\n❌ Failed to initialize webhook")
