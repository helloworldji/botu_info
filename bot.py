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

# 🔒 Privacy Protected Numbers - DO NOT SEARCH
PROTECTED_NUMBERS = [
    '9161636853',  # Protected 1
    '9451180555',  # Protected 2
    '6306791897'   # Protected 3
]

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Stats
stats = {
    'total_requests': 0,
    'successful_searches': 0,
    'failed_searches': 0,
    'privacy_blocks': 0,
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
    """Clean and normalize phone number to 10 digits"""
    # Remove all non-digits
    cleaned = ''.join(filter(str.isdigit, number))
    
    # Remove leading 91 if present
    if cleaned.startswith('91') and len(cleaned) > 10:
        cleaned = cleaned[2:]
    
    # Remove leading 0 if present
    if cleaned.startswith('0') and len(cleaned) == 11:
        cleaned = cleaned[1:]
    
    # Take last 10 digits
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
    
    # Split by !! and ! and clean
    parts = address.replace("!!", "!").split("!")
    
    # Clean and filter parts
    cleaned_parts = []
    for part in parts:
        part = part.strip()
        if part and part != "null" and len(part) > 2:
            cleaned_parts.append(part)
    
    if not cleaned_parts:
        return "Not Available"
    
    # Join with proper formatting (max 4 lines)
    return "\n".join(cleaned_parts[:4])

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def is_protected_number(number: str) -> bool:
    """Check if number is privacy protected"""
    cleaned = clean_number(number)
    is_protected = cleaned in PROTECTED_NUMBERS
    
    if is_protected:
        stats['privacy_blocks'] += 1
        print(f"🔒 Privacy block: {cleaned}")
    
    return is_protected

def get_uptime() -> str:
    uptime = time.time() - stats['start_time']
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

# ==================== Keyboards ====================
def create_main_keyboard(is_admin_user=False):
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton("🔍 Start Search", callback_data="new_search"))
    if is_admin_user:
        markup.add(InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel"))
    markup.add(InlineKeyboardButton("💬 Contact Dev", url=f"https://t.me/{DEVELOPER[1:]}"))
    return markup

def create_admin_keyboard():
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
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 New Search", callback_data="new_search"),
        InlineKeyboardButton("🏠 Home", callback_data="main_menu")
    )
    return markup

# ==================== API ====================
def fetch_mobile_info(mobile: str) -> Optional[dict]:
    """Fetch mobile info with privacy protection"""
    
    # 🔒 PRIVACY CHECK FIRST
    if is_protected_number(mobile):
        return {'protected': True}
    
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
                
                # Validate data
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
        print(f"Timeout for: {mobile}")
        stats['failed_searches'] += 1
        return None
    except Exception as e:
        print(f"API Error: {e}")
        stats['failed_searches'] += 1
        return None

# ==================== Messages ====================
def get_welcome_message(user_name: str, is_admin_user: bool) -> str:
    admin_badge = "\n\n🔐 <b>Admin Access Enabled</b>" if is_admin_user else ""
    
    return f"""
<b>Hello {user_name} 👋</b>

<b>Mobile Information Lookup</b>

Fast, accurate mobile number searches with detailed information.{admin_badge}

<i>Developed by {DEVELOPER}</i>
"""

def get_privacy_message(number: str) -> str:
    """Privacy protected number message"""
    return f"""
<b>🔒 Privacy Protected</b>

Number: <code>{format_phone(number)}</code>

Due to privacy reasons, information for this number cannot be displayed.

<i>Respecting user privacy • {DEVELOPER}</i>
"""

def get_admin_stats() -> str:
    success_rate = 0
    if stats['total_requests'] > 0:
        success_rate = (stats['successful_searches'] / stats['total_requests']) * 100
    
    return f"""
<b>📊 Statistics</b>

<b>Requests:</b> {stats['total_requests']}
<b>Success:</b> {stats['successful_searches']} ({success_rate:.1f}%)
<b>Failed:</b> {stats['failed_searches']}
<b>Privacy Blocks:</b> {stats['privacy_blocks']}
<b>Users:</b> {len(stats['total_users'])}
<b>Cache:</b> {len(cache)} items

<b>Protected Numbers:</b> {len(PROTECTED_NUMBERS)}

<b>Uptime:</b> {get_uptime()}
<b>Started:</b> {datetime.fromtimestamp(stats['start_time']).strftime('%d %b %Y, %H:%M')}
"""

def get_admin_about() -> str:
    return f"""
<b>ℹ️ Bot Information</b>

<b>Name:</b> Mobile Info Lookup Bot
<b>Version:</b> 2.7 Professional
<b>Developer:</b> {DEVELOPER}
<b>Mode:</b> Webhook

<b>Features:</b>
• Advanced caching system
• Real-time statistics
• Privacy protection ({len(PROTECTED_NUMBERS)} numbers)
• Admin dashboard
• Clean minimalist UI

<b>Tech Stack:</b>
• Python 3.13
• pyTelegramBotAPI
• Flask Webhook
• psutil monitoring
"""

def get_system_info() -> str:
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
<b>Protected:</b> {len(PROTECTED_NUMBERS)} numbers

<b>Status:</b> ✅ Healthy
"""
    except:
        return "<b>💾 System Resources</b>\n\n<i>Information unavailable</i>"

def format_result_message(data: dict, searched_number: str) -> list:
    """Ultra-clean result formatting with validation"""
    
    # 🔒 Check if privacy protected
    if data.get('protected'):
        return [get_privacy_message(searched_number)]
    
    # Check if data exists
    if not data or not isinstance(data, dict):
        return [f"""
<b>No Results Found</b>

Number: <code>{format_phone(searched_number)}</code>

No information available for this number.

<i>{DEVELOPER}</i>
"""]
    
    # Get data array
    data_array = data.get('data', [])
    
    if not data_array or not isinstance(data_array, list) or len(data_array) == 0:
        return [f"""
<b>No Results Found</b>

Number: <code>{format_phone(searched_number)}</code>

No information available for this number.

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
<b>No Results Found</b>

Number: <code>{format_phone(searched_number)}</code>

No information available for this number.

<i>{DEVELOPER}</i>
"""]
    
    messages = []
    
    for i, record in enumerate(unique_records[:3], 1):  # Max 3 results
        name = record.get('name', 'N/A')
        fname = record.get('fname', 'N/A')
        mobile_num = record.get('mobile', searched_number)
        alt = record.get('alt', '')
        circle = record.get('circle', 'N/A')
        uid = record.get('id', 'N/A')
        address = record.get('address', '')
        
        # Format data
        mobile_formatted = format_phone(mobile_num)
        alt_formatted = format_phone(alt) if alt and alt != 'null' else 'Not Available'
        address_formatted = format_address(address)
        
        # Result header
        result_header = f"<b>Search Result {i}</b>" if len(unique_records) > 1 else "<b>Search Result</b>"
        
        message = f"""
{result_header}

<b>👤 {name}</b>
Father: {fname}

<b>📱 Contact</b>
Primary: <code>{mobile_formatted}</code>
Alternate: <code>{alt_formatted}</code>

<b>🌐 Network</b>
Circle: {circle}
ID: <code>{uid}</code>

<b>📍 Address</b>
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
    
    # Clean the input number
    text = clean_number(message.text)
    
    # Check if waiting for input or direct number
    is_waiting = message.chat.id in user_states
    is_valid_number = text.isdigit() and len(text) == 10
    
    if is_waiting or is_valid_number:
        # Validate number
        if not text.isdigit() or len(text) != 10:
            bot.reply_to(
                message, 
                "❌ <b>Invalid Number</b>\n\nPlease send a valid 10-digit mobile number\n\n<i>Example: 9876543210</i>", 
                parse_mode='HTML'
            )
            return
        
        # Show searching
        searching_msg = bot.send_message(
            message.chat.id, 
            "🔍 <b>Searching...</b>\n\n<i>Please wait</i>", 
            parse_mode='HTML'
        )
        
        # Fetch data
        data = fetch_mobile_info(text)
        
        # Delete searching message
        try:
            bot.delete_message(message.chat.id, searching_msg.message_id)
        except:
            pass
        
        # Format and send results
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
                f"<b>⚠️ Service Unavailable</b>\n\nUnable to fetch information at this time.\n\nPlease try again later.\n\n<i>{DEVELOPER}</i>",
                parse_mode='HTML',
                reply_markup=create_result_keyboard()
            )
        
        # Clear state
        user_states.pop(message.chat.id, None)
    
    else:
        # Unknown input
        is_admin_user = is_admin(message.from_user.id)
        bot.send_message(
            message.chat.id,
            "Send a 10-digit mobile number to search\n\n<i>or use the button below</i>",
            parse_mode='HTML',
            reply_markup=create_main_keyboard(is_admin_user)
        )

# ==================== Flask ====================
@app.route('/', methods=['GET'])
def index():
    return {
        'status': 'running',
        'bot': 'Mobile Info Bot',
        'version': '2.7',
        'developer': DEVELOPER,
        'protected_numbers': len(PROTECTED_NUMBERS),
        'uptime': get_uptime(),
        'requests': stats['total_requests'],
        'privacy_blocks': stats['privacy_blocks']
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
║  Mobile Info Bot v2.7 Professional ║
║  Developer: @aadi_io               ║
╚═══════════════════════════════════╝
    """)
    
    print(f"\n🔒 Privacy Protected Numbers:")
    for num in PROTECTED_NUMBERS:
        print(f"   • {format_phone(num)}")
    
    if set_webhook():
        print(f"\n✅ Admin ID: {ADMIN_ID}")
        print(f"✅ Protected: {len(PROTECTED_NUMBERS)} numbers")
        port = int(os.environ.get('PORT', 10000))
        print(f"✅ Port: {port}\n")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("❌ Failed to start")
