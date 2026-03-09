# 🤖 Bot Telegram - Check Channel Join

Bot Telegram đơn giản để yêu cầu người dùng tham gia channel trước khi sử dụng.

## ✨ Tính năng

- 👋 Chào mừng người dùng với thông điệp tùy chỉnh
- ✅ Lệnh `/CheckChannel` để kiểm tra tham gia channel **thực sự**
- 🔒 **Tự động bảo vệ các lệnh** - Yêu cầu tham gia channel trước
- 🔘 **Inline Buttons** - Join channel và kiểm tra dễ dàng
- ⚡ **Cache System** - Tối ưu hiệu suất, giảm API calls
- 🛡️ **Xử lý lỗi thông minh** - Thông báo lỗi cụ thể và hướng dẫn
- 📝 Hỗ trợ các lệnh cơ bản

## 🚀 Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Tạo file `.env`

Sao chép file `.env.example` và đổi tên thành `.env`:

```bash
cp .env.example .env
```

### 3. Cấu hình

Mở file `.env` và điền thông tin:

```env
BOT_TOKEN=your_bot_token_here
CHANNEL_USERNAME=@channelname
BOT_NAME=iShare
CLAIM_LINK=https://example.com/claim
```

**Lấy Bot Token:**
1. Tìm [@BotFather](https://t.me/BotFather) trên Telegram
2. Gửi lệnh `/newbot` và làm theo hướng dẫn
3. Copy token và dán vào file `.env`

**Thêm bot vào channel:**
1. Xem hướng dẫn chi tiết trong file `SETUP_CHANNEL.md`
2. Thêm bot vào channel với quyền **admin** (ít nhất quyền "View messages")
3. Đảm bảo `CHANNEL_USERNAME` trong file `.env` đúng với channel của bạn

## 🎯 Sử dụng

Chạy bot:

```bash
python bot.py
```

### Các lệnh có sẵn

- `/start` - Bắt đầu sử dụng bot
- `/CheckChannel` - Kiểm tra xem đã tham gia channel chưa
- `/help` - Hiển thị trợ giúp

## 📝 Ví dụ sử dụng

```
User: /start
Bot: 👋 Xin chào @username đã đến với bot của iShare
     Vui lòng tham gia Channel để nhận gift
     @channelname
     dùng câu lệnh sau để check xem đã tham gia chưa ? /CheckChannel

User: /CheckChannel
Bot: ✅ bạn đã tham gia thành công vui lòng sử dụng các câu lệnh ví dụ /start

# Hoặc nếu chưa tham gia:
User: /CheckChannel
Bot: ❌ bạn chưa tham gia vui lòng tham gia channel @channelname
```

## 🔧 Cấu trúc dự án

```
bot-checkjoin/
├── bot.py              # File chính chứa logic bot
├── config.py           # File cấu hình
├── requirements.txt    # Dependencies
├── .env.example        # Template file môi trường
├── .gitignore         # Git ignore
├── README.md          # File này
├── SETUP_CHANNEL.md   # Hướng dẫn tích hợp bot vào channel
├── TEST_GUIDE.md      # Hướng dẫn test bot
├── IMPROVEMENTS.md    # Tóm tắt các cải tiến
└── plan/
    └── PLAN.md        # Kế hoạch chi tiết
```

## ⚠️ Lưu ý quan trọng

- **Bot phải là admin của channel** để có thể kiểm tra thành viên
- Xem file `SETUP_CHANNEL.md` để biết cách thêm bot vào channel
- Bot chỉ cần quyền "View messages" là đủ
- Channel phải là public hoặc bot đã được thêm vào channel

## 📌 Tính năng đã hoàn thành

- [x] Tích hợp check member thực sự từ Telegram API
- [x] Xử lý các trường hợp lỗi khi check channel
- [x] Logging để debug
- [x] **Bảo vệ các lệnh khác** (yêu cầu tham gia channel)
- [x] **Inline Buttons** để join channel dễ dàng
- [x] **Cache System** để tối ưu hiệu suất
- [x] **Xử lý lệnh không xác định**

> 📖 Xem chi tiết các cải tiến trong file `IMPROVEMENTS.md`

## 📄 License

MIT
