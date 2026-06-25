# Euro Rent AI Bot

Telegram bot for analyzing rental listings across Europe using AI.

## Features

- Translate rental listings from any European language
- Identify hidden costs and fees
- Detect potential scams and risks
- Provide country-specific documentation requirements
- Give risk assessment scores (1-10)

## Setup

1. **Get Telegram Bot Token**
   - Go to @BotFather in Telegram
   - Send `/newbot`
   - Follow instructions to create your bot
   - Copy the API token

2. **Get OpenAI API Key**
   - Go to platform.openai.com
   - Create an account
   - Generate an API key

3. **Run the bot**
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

## Deployment

### Render.com (Free)
1. Push code to GitHub
2. Create account on render.com
3. Click "New +" and select "Web Service"
4. Connect your GitHub repository
5. Configure:
   - Name: euro-rent-bot
   - Region: Frankfurt (Germany)
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
6. Add environment variables:
   - TELEGRAM_TOKEN
   - OPENAI_API_KEY
7. Deploy

The bot includes a health check endpoint on port 10000 that responds to GET requests.

### UptimeRobot (Free)
- Keep your Render service awake
- Check interval: 5 minutes
- URL: https://your-bot-name.onrender.com

## Environment Variables

- `TELEGRAM_TOKEN` - Your Telegram bot token
- `OPENAI_API_KEY` - Your OpenAI API key

## Commands

- `/start` - Start the bot
- `/help` - Get usage instructions

## Usage

Simply send any rental listing text to the bot, and it will provide:
1. Clean translation
2. Price breakdown
3. Required documents
4. Hidden risks and recommendations
