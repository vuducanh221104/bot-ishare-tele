"""
File cấu hình cho bot Telegram
"""
import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# Bot Token từ BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Channel username (ví dụ: @channelname) hoặc Channel ID (số âm)
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@channelname")
# Nếu dùng Channel ID, đảm bảo CHANNEL_USERNAME là số (ví dụ: "-1001234567890")

# Bot name (tùy chọn)
BOT_NAME = os.getenv("BOT_NAME", "iShare")

# Claim link (link để nhận gift sau khi join channel) - Deprecated, dùng links.json
CLAIM_LINK = os.getenv("CLAIM_LINK", "")

# Admin ID (có thể nhiều admin, cách nhau bằng dấu phẩy)
ADMIN_IDS = [int(admin_id.strip()) for admin_id in os.getenv("ADMIN_IDS", "").split(",") if admin_id.strip().isdigit()]
