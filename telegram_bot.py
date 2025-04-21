import os
import requests

def send_telegram_message(text):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Télégram erreur : {e}")
