import asyncio
import aiohttp
import logging
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

# ==================== Configuration ====================
BOT_TOKEN = "8377073485:AAFtAvmkUVbyE1GhVpgMBBGjK2IVeUsVdCo"
API_URL = "https://demon.taitanx.workers.dev/?mobile={}"
DEVELOPER = "@aadi_io"
CACHE_DURATION = 300  # 5 minutes cache

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Bot Initialization ====================
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==================== States ====================
class SearchStates(StatesGroup):
    waiting_for_number = State()

# ==================== Cache System ====================
class CacheManager:
    def __init__(self):
        self.cache: Dict[str, tuple] = {}
    
    def get(self, key: str) -> Optional[dict]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < CACHE_DURATION:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: dict):
        self.cache[key] = (data, time.time())
    
    def clear_old(self):
        current_time = time.time()
        keys_to_delete = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= CACHE_DURATION
        ]
        for key in keys_to_delete:
            del self.cache[key]

cache = CacheManager()

# ==================== Utility Functions ====================
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

def create_main_keyboard() -> InlineKeyboardMarkup:
    """Create main menu keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔍 New Search", callback_data="new_search"),
            InlineKeyboardButton(text="📖 Help", callback_data="help")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Developer", url=f"https://t.me/{DEVELOPER[1:]}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_back_keyboard() -> InlineKeyboardMarkup:
    """Create back button keyboard"""
    keyboard = [
        [InlineKeyboardButton(text="◀️ Back to Menu", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_search_again_keyboard() -> InlineKeyboardMarkup:
    """Create search again keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Search Again", callback_data="new_search"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ==================== API Functions ====================
async def fetch_mobile_info(mobile: str) -> Optional[dict]:
    """Fetch mobile information from API with caching"""
    
    # Check cache first
    cached_data = cache.get(mobile)
    if cached_data:
        logger.info(f"Cache hit for {mobile}")
        return cached_data
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                API_URL.format(mobile),
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    cache.set(mobile, data)
                    logger.info(f"API call successful for {mobile}")
                    return data
                else:
                    logger.error(f"API returned status {response.status}")
                    return None
    except asyncio.TimeoutError:
        logger.error(f"Timeout for {mobile}")
        return None
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
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

def format_result_message(data: dict, mobile: str) -> str:
    """Format the result message beautifully"""
    if not data.get('data') or len(data['data']) == 0:
        return f"""
<b>❌ No Results Found</b>
━━━━━━━━━━━━━━━━━━━━━

No information available for:
<code>{mobile}</code>

<i>Please verify the number and try again.</i>
"""
    
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

# ==================== Command Handlers ====================
@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    user_name = message.from_user.first_name or "User"
    
    # Send welcome message with typing animation
    await bot.send_chat_action(message.chat.id, "typing")
    await asyncio.sleep(0.5)
    
    await message.answer(
        get_welcome_message(user_name),
        reply_markup=create_main_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    """Handle /help command"""
    await message.answer(
        get_help_message(),
        reply_markup=create_back_keyboard()
    )

@dp.message(Command("search"))
async def search_command(message: Message, state: FSMContext):
    """Handle /search command"""
    await state.set_state(SearchStates.waiting_for_number)
    
    search_prompt = """
<b>🔍 Mobile Number Search</b>
━━━━━━━━━━━━━━━━━━━━━

Please enter a <b>10-digit mobile number</b>:

<i>Example: 8789793154</i>
"""
    
    await message.answer(
        search_prompt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu")]
        ])
    )

# ==================== Callback Handlers ====================
@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Handle main menu callback"""
    await state.clear()
    
    user_name = callback.from_user.first_name or "User"
    
    await callback.message.edit_text(
        get_welcome_message(user_name),
        reply_markup=create_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Handle help callback"""
    await callback.message.edit_text(
        get_help_message(),
        reply_markup=create_back_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "new_search")
async def new_search_callback(callback: CallbackQuery, state: FSMContext):
    """Handle new search callback"""
    await state.set_state(SearchStates.waiting_for_number)
    
    search_prompt = """
<b>🔍 Mobile Number Search</b>
━━━━━━━━━━━━━━━━━━━━━

Please enter a <b>10-digit mobile number</b>:

<i>Example: 8789793154</i>
"""
    
    await callback.message.edit_text(
        search_prompt,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="main_menu")]
        ])
    )
    await callback.answer()

# ==================== Message Handlers ====================
@dp.message(SearchStates.waiting_for_number)
async def process_mobile_number(message: Message, state: FSMContext):
    """Process mobile number input"""
    mobile = message.text.strip().replace(" ", "").replace("-", "").replace("+91", "")
    
    # Validate mobile number
    if not mobile.isdigit():
        error_msg = """
<b>❌ Invalid Input</b>

Please enter only digits.
<i>Example: 8789793154</i>
"""
        await message.answer(error_msg)
        return
    
    if len(mobile) != 10:
        error_msg = """
<b>❌ Invalid Length</b>

Mobile number must be exactly 10 digits.
<i>Example: 8789793154</i>
"""
        await message.answer(error_msg)
        return
    
    # Send searching animation
    searching_msg = await message.answer(
        "<b>🔍 Searching...</b>\n\n<i>Please wait while we fetch the information.</i>"
    )
    
    # Show typing animation
    await bot.send_chat_action(message.chat.id, "typing")
    
    # Fetch data
    data = await fetch_mobile_info(mobile)
    
    if data:
        messages = format_result_message(data, mobile)
        
        if isinstance(messages, list):
            # Delete searching message
            await searching_msg.delete()
            
            # Send each result
            for msg in messages:
                await message.answer(
                    msg,
                    reply_markup=create_search_again_keyboard()
                )
                await asyncio.sleep(0.3)  # Small delay between messages
        else:
            await searching_msg.edit_text(
                messages,
                reply_markup=create_search_again_keyboard()
            )
    else:
        error_msg = """
<b>⚠️ Service Unavailable</b>
━━━━━━━━━━━━━━━━━━━━━

Unable to fetch information at the moment.
Please try again later.

<i>If the problem persists, contact {DEVELOPER}</i>
"""
        await searching_msg.edit_text(
            error_msg.format(DEVELOPER=DEVELOPER),
            reply_markup=create_search_again_keyboard()
        )
    
    await state.clear()

@dp.message()
async def handle_any_message(message: Message, state: FSMContext):
    """Handle any other message"""
    text = message.text.strip().replace(" ", "").replace("-", "").replace("+91", "")
    
    # Check if it might be a mobile number
    if text.isdigit() and len(text) == 10:
        await state.set_state(SearchStates.waiting_for_number)
        await process_mobile_number(message, state)
    else:
        info_msg = """
<b>ℹ️ How can I help you?</b>

• To search, click "🔍 New Search"
• Or send a 10-digit mobile number directly
• For help, click "📖 Help"
"""
        await message.answer(
            info_msg,
            reply_markup=create_main_keyboard()
        )

# ==================== Error Handler ====================
@dp.error()
async def error_handler(event, exception):
    """Handle errors"""
    logger.error(f"Error: {exception}")
    return True

# ==================== Periodic Tasks ====================
async def periodic_cache_cleanup():
    """Periodically clean up old cache entries"""
    while True:
        await asyncio.sleep(600)  # Every 10 minutes
        cache.clear_old()
        logger.info("Cache cleanup completed")

# ==================== Main Function ====================
async def main():
    """Start the bot"""
    logger.info("Starting bot...")
    
    # Start periodic tasks
    asyncio.create_task(periodic_cache_cleanup())
    
    # Start polling
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════╗
    ║   Mobile Info Bot - Professional     ║
    ║   Developer: @aadi_io                ║
    ║   Status: Running...                 ║
    ╚══════════════════════════════════════╝
    """)
    
    asyncio.run(main())
