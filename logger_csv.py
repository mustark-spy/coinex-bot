import csv
import os
from datetime import datetime

CSV_FILE = "journal.csv"

def format_timestamp():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def log_trade(data):
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, mode="a", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            "timestamp", "symbol", "signal", "price", "quantity",
            "TP (%)", "SL (%)", "status", "PnL estimé"
        ])
        if not file_exists:
            writer.writeheader()
        writer.writerow(data)
