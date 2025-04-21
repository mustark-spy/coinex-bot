import os
import time
import threading
from dotenv import load_dotenv
from datetime import datetime
from coinex_api import CoinExAPI
from telegram_bot import send_telegram_message
from indicators import prepare_dataframe, calculate_ema, calculate_rsi, calculate_atr
from logger_csv import log_trade, format_timestamp
from bot_status import get_bot_status
from telegram_listener import start_telegram_listener

load_dotenv()

symbol = os.getenv("TRADE_SYMBOL")
amount_usdt = float(os.getenv("TRADE_AMOUNT_USDT"))
rsi_period = int(os.getenv("RSI_PERIOD"))
ema_fast = int(os.getenv("EMA_FAST"))
ema_slow = int(os.getenv("EMA_SLOW"))
period = os.getenv("TIMEFRAME")
tp_atr_mult = float(os.getenv("TP_ATR_MULTIPLIER"))
sl_atr_mult = float(os.getenv("SL_ATR_MULTIPLIER"))
allowed_hours = list(map(int, os.getenv("ALLOWED_HOURS", "").split(",")))
rsi_overbought = float(os.getenv("RSI_OVERBOUGHT", 70))
rsi_oversold = float(os.getenv("RSI_OVERSOLD", 30))

coinex = CoinExAPI()

def profit_lock_loop():
    if os.getenv("ENABLE_PROFIT_LOCK", "false").lower() != "true":
        return
    threshold = float(os.getenv("PROFIT_LOCK_THRESHOLD_PERCENT", "1.5"))
    interval = int(os.getenv("PROFIT_LOCK_INTERVAL_MINUTES", "60")) * 60
    base_balance = None

    while True:
        try:
            balance = coinex.get_balance()
            if balance and "data" in balance:
                usdt_info = next((item for item in balance["data"] if item["coin"] == "USDT"), None)
                usdt = float(usdt_info["available"]) if usdt_info else 0.0
                if base_balance is None:
                    base_balance = usdt
                profit = usdt - base_balance
                profit_pct = (profit / base_balance) * 100 if base_balance > 0 else 0
                if profit_pct >= threshold and profit > 0:
                    result = coinex.transfer_asset("USDT", profit, from_account="FUTURES", to_account="SPOT")
                    if result and result.get("code") == 0:
                        send_telegram_message(f"🔒 Profit Lock : Transféré {round(profit,2)} USDT de FUTURES vers SPOT ✅")
                        base_balance = usdt - profit
                    else:
                        send_telegram_message(f"⚠️ Erreur transfert Profit Lock : {result}")
        except Exception as e:
            print(f"[Erreur Profit Lock] {e}")
        time.sleep(interval)

def run_bot():
    if get_bot_status() == "paused":
        print("Bot en pause.")
        return

    current_hour = datetime.utcnow().hour
    if current_hour not in allowed_hours:
        print(f"Bot désactivé à {current_hour}h UTC (filtre horaire).")
        return

    try:
        candles = coinex.get_ohlcv(symbol, period=period, limit=300)
        if not candles:
            send_telegram_message("Erreur : impossible de récupérer les bougies.")
            return

        df = prepare_dataframe(candles)
        df["EMA_fast"] = calculate_ema(df, ema_fast)
        df["EMA_slow"] = calculate_ema(df, ema_slow)
        df["EMA_200"] = calculate_ema(df, 200)
        df["RSI"] = calculate_rsi(df, rsi_period)
        df["ATR"] = calculate_atr(df)
        latest = df.iloc[-1]

        message = f"""📊 Analyse {symbol} ({period})
Prix : {latest['close']:.2f}
RSI({rsi_period}) : {latest['RSI']:.2f}
EMA{ema_fast} : {latest['EMA_fast']:.2f}
EMA{ema_slow} : {latest['EMA_slow']:.2f}
EMA200 : {latest['EMA_200']:.2f}
"""

        side = None
        reason = ""
        if latest["RSI"] < rsi_oversold and latest["EMA_fast"] > latest["EMA_slow"] and latest["close"] > latest["EMA_200"]:
            side = 1
            reason = f"RSI ({latest['RSI']:.2f}) < {rsi_oversold} + EMA{ema_fast} > EMA{ema_slow} + Prix > EMA200"
        elif latest["RSI"] > rsi_overbought and latest["EMA_fast"] < latest["EMA_slow"] and latest["close"] < latest["EMA_200"]:
            side = 2
            reason = f"RSI ({latest['RSI']:.2f}) > {rsi_overbought} + EMA{ema_fast} < EMA{ema_slow} + Prix < EMA200"

        if side:
            direction = "📈 LONG" if side == 1 else "📉 SHORT"
            message += f"\n✅ Signal détecté : {direction}\n📌 Critères validés :\n{reason}"

            price = coinex.get_last_price(symbol)
            qty = round(amount_usdt / price, 4)
            atr = latest["ATR"]
            entry = latest["close"]
            tp_pct = (atr / entry) * tp_atr_mult * 100
            sl_pct = (atr / entry) * sl_atr_mult * 100

            result = coinex.place_order(symbol, side=side, amount=qty)
            if result:
                position = coinex.get_pending_position(symbol)
                if position:
                    coinex.set_tp_sl(symbol, position["position_id"], float(position["avg_entry_price"]), tp_pct, sl_pct, side)
                    pnl_estime = abs(tp_pct / 100 * float(position["avg_entry_price"])) * qty
                    message += f"\n🎯 TP/SL appliqués.\n💰 PnL estimé : {round(pnl_estime,2)} USDT"
                    log_trade({
                        "timestamp": format_timestamp(),
                        "symbol": symbol,
                        "signal": "LONG" if side == 1 else "SHORT",
                        "price": round(price, 2),
                        "quantity": qty,
                        "TP (%)": round(tp_pct, 2),
                        "SL (%)": round(sl_pct, 2),
                        "status": "executé",
                        "PnL estimé": round(pnl_estime, 2)
                    })
                else:
                    message += "\n⚠️ Erreur : position introuvable après exécution."
            else:
                message += "\n❌ Erreur lors de l’exécution de l’ordre."
        else:
            message += f"\n⏳ Aucun signal - conditions non remplies (RSI actuel : {latest['RSI']:.2f})"

        send_telegram_message(message)

    except Exception as e:
        send_telegram_message(f"Erreur du bot : {e}")

if __name__ == "__main__":
    start_telegram_listener()
    threading.Thread(target=profit_lock_loop, daemon=True).start()
    while True:
        run_bot()
        time.sleep(900)  # 15 minutes
