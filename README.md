# 🎭 Anonymous Bot v3.0

A Telegram bot that allows users to send anonymous messages in group chats.

## ✨ Features

- **Direct Mode**: Type `@anon Your message` to send anonymously
- **Delayed Mode**: Type `@anon` then send any media (stickers, voice, etc.)
- **Full Media Support**: Photos, videos, GIFs, documents, audio, voice, video notes, stickers
- **Reply Preservation**: Maintains reply chains for context
- **Auto-cleanup**: Failed requests timeout after 60 seconds
- **Docker Ready**: Production-ready containerization

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)

### Setup BotFather

```
/setprivacy → Disable
/setjoingroups → Enable
```

### Installation

1. **Clone and setup**
```bash
git clone <repo>
cd anonymous_bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure**
```bash
cp .env.example .env
# Edit .env and add your BOT_TOKEN
```

3. **Run**
```bash
python -m bot.main
```

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📖 Usage

### Mode 1: Direct Anonymization

```
@anon Hello everyone!
```
→ Message deleted, bot sends "Hello everyone!"

```
@anon Check this out! [photo]
```
→ Photo with caption sent anonymously

### Mode 2: Delayed (for stickers/voice)

```
Step 1: @anon
        [message deleted, bot waits 60s]

Step 2: [send sticker/voice/video_note]
        [bot sends it anonymously]
```

## 🔧 Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `BOT_TOKEN` | - | Telegram Bot API token (required) |
| `COMMAND_PREFIX` | `@anon` | Trigger phrase |
| `QUEUE_TIMEOUT` | `60` | Seconds to wait for follow-up |
| `ERROR_NOTIFICATIONS` | `true` | Show errors in chat |

## 📋 Bot Permissions Required

- ✅ Delete messages
- ✅ Send messages
- ✅ Send media
- ✅ Send stickers & GIFs

## ⚠️ Limitations

- ❌ Polls (API limitation)
- ❌ Contacts (requires phone number)
- ❌ Location (can be added if needed)
- ❌ Messages older than 48h cannot be deleted

## 📜 License

MIT License - feel free to modify and distribute.

---

Made with ❤️ and Python
```

---

## 🏃 Quick Start Commands

```bash
# Create project structure
mkdir -p anonymous_bot/bot/{handlers,services,utils}

# Create all files (copy content above)

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "BOT_TOKEN=your_token_here" > .env

# Run the bot
python -m bot.main