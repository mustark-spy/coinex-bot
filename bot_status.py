import json
import os

STATUS_FILE = "status.json"

def get_bot_status():
    if not os.path.exists(STATUS_FILE):
        return "running"
    with open(STATUS_FILE, "r") as f:
        data = json.load(f)
        return data.get("status", "running")

def set_bot_status(new_status):
    with open(STATUS_FILE, "w") as f:
        json.dump({"status": new_status}, f)
