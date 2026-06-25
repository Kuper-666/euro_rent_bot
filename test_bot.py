import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

def test_environment_variables():
    telegram_token = os.getenv('TELEGRAM_TOKEN')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    print(f"Telegram Token: {telegram_token[:10]}...")
    print(f"OpenAI API Key: {openai_api_key[:10]}...")
    
    return bool(telegram_token and openai_api_key)

if __name__ == "__main__":
    if test_environment_variables():
        print("Environment variables are set correctly!")
    else:
        print("Warning: Some environment variables are missing.")