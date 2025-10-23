import telebot
import requests
import json
import time
from typing import Dict, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== Configuration ====================
BOT_TOKEN = "8377073485:AAFtAvmkUVbyE1GhVpgMBBGjK2IVeUsVdCo"
API_URL = "https://demon.taitanx.workers.dev/?mobile={}"
DEVELOPER = "@aadi_io"

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Simple cache
cache: Dict[str, tuple] = {}
CACHE_DURATION = 300  # 5 minutes

# User states storage
user_states = {}

# ==================== Utility Functions ====================
def get_from_cache(key: str) -> Optional[dict]:
    """Get data from cache if not expired"""
    if key in cache:
        data, timestamp = cache[key]
        if time.time() - timestamp < CACHE_DURATION:
            return data
        else:
            del cache[key]
    return None

def save_to_cache(key: str, data: dict):
    """Save data to cache"""
    cache[key] = (data, time.time())

def format_phone(phone: str) -> str:
    """Format phone number for display"""
    if phone and phone.startswith('91'):
        return f"+91 {phone[2:7]} {phone[7:]}"
    return phone

def format_address(address: str) -> str:
    """Format address with proper line breaks"""
    if not address:
        return "Not Available"
    
    parts = address.replace("!!", "!").split("!")
    formatted_parts = []
    
    for part in parts:
        part = part.strip()
        if part and part != "null":
            formatted_parts.append(f"  • {part}")
    
    return "\n".join(formatted_parts) if formatted_parts else "Not Available"

def create_main_keyboard():
    """Create main menu keyboard"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔍 New Search", callback_data="new_search"),
        InlineKeyboardButton("📖 Help", callback_data="help")
    )
    markup.row(
        InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER[1:]}")
    )
    return markup

def create_back_keyboard():
    """Create back button keyboard"""
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu"))
    return markup

def create_search_again_keyboard():
    """Create search again keyboard"""
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🔄 Search Again", callback_data="new_search"),
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    )
    return markup

# ==================== API Function ====================
def fetch_mobile_info(mobile: str) -> Optional[dict]:
    """Fetch mobile information from API"""
    # Check cache first
    cached_data = get_from_cache(mobile)
    if cached_data:
        return cached_data
    
    try:
        response = requests.get(API_URL.format(mobile), timeout=10)
        if response.status_code == 200:
            data = response.json()
            save_to_cache(mobile, data)
            return data
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

# ==================== Message Templates ====================
def get_welcome_message(user_name: str) -> str:
    """Generate welcome message"""
    return f"""
<b>👋 Welcome, {user_name}!</b>

<b>📱 Mobile Information Lookup Bot</b>
━━━━━━━━━━━━━━━━━━━━━

This bot provides detailed information about Indian mobile numbers quickly and efficiently.

<b>✨ Features:</b>
• Fast and accurate results
• Clean, professional interface
• Detailed information display
• Smart caching for speed

<b>🚀 Get started by clicking the button below!</b>

<i>Developed with ❤️ by {DEVELOPER}</i>
"""

def get_help_message() -> str:
    """Generate help message"""
    return f"""
<b>📖 Help & Guide</b>
━━━━━━━━━━━━━━━━━━━━━

<b>How to use this bot:</b>

<b>1️⃣ Quick Search:</b>
   • Click "🔍 New Search"
   • Enter a 10-digit mobile number
   • Get instant results!

<b>2️⃣ Direct Input:</b>
   • Simply send any 10-digit number
   • Bot will automatically search

<b>📋 Information Provided:</b>
   ✓ Owner Name
   ✓ Father's Name
   ✓ Full Address
   ✓ Alternate Numbers
   ✓ Telecom Circle
   ✓ Unique ID

<b>💡 Tips:</b>
• Enter numbers without +91 or 0
• Example: 8789793154

<i>Dev: {DEVELOPER}</i>
"""

def format_result_message(data: dict, mobile: str) -> list:
    """Format the result message"""
    if not data.get('data') or len(data['data']) == 0:
        return [f"""
<b>❌ No Results Found</b>
━━━━━━━━━━━━━━━━━━━━━

No information available for:
<code>{mobile}</code>

<i>Please verify the number and try again.</i>

<i>Dev: {DEVELOPER}</i>
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
    for i, record in enumerate(unique_records, 1):
        name = record.get('name', 'N/A')
        fname = record.get('fname', 'N/A')
        mobile_num = record.get('mobile', 'N/A')
        alt = record.get('alt', '')
        circle = record.get('circle', 'N/A')
        uid = record.get('id', 'N/A')
        address = format_address(record.get('address', ''))
        
        # Format alternate number
        if alt and alt != 'null':
            alt_formatted = format_phone(alt.replace('91', '91'))
        else:
            alt_formatted = 'Not Available'
        
        message = f"""
<b>📱 Search Results #{i}</b>
━━━━━━━━━━━━━━━━━━━━━

<b>👤 Personal Information</b>
<b>Name:</b> {name}
<b>Father:</b> {fname}

<b>📞 Contact Details</b>
<b>Primary:</b> <code>{mobile_num}</code>
<b>Alternate:</b> <code>{alt_formatted}</code>

<b>🌐 Network Information</b>
<b>Circle:</b> {circle}
<b>ID:</b> <code>{uid}</code>

<b>📍 Address</b>
{address}

━━━━━━━━━━━━━━━━━━━━━
<i>Dev: {DEVELOPER}</i>
"""
        messages.append(message)
    
    return messages

# ==================== Handlers ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_name = message.from_user.first_name or "User"
    bot.send_message(
        message.chat.id,
        get_welcome_message(user_name),
        parse_mode='HTML',
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    bot.send_message(
        message.chat.id,
        get_help_message(),
        parse_mode='HTML',
        reply_markup=create_back_keyboard()
    )

@bot.message_handler(commands=['search'])
def search_command(message):
    """Handle /search command"""
    user_states[message.chat.id] = 'waiting_for_number'
    search_prompt = f"""
<b>🔍 Mobile Number Search</b>
━━━━━━━━━━━━━━━━━━━━━

Please enter a <b>10-digit mobile number</b>:

<i>Example: 8789793154</i>

<i>Dev: {DEVELOPER}</i>
"""
    bot.send_message(
        message.chat.id,
        search_prompt,
        parse_mode='HTML'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    """Handle callback queries"""
    try:
        if call.data == "main_menu":
            user_name = call.from_user.first_name or "User"
            bot.edit_message_text(
                get_welcome_message(user_name),
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=create_main_keyboard()
            )
            if call.message.chat.id in user_states:
                del user_states[call.message.chat.id]
        
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
            search_prompt = f"""
<b>🔍 Mobile Number Search</b>
━━━━━━━━━━━━━━━━━━━━━

Please enter a <b>10-digit mobile number</b>:

<i>Example: 8789793154</i>

<i>Dev: {DEVELOPER}</i>
"""
            bot.edit_message_text(
                search_prompt,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML'
            )
        
        bot.answer_callback_query(call.id)
    except Exception as e:
        print(f"Callback error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle all text messages"""
    text = message.text.strip().replace(" ", "").replace("-", "").replace("+91", "")
    
    # Check if user is waiting for number input or if it's a direct number
    if message.chat.id in user_states and user_states[message.chat.id] == 'waiting_for_number' or (text.isdigit() and len(text) == 10):
        
        if not text.isdigit():
            bot.send_message(
                message.chat.id,
                f"<b>❌ Invalid Input</b>\n\nPlease enter only digits.\n<i>Example: 8789793154</i>\n\n<i>Dev: {DEVELOPER}</i>",
                parse_mode='HTML'
            )
            return
        
        if len(text) != 10:
            bot.send_message(
                message.chat.id,
                f"<b>❌ Invalid Length</b>\n\nMobile number must be exactly 10 digits.\n<i>Example: 8789793154</i>\n\n<i>Dev: {DEVELOPER}</i>",
                parse_mode='HTML'
            )
            return
        
        # Send searching message
        searching_msg = bot.send_message(
            message.chat.id,
            "<b>🔍 Searching...</b>\n\n<i>Please wait while we fetch the information.</i>",
            parse_mode='HTML'
        )
        
        # Fetch data
        data = fetch_mobile_info(text)
        
        if data:
            messages = format_result_message(data, text)
            
            # Delete searching message
            try:
                bot.delete_message(message.chat.id, searching_msg.message_id)
            except:
                pass
            
            # Send results
            for msg in messages:
                bot.send_message(
                    message.chat.id,
                    msg,
                    parse_mode='HTML',
                    reply_markup=create_search_again_keyboard()
                )
        else:
            bot.edit_message_text(
                f"<b>⚠️ Service Unavailable</b>\n━━━━━━━━━━━━━━━━━━━━━\n\nUnable to fetch information at the moment.\nPlease try again later.\n\n<i>If the problem persists, contact {DEVELOPER}</i>",
                message.chat.id,
                searching_msg.message_id,
                parse_mode='HTML',
                reply_markup=create_search_again_keyboard()
            )
        
        # Clear user state
        if message.chat.id in user_states:
            del user_states[message.chat.id]
    
    else:
        bot.send_message(
            message.chat.id,
            f"<b>ℹ️ How can I help you?</b>\n\n• To search, click '🔍 New Search'\n• Or send a 10-digit mobile number directly\n• For help, click '📖 Help'\n\n<i>Dev: {DEVELOPER}</i>",
            parse_mode='HTML',
            reply_markup=create_main_keyboard()
        )

# ==================== Main ====================
if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║   Mobile Info Bot - Professional     ║
    ║   Developer: @aadi_io                ║
    ║   Status: Running...                 ║
    ║   Token: 8377073485:AAFt...          ║
    ╚══════════════════════════════════════╝
    """)
    
    try:
        print(f"Bot started successfully! Dev: {DEVELOPER}")
        bot.polling(none_stop=True, interval=0, timeout=20)
    except KeyboardInterrupt:
        print("\n\nBot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        print("Restarting in 5 seconds...")
        time.sleep(5)
