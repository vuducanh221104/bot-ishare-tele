"""
Bot Telegram - Check Channel Join
Đã tích hợp check member thực sự từ Telegram API
Phiên bản cải tiến với nhiều tính năng mới
"""
import logging
import time
import json
import os
from datetime import datetime
from functools import wraps
from typing import Tuple, List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from telegram.error import TelegramError, BadRequest, Forbidden
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from config import BOT_TOKEN, CHANNEL_USERNAME, BOT_NAME, CLAIM_LINK, ADMIN_IDS

# Thiết lập logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cache đơn giản để tránh spam API (lưu trong memory)
# Format: {user_id: {"status": "member/left", "timestamp": time}}
_member_cache = {}
CACHE_DURATION = 300  # Cache trong 5 phút

# File lưu trữ claim links
LINKS_FILE = "links.json"
COMMANDS_FILE = "commands.json"
LANG_FILE = "lang.json"
USER_LANG_FILE = "user_lang.json"
PING_FILE = "ping_data.json"
USERS_FILE = "users.json"
DEFAULT_LANG = "vi"

# ==================== LANGUAGE SYSTEM ====================

def load_lang() -> Dict:
    """Load tất cả ngôn ngữ từ lang.json"""
    if os.path.exists(LANG_FILE):
        try:
            with open(LANG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc lang.json: {e}")
    return {}

def load_user_langs() -> Dict[str, str]:
    """Load ngôn ngữ đã chọn của từng user {user_id: lang_code}"""
    if os.path.exists(USER_LANG_FILE):
        try:
            with open(USER_LANG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc user_lang.json: {e}")
    return {}

def save_user_langs(data: Dict[str, str]):
    """Lưu ngôn ngữ user"""
    try:
        with open(USER_LANG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi khi lưu user_lang.json: {e}")

_langs = load_lang()
_user_langs = load_user_langs()

def get_user_lang(user_id: int) -> str:
    """Lấy ngôn ngữ của user"""
    return _user_langs.get(str(user_id), DEFAULT_LANG)

def set_user_lang(user_id: int, lang: str):
    """Đặt ngôn ngữ cho user"""
    _user_langs[str(user_id)] = lang
    save_user_langs(_user_langs)

def t(user_id: int, key: str, **kwargs) -> str:
    """Lấy text theo ngôn ngữ user, hỗ trợ format variables"""
    lang = get_user_lang(user_id)
    text = _langs.get(lang, {}).get(key) or _langs.get(DEFAULT_LANG, {}).get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# ==================== PING SYSTEM ====================

def load_pings() -> Dict:
    """Load ping data từ file JSON"""
    if os.path.exists(PING_FILE):
        try:
            with open(PING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc ping_data.json: {e}")
    return {}

def save_pings(data: Dict):
    """Lưu ping data vào file JSON"""
    try:
        with open(PING_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi khi lưu ping_data.json: {e}")

# ==================== USER TRACKING SYSTEM ====================

def load_users() -> Dict:
    """Load user data từ file JSON"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc users.json: {e}")
    return {}

def save_users(data: Dict):
    """Lưu user data vào file JSON"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Lỗi khi lưu users.json: {e}")

def track_user(user_id: int, username: str = None, first_name: str = None, track_claim: bool = False):
    """Theo dõi người dùng - ghi nhận khi start bot hoặc claim link"""
    users = load_users()
    uid_str = str(user_id)
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
    
    is_new = uid_str not in users
    
    if uid_str not in users:
        users[uid_str] = {
            "first_seen": timestamp,
            "last_active": timestamp,
            "username": username or first_name or "Unknown",
            "total_commands": 0,
            "daily_commands": {},
            "is_member": False,
            "total_claims": 0,
            "claim_dates": []
        }
    else:
        users[uid_str]["last_active"] = timestamp
        if username and username != "Unknown":
            users[uid_str]["username"] = username
    
    # Tăng command count (chỉ khi không phải claim)
    if not track_claim:
        users[uid_str]["total_commands"] = users[uid_str].get("total_commands", 0) + 1
        
        # Tăng daily count
        if today_str not in users[uid_str].get("daily_commands", {}):
            users[uid_str]["daily_commands"] = {today_str: 0}
        users[uid_str]["daily_commands"][today_str] = users[uid_str]["daily_commands"].get(today_str, 0) + 1
    else:
        # Tăng claim count
        users[uid_str]["total_claims"] = users[uid_str].get("total_claims", 0) + 1
        if "claim_dates" not in users[uid_str]:
            users[uid_str]["claim_dates"] = []
        users[uid_str]["claim_dates"].append(timestamp)
    
    save_users(users)
    return is_new

def update_user_membership(user_id: int, is_member: bool):
    """Cập nhật trạng thái channel membership của user"""
    users = load_users()
    uid_str = str(user_id)
    
    if uid_str in users:
        users[uid_str]["is_member"] = is_member
        save_users(users)

# Load user data
_users_data = load_users()

def load_commands() -> Dict:
    """Load commands config từ file JSON"""
    if os.path.exists(COMMANDS_FILE):
        try:
            with open(COMMANDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc commands.json: {e}")
            return {}
    return {}

# Load claim links từ file
def load_links() -> Dict:
    """Load claim links từ file JSON"""
    if os.path.exists(LINKS_FILE):
        try:
            with open(LINKS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Migration: chuyển format cũ {name: url} sang {name: {url, enabled, added_at}}
            migrated = False
            for key, val in data.items():
                if isinstance(val, str):
                    data[key] = {"url": val, "enabled": True, "added_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
                    migrated = True
            if migrated:
                save_links(data)
            return data
        except Exception as e:
            logger.error(f"Lỗi khi đọc links.json: {e}")
            return {}
    return {}

def get_active_links(links: Dict) -> Dict[str, str]:
    """Lấy danh sách links đang bật (enabled), trả về {name: url}"""
    return {name: info["url"] for name, info in links.items() if info.get("enabled", True)}

# Lưu claim links vào file
def save_links(links: Dict):
    """Lưu claim links vào file JSON"""
    try:
        with open(LINKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(links, f, ensure_ascii=False, indent=2)
        logger.info(f"Đã lưu {len(links)} links vào {LINKS_FILE}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu links.json: {e}")

# Khởi tạo links
_claim_links = load_links()
# Nếu có CLAIM_LINK cũ trong .env, thêm vào links
if CLAIM_LINK and "default" not in _claim_links:
    _claim_links["default"] = {"url": CLAIM_LINK, "enabled": True, "added_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
    save_links(_claim_links)


async def is_member_of_channel(user_id: int, bot) -> Tuple[bool, str]:
    """
    Kiểm tra xem user có tham gia channel không
    Returns: (is_member: bool, status: str)
    """
    # Kiểm tra cache trước
    if user_id in _member_cache:
        cached_data = _member_cache[user_id]
        if time.time() - cached_data["timestamp"] < CACHE_DURATION:
            is_member = cached_data["status"] in ["member", "administrator", "creator", "restricted"]
            return is_member, cached_data["status"]
    
    try:
        # Kiểm tra member trong channel
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        status = member.status
        
        # Lưu vào cache
        _member_cache[user_id] = {
            "status": status,
            "timestamp": time.time()
        }
        
        is_member = status in ["member", "administrator", "creator", "restricted"]
        return is_member, status
        
    except BadRequest as e:
        logger.error(f"BadRequest khi kiểm tra channel: {e}")
        if "chat not found" in str(e).lower():
            return False, "chat_not_found"
        return False, "error"
    except Forbidden as e:
        logger.error(f"Forbidden khi kiểm tra channel: {e}")
        return False, "forbidden"
    except TelegramError as e:
        logger.error(f"TelegramError khi kiểm tra channel: {e}")
        return False, "error"
    except Exception as e:
        logger.error(f"Lỗi không xác định khi kiểm tra channel: {e}")
        return False, "error"


def require_admin(func):
    """Decorator để kiểm tra quyền admin"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if user.id not in ADMIN_IDS:
            await update.message.reply_text(t(user.id, "admin_no_access"), parse_mode='HTML')
            return
        
        return await func(update, context)
    
    return wrapper


def require_channel_membership(func):
    """Decorator để bảo vệ các lệnh - yêu cầu tham gia channel"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        uid = user.id
        
        # Kiểm tra tham gia channel
        is_member, status = await is_member_of_channel(uid, context.bot)
        
        if not is_member:
            keyboard = [
                [
                    InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
                ],
                [
                    InlineKeyboardButton(t(uid, "btn_joined_check"), callback_data="check_after_join")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message = t(uid, "require_join_title") + "\n\n" + t(uid, "require_join_msg", channel=CHANNEL_USERNAME)
            
            await update.message.reply_text(
                message, 
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
            return
        
        return await func(update, context)
    
    return wrapper


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
    user = update.effective_user
    uid = user.id
    username = user.username if user.username else None
    first_name = user.first_name
    
    # Theo dõi người dùng khi start bot
    is_new_user = track_user(uid, username, first_name)
    
    # Nếu user chưa chọn ngôn ngữ, hiển thị chọn ngôn ngữ trước
    if str(uid) not in _user_langs:
        keyboard = [
            [
                InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="start_lang_vi"),
                InlineKeyboardButton("🇬🇧 English", callback_data="start_lang_en")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🌐 <b>Chọn ngôn ngữ / Choose language:</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return
    
    # Đã có ngôn ngữ, hiển thị welcome
    await _send_welcome(update.message, uid, user)


async def _send_welcome(message_or_edit, uid: int, user, edit: bool = False):
    """Gửi welcome message (dùng chung cho start và callback)"""
    username = user.username if user.username else user.first_name
    welcome_message = t(uid, "welcome", username=username, bot_name=BOT_NAME, channel=CHANNEL_USERNAME)
    
    keyboard = [
        [
            InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        ],
        [
            InlineKeyboardButton(t(uid, "btn_joined_check"), callback_data="check_membership")
        ],
        [
            InlineKeyboardButton(t(uid, "btn_view_guide"), callback_data="show_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if edit:
        await message_or_edit.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await message_or_edit.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='HTML')


async def check_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /CheckChannel - Kiểm tra tham gia channel thực sự"""
    user = update.effective_user
    uid = user.id
    
    # Xóa cache để force check lại
    if uid in _member_cache:
        del _member_cache[uid]
    
    # Kiểm tra member
    is_member, status = await is_member_of_channel(uid, context.bot)
    
    # Cập nhật trạng thái membership của user
    update_user_membership(uid, is_member)
    
    if status == "chat_not_found":
        keyboard = [[InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "channel_not_found", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')
        return
    
    if status == "forbidden":
        keyboard = [[InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "bot_no_access", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')
        return
    
    if status == "error":
        keyboard = [[
            InlineKeyboardButton(t(uid, "btn_retry"), callback_data="check_membership"),
            InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "error_occurred"), reply_markup=reply_markup, parse_mode='HTML')
        return
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton(t(uid, "btn_recheck"), callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "not_joined", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')
    else:
        keyboard = [
            [InlineKeyboardButton(t(uid, "btn_claim_gift"), callback_data="claim_link")],
            [
                InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
                InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "check_success", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')


@require_channel_membership
async def claimlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /claimlink - Hiển thị link nhận gift"""
    uid = update.effective_user.id
    links = load_links()
    active = get_active_links(links)
    
    if active:
        claim_link = active.get("default") or next(iter(active.values()), "") or CLAIM_LINK
    else:
        claim_link = CLAIM_LINK
    
    if not claim_link:
        await update.message.reply_text(t(uid, "claim_expired"), parse_mode='HTML')
        return
    
    if len(active) > 1:
        keyboard = []
        for link_name, link_url in active.items():
            keyboard.append([InlineKeyboardButton(f"🎁 {link_name}", callback_data=f"claim_{link_name}")])
        keyboard.append([
            InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
            InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = t(uid, "claim_choose")
    else:
        # Lấy link đầu tiên
        first_link_name = next(iter(active.keys()), "")
        first_link_url = next(iter(active.values()), "")
        
        keyboard = [
            [InlineKeyboardButton(t(uid, "btn_claim_now"), callback_data=f"get_link_{first_link_name}")],
            [
                InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
                InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = t(uid, "claim_single")
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


@require_channel_membership
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /help"""
    uid = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
            InlineKeyboardButton(t(uid, "btn_check"), callback_data="check_membership")
        ],
        [InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        t(uid, "help_title", channel=CHANNEL_USERNAME, bot_name=BOT_NAME),
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


# ==================== ADMIN COMMANDS ====================

@require_admin
async def addlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thêm claim link mới - Chỉ admin"""
    uid = update.effective_user.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(t(uid, "addlink_usage"), parse_mode='HTML')
        return
    
    link_name = context.args[0]
    link_url = " ".join(context.args[1:])
    
    if not link_url.startswith(("http://", "https://")):
        await update.message.reply_text(t(uid, "invalid_url"))
        return
    
    links = load_links()
    MAX_LINKS = 5
    if link_name not in links and len(links) >= MAX_LINKS:
        await update.message.reply_text(t(uid, "max_links", max=MAX_LINKS), parse_mode='HTML')
        return
    
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    links[link_name] = {"url": link_url, "enabled": True, "added_at": now}
    save_links(links)
    
    await update.message.reply_text(
        t(uid, "addlink_success", name=link_name, url=link_url, date=now, count=len(links), max=MAX_LINKS),
        parse_mode='HTML'
    )


@require_admin
async def editlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sửa claim link - Chỉ admin"""
    uid = update.effective_user.id
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(t(uid, "editlink_usage"), parse_mode='HTML')
        return
    
    link_name = context.args[0]
    link_url = " ".join(context.args[1:])
    
    if not link_url.startswith(("http://", "https://")):
        await update.message.reply_text(t(uid, "invalid_url"))
        return
    
    links = load_links()
    if link_name not in links:
        await update.message.reply_text(t(uid, "link_not_found", name=link_name), parse_mode='HTML')
        return
    
    old_url = links[link_name]["url"]
    links[link_name]["url"] = link_url
    save_links(links)
    
    await update.message.reply_text(
        t(uid, "editlink_success", name=link_name, old_url=old_url, new_url=link_url),
        parse_mode='HTML'
    )


@require_admin
async def deletelink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa claim link - Chỉ admin"""
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text(t(uid, "deletelink_usage"), parse_mode='HTML')
        return
    
    link_name = context.args[0]
    links = load_links()
    if link_name not in links:
        await update.message.reply_text(t(uid, "link_not_found", name=link_name), parse_mode='HTML')
        return
    
    deleted_info = links.pop(link_name)
    save_links(links)
    
    await update.message.reply_text(
        t(uid, "deletelink_success", name=link_name, url=deleted_info['url'], count=len(links)),
        parse_mode='HTML'
    )


@require_admin
async def listlinks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xem danh sách tất cả claim links - Chỉ admin"""
    uid = update.effective_user.id
    links = load_links()
    
    if not links:
        await update.message.reply_text(t(uid, "listlinks_empty"), parse_mode='HTML')
        return
    
    active_count = sum(1 for info in links.values() if info.get("enabled", True))
    message = t(uid, "listlinks_title")
    for i, (link_name, info) in enumerate(links.items(), 1):
        status = t(uid, "status_on") if info.get("enabled", True) else t(uid, "status_off")
        added_at = info.get("added_at", "N/A")
        message += t(uid, "listlinks_item", i=i, name=link_name, status=status, url=info['url'], date=added_at)
    
    message += t(uid, "listlinks_footer", total=len(links), active=active_count)
    await update.message.reply_text(message, parse_mode='HTML')


@require_admin
async def togglelink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bật/tắt claim link - Chỉ admin"""
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text(t(uid, "togglelink_usage"), parse_mode='HTML')
        return
    
    link_name = context.args[0]
    links = load_links()
    if link_name not in links:
        await update.message.reply_text(t(uid, "link_not_found", name=link_name), parse_mode='HTML')
        return
    
    current = links[link_name].get("enabled", True)
    links[link_name]["enabled"] = not current
    save_links(links)
    
    new_status = t(uid, "status_on") if not current else t(uid, "status_off")
    await update.message.reply_text(
        t(uid, "togglelink_success", name=link_name, url=links[link_name]['url'], status=new_status),
        parse_mode='HTML'
    )


@require_admin
async def stopbot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dừng bot - Chỉ admin"""
    uid = update.effective_user.id
    await update.message.reply_text(t(uid, "stopbot_msg"), parse_mode='HTML')
    logger.info(f"Bot được dừng bởi admin {uid}")
    context.application.stop_running()


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /ping - Ping bot"""
    user = update.effective_user
    uid = user.id
    username = user.username if user.username else user.first_name
    
    now = datetime.now()
    timestamp = now.strftime("%d/%m/%Y %H:%M:%S")
    
    pings = load_pings()
    uid_str = str(uid)
    if uid_str not in pings:
        pings[uid_str] = {"username": username, "records": []}
    pings[uid_str]["username"] = username
    pings[uid_str]["records"].append(timestamp)
    save_pings(pings)
    
    total = len(pings[uid_str]["records"])
    
    # Tính ping hôm nay
    today_str = now.strftime("%d/%m/%Y")
    today_count = sum(1 for r in pings[uid_str]["records"] if r.startswith(today_str))
    
    await update.message.reply_text(
        t(uid, "ping_success", username=username, total=total, today=today_count, time=timestamp),
        parse_mode='HTML'
    )


@require_admin
async def pingstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thống kê ping - Chỉ admin"""
    uid = update.effective_user.id
    pings = load_pings()
    
    if not pings:
        await update.message.reply_text(t(uid, "pingstats_empty"), parse_mode='HTML')
        return
    
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    
    # Tính ngày đầu tuần (thứ 2)
    from datetime import timedelta
    weekday = now.weekday()  # 0=Mon
    week_start = now - timedelta(days=weekday)
    
    total_all = 0
    today_all = 0
    week_all = 0
    user_stats = []
    
    for uid_str, data in pings.items():
        records = data.get("records", [])
        username = data.get("username", uid_str)
        user_total = len(records)
        total_all += user_total
        
        user_today = 0
        user_week = 0
        for r in records:
            try:
                dt = datetime.strptime(r, "%d/%m/%Y %H:%M:%S")
                if r.startswith(today_str):
                    user_today += 1
                if dt >= week_start.replace(hour=0, minute=0, second=0):
                    user_week += 1
            except ValueError:
                pass
        
        today_all += user_today
        week_all += user_week
        user_stats.append((username, user_total, user_today, user_week))
    
    # Sắp xếp theo tổng ping giảm dần
    user_stats.sort(key=lambda x: x[1], reverse=True)
    
    message = t(uid, "pingstats_title", total=total_all, today=today_all, week=week_all)
    
    for i, (username, u_total, u_today, u_week) in enumerate(user_stats, 1):
        message += t(uid, "pingstats_user", i=i, username=username, total=u_total, today=u_today, week=u_week)
    
    await update.message.reply_text(message, parse_mode='HTML')


@require_admin
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thống kê người dùng - Chỉ admin"""
    uid = update.effective_user.id
    users = load_users()
    
    if not users:
        await update.message.reply_text(t(uid, "stats_no_data"), parse_mode='HTML')
        return
    
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    this_month = now.strftime("%m/%Y")  # Tháng này
    
    # Tính ngày đầu tuần (thứ 2)
    from datetime import timedelta
    weekday = now.weekday()  # 0=Mon
    week_start = now - timedelta(days=weekday)
    
    # Tính ngày đầu tháng
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    total_users = len(users)
    new_today = 0
    active_today = 0
    week_users = 0
    member_count = 0
    total_claims = 0
    users_who_claimed = 0
    claims_today = 0
    month_users = 0  # User mới tháng này
    month_claims = 0  # Claims tháng này
    
    user_list = []
    
    for uid_str, data in users.items():
        # Đếm thành viên đã join channel
        if data.get("is_member", False):
            member_count += 1
        
        # Đếm claims
        user_claims = data.get("total_claims", 0)
        if user_claims > 0:
            users_who_claimed += 1
            total_claims += user_claims
            
            # Đếm claims hôm nay
            claim_dates = data.get("claim_dates", [])
            for cd in claim_dates:
                if cd.startswith(today_str):
                    claims_today += 1
                # Đếm claims tháng này
                if cd[3:10] == this_month:
                    month_claims += 1
        
        # Đếm user mới hôm nay (first_seen)
        first_seen = data.get("first_seen", "")
        if first_seen.startswith(today_str):
            new_today += 1
        
        # Đếm user mới tháng này
        if first_seen and first_seen[3:10] == this_month:
            month_users += 1
        
        # Đếm user hoạt động hôm nay (có command)
        daily_commands = data.get("daily_commands", {})
        if today_str in daily_commands:
            active_today += 1
        
        # Đếm user hoạt động tuần này
        last_active = data.get("last_active", "")
        try:
            if last_active:
                dt = datetime.strptime(last_active, "%d/%m/%Y %H:%M:%S")
                if dt >= week_start.replace(hour=0, minute=0, second=0):
                    week_users += 1
        except ValueError:
            pass
        
        # Thu thập thông tin user cho danh sách
        username = data.get("username", uid_str)
        last_active = data.get("last_active", "N/A")
        user_list.append({
            "username": username,
            "last_active": last_active,
            "total": data.get("total_commands", 0)
        })
    
    # Sắp xếp theo last_active giảm dần (mới nhất trước)
    user_list.sort(key=lambda x: x["last_active"], reverse=True)
    
    # Tạo message
    message = t(uid, "stats_title", total=total_users, today=active_today, week=week_users)
    message += t(uid, "stats_new_users", new_today=new_today)
    message += t(uid, "stats_active", active_today=active_today)
    message += t(uid, "stats_member", member_count=member_count)
    message += t(uid, "stats_month", month_users=month_users, month_claims=month_claims)
    message += t(uid, "stats_claims", total_claims=total_claims, users_claimed=users_who_claimed, claims_today=claims_today)
    
    # Thêm danh sách 10 user mới nhất
    message += t(uid, "stats_user_list")
    for i, u in enumerate(user_list[:10], 1):
        message += f"{i}. @{u['username']} - {u['last_active']} ({u['total']} cmds)\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


@require_admin
async def weekstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thống kê theo tuần - Chỉ admin"""
    uid = update.effective_user.id
    users = load_users()
    
    if not users:
        await update.message.reply_text(t(uid, "stats_no_data"), parse_mode='HTML')
        return
    
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    
    from datetime import timedelta
    weekday = now.weekday()  # 0=Mon
    week_start = now - timedelta(days=weekday)
    
    # Tuần trước
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(seconds=1)
    
    total_users = len(users)
    new_this_week = 0
    active_this_week = 0
    claims_this_week = 0
    member_count = 0
    
    user_list = []
    
    for uid_str, data in users.items():
        # Đếm thành viên đã join channel
        if data.get("is_member", False):
            member_count += 1
        
        # Đếm user mới tuần này
        first_seen = data.get("first_seen", "")
        try:
            if first_seen:
                dt = datetime.strptime(first_seen, "%d/%m/%Y %H:%M:%S")
                if dt >= week_start.replace(hour=0, minute=0, second=0):
                    new_this_week += 1
        except ValueError:
            pass
        
        # Đếm user hoạt động tuần này
        last_active = data.get("last_active", "")
        try:
            if last_active:
                dt = datetime.strptime(last_active, "%d/%m/%Y %H:%M:%S")
                if dt >= week_start.replace(hour=0, minute=0, second=0):
                    active_this_week += 1
                    user_list.append({
                        "username": data.get("username", uid_str),
                        "last_active": last_active,
                        "total": data.get("total_commands", 0)
                    })
        except ValueError:
            pass
        
        # Đếm claims tuần này
        claim_dates = data.get("claim_dates", [])
        for cd in claim_dates:
            try:
                dt = datetime.strptime(cd, "%d/%m/%Y %H:%M:%S")
                if dt >= week_start.replace(hour=0, minute=0, second=0):
                    claims_this_week += 1
            except ValueError:
                pass
    
    # Sắp xếp theo last_active giảm dần
    user_list.sort(key=lambda x: x["last_active"], reverse=True)
    
    message = t(uid, "weekstats_title", total=total_users, active=active_this_week)
    message += t(uid, "weekstats_new", new_week=new_this_week)
    message += t(uid, "weekstats_claims", claims_week=claims_this_week)
    message += t(uid, "stats_member", member_count=member_count)
    message += t(uid, "stats_user_list")
    for i, u in enumerate(user_list[:15], 1):
        message += f"{i}. @{u['username']} - {u['last_active']} ({u['total']} cmds)\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


@require_admin
async def monthstats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Thống kê theo tháng - Chỉ admin"""
    uid = update.effective_user.id
    users = load_users()
    
    if not users:
        await update.message.reply_text(t(uid, "stats_no_data"), parse_mode='HTML')
        return
    
    now = datetime.now()
    today_str = now.strftime("%d/%m/%Y")
    this_month = now.strftime("%m/%Y")
    
    from datetime import timedelta
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    total_users = len(users)
    new_this_month = 0
    active_this_month = 0
    claims_this_month = 0
    member_count = 0
    
    user_list = []
    
    for uid_str, data in users.items():
        # Đếm thành viên đã join channel
        if data.get("is_member", False):
            member_count += 1
        
        # Đếm user mới tháng này
        first_seen = data.get("first_seen", "")
        if first_seen and first_seen[3:10] == this_month:
            new_this_month += 1
        
        # Đếm user hoạt động tháng này
        last_active = data.get("last_active", "")
        try:
            if last_active:
                dt = datetime.strptime(last_active, "%d/%m/%Y %H:%M:%S")
                if dt >= month_start:
                    active_this_month += 1
                    user_list.append({
                        "username": data.get("username", uid_str),
                        "last_active": last_active,
                        "total": data.get("total_commands", 0)
                    })
        except ValueError:
            pass
        
        # Đếm claims tháng này
        claim_dates = data.get("claim_dates", [])
        for cd in claim_dates:
            if cd[3:10] == this_month:
                claims_this_month += 1
    
    # Sắp xếp theo last_active giảm dần
    user_list.sort(key=lambda x: x["last_active"], reverse=True)
    
    message = t(uid, "monthstats_title", total=total_users, active=active_this_month)
    message += t(uid, "monthstats_new", new_month=new_this_month)
    message += t(uid, "monthstats_claims", claims_month=claims_this_month)
    message += t(uid, "stats_member", member_count=member_count)
    message += t(uid, "stats_user_list")
    for i, u in enumerate(user_list[:15], 1):
        message += f"{i}. @{u['username']} - {u['last_active']} ({u['total']} cmds)\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chọn ngôn ngữ / Choose language"""
    uid = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
            InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = t(uid, "lang_choose") + "\n\n" + t(uid, "lang_current")
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý callback từ inline buttons"""
    query = update.callback_query
    user = query.from_user
    uid = user.id
    
    if query.data == "check_membership" or query.data == "check_after_join":
        await query.answer(t(uid, "checking"), show_alert=False)
        
        if uid in _member_cache:
            del _member_cache[uid]
        
        is_member, status = await is_member_of_channel(uid, context.bot)
        
        # Cập nhật trạng thái membership của user
        update_user_membership(uid, is_member)
        
        if is_member:
            keyboard = [
                [InlineKeyboardButton(t(uid, "btn_claim_gift"), callback_data="claim_link")],
                [
                    InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
                    InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(t(uid, "confirm_success", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')
        else:
            keyboard = [
                [InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
                [InlineKeyboardButton(t(uid, "btn_recheck"), callback_data="check_membership")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(t(uid, "not_joined_yet", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')
    
    elif query.data == "claim_link" or query.data.startswith("claim_"):
        links = load_links()
        active = get_active_links(links)
        
        if query.data == "claim_link":
            if active:
                claim_link = active.get("default") or next(iter(active.values()), "") or CLAIM_LINK
                link_name = "default" if "default" in active else next(iter(active.keys()), "")
            else:
                claim_link = CLAIM_LINK
                link_name = ""
        else:
            link_name = query.data.replace("claim_", "")
            claim_link = active.get(link_name)
        
        if not claim_link:
            await query.answer(t(uid, "claim_not_configured"), show_alert=True)
            return
        
        await query.answer(t(uid, "claim_loading"), show_alert=False)
        
        keyboard = [
            [InlineKeyboardButton(t(uid, "btn_claim_now"), callback_data=f"get_link_{link_name}")],
            [
                InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
                InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(t(uid, "claim_success"), reply_markup=reply_markup, parse_mode='HTML')
    
    elif query.data.startswith("get_link_"):
        link_name = query.data.replace("get_link_", "")
        links = load_links()
        
        if link_name and link_name in links:
            claim_link = links[link_name].get("url", "")
        else:
            # Nếu không có link_name hoặc không tìm thấy, lấy link đầu tiên
            active = get_active_links(links)
            claim_link = active.get("default") or next(iter(active.values()), "") or CLAIM_LINK
        
        if not claim_link:
            await query.answer(t(uid, "claim_not_configured"), show_alert=True)
            return
        
        # Theo dõi claim link
        track_user(uid, track_claim=True)
        
        await query.answer(t(uid, "claim_loading"), show_alert=False)
        
        # Gửi link như một tin nhắn chat thay vì mở URL
        link_message = t(uid, "link_format", link=claim_link)
        await query.message.reply_text(link_message, parse_mode='HTML')
        
        # Cập nhật tin nhắn trước đó
        keyboard = [
            [InlineKeyboardButton(t(uid, "btn_claim_now"), callback_data=f"get_link_{link_name}")],
            [
                InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
                InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(t(uid, "claim_sent"), reply_markup=reply_markup, parse_mode='HTML')
    
    elif query.data == "show_help":
        await query.answer(t(uid, "loading"), show_alert=False)
        
        keyboard = [
            [
                InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}"),
                InlineKeyboardButton(t(uid, "btn_check"), callback_data="check_membership")
            ],
            [InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            t(uid, "help_title", channel=CHANNEL_USERNAME, bot_name=BOT_NAME),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    elif query.data == "back_to_start":
        await query.answer(t(uid, "going_home"), show_alert=False)
        await _send_welcome(query, uid, user, edit=True)
    
    elif query.data.startswith("start_lang_"):
        lang_code = query.data.replace("start_lang_", "")
        if lang_code in _langs:
            set_user_lang(uid, lang_code)
            await query.answer("✅", show_alert=False)
            # Sau khi chọn ngôn ngữ, hiển thị welcome
            await _send_welcome(query, uid, user, edit=True)
        else:
            await query.answer("❌", show_alert=True)
    
    elif query.data.startswith("lang_"):
        lang_code = query.data.replace("lang_", "")
        if lang_code in _langs:
            set_user_lang(uid, lang_code)
            await query.answer("✅", show_alert=False)
            await query.edit_message_text(t(uid, "lang_changed"), parse_mode='HTML')
        else:
            await query.answer("❌", show_alert=True)


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý các lệnh không xác định"""
    user = update.effective_user
    uid = user.id
    
    is_member, _ = await is_member_of_channel(uid, context.bot)
    
    if not is_member:
        keyboard = [
            [InlineKeyboardButton(t(uid, "btn_join_channel"), url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton(t(uid, "btn_check_join"), callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "unknown_not_joined", channel=CHANNEL_USERNAME), reply_markup=reply_markup, parse_mode='HTML')
    else:
        keyboard = [[
            InlineKeyboardButton(t(uid, "btn_view_cmds"), callback_data="show_help"),
            InlineKeyboardButton(t(uid, "btn_home"), callback_data="back_to_start")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(t(uid, "unknown_joined"), reply_markup=reply_markup, parse_mode='HTML')


async def setup_bot_commands(application: Application):
    """Thiết lập menu commands theo role từ commands.json"""
    cmds = load_commands()
    
    # User commands (default - tất cả user thấy)
    user_cmds = [BotCommand(c["command"], c["description"]) for c in cmds.get("user", [])]
    if user_cmds:
        await application.bot.set_my_commands(user_cmds, scope=BotCommandScopeDefault())
    
    # Admin commands (chỉ admin thấy)
    admin_cmds = [BotCommand(c["command"], c["description"]) for c in cmds.get("admin", [])]
    if admin_cmds:
        for admin_id in ADMIN_IDS:
            try:
                await application.bot.set_my_commands(admin_cmds, scope=BotCommandScopeChat(chat_id=admin_id))
            except Exception as e:
                logger.warning(f"Không thể set commands cho admin {admin_id}: {e}")
    
    logger.info(f"✅ Đã thiết lập menu: {len(user_cmds)} user cmds, {len(admin_cmds)} admin cmds")


def main():
    """Hàm chính để chạy bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN không được tìm thấy! Vui lòng kiểm tra file .env")
        return
    
    if not CHANNEL_USERNAME:
        logger.error("CHANNEL_USERNAME không được tìm thấy! Vui lòng kiểm tra file .env")
        return
    
    # Tạo application với post_init callback để thiết lập commands
    async def post_init(app: Application):
        await setup_bot_commands(app)
    
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Đăng ký các command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("CheckChannel", check_channel_command))
    application.add_handler(CommandHandler("checkchannel", check_channel_command))  # Case insensitive
    application.add_handler(CommandHandler("claimlink", claimlink_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("ping", ping_command))
    
    # Đăng ký admin command handlers
    application.add_handler(CommandHandler("addlink", addlink_command))
    application.add_handler(CommandHandler("editlink", editlink_command))
    application.add_handler(CommandHandler("deletelink", deletelink_command))
    application.add_handler(CommandHandler("listlinks", listlinks_command))
    application.add_handler(CommandHandler("togglelink", togglelink_command))
    application.add_handler(CommandHandler("stopbot", stopbot_command))
    application.add_handler(CommandHandler("pingstats", pingstats_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("weekstats", weekstats_command))
    application.add_handler(CommandHandler("monthstats", monthstats_command))
    
    # Đăng ký callback handler cho inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Đăng ký handler cho các lệnh không xác định
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    
    # Bắt đầu bot
    logger.info("Bot đang khởi động...")
    logger.info(f"Channel: {CHANNEL_USERNAME}")
    logger.info(f"Bot name: {BOT_NAME}")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
