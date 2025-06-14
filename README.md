# HowGayBotStats Telegram Bot

Tracks and summarizes gayness stats from @HowGayBot in a Telegram group chat.

## Prep Env
1. Clone the repository:
```bash
conda create -n howgaybotstats python=3.10
conda activate howgaybotstats
pip install -r requirements.txt
```

2. Create a `.env` file in the root directory of the project and add your Telegram bot token:
```
TELEGRAM_BOT_TOKEN='your_telegram_bot_token_here'
```

## Start app
```bash
python main.py
```

## Telebot Token Generation
1. Go to [BotFather](https://t.me/botfather) on Telegram.
2. Start a chat with BotFather and send the command `/newbot`.
3. Give a username and a name for your bot.
4. After creation, BotFather will provide you with a token. Save this token in `.env` file as `TELEGRAM_BOT_TOKEN`.

