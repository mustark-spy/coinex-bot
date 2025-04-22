import os
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

from telegram_bot import send_telegram_message
from bot_status import set_bot_status
from coinex_api import CoinExAPI
from indicators import prepare_dataframe, calculate_rsi, calculate_ema, calculate_atr
from datetime import datetime

coinex = CoinExAPI()

# /start
def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="🤖 Bot de trading actif.\nUtilisez /pause, /resume ou /signal.")

# /pause
def pause(update: Update, context: CallbackContext):
    set_bot_status("paused")
    context.bot.send_message(chat_id=update.effective_chat.id, text="⏸️ Bot mis en pause.")

# /resume
def resume(update: Update, context: CallbackContext):
    set_bot_status("running")
    context.bot.send_message(chat_id=update.effective_chat.id, text="▶️ Bot relancé.")

# /signal + boutons
def signal(update: Update, context: CallbackContext):
    msg = get_signal_message()
    keyboard = [
        [
            InlineKeyboardButton("📈 Entrer en LONG", callback_data='manual_long'),
            InlineKeyboardButton("📉 Entrer en SHORT", callback_data='manual_short')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, reply_markup=reply_markup)

def handle_pnl(update: Update, context: CallbackContext):
    summary = coinex.get_pnl_summary("BTCUSDT")
    context.bot.send_message(chat_id=update.effective_chat.id, text=summary)

# Donne le signal actuel avec tendance et interprétation
def get_signal_message():
    symbol = os.getenv("TRADE_SYMBOL")
    rsi_period = int(os.getenv("RSI_PERIOD"))
    ema_fast = int(os.getenv("EMA_FAST"))
    ema_slow = int(os.getenv("EMA_SLOW"))
    period = os.getenv("TIMEFRAME")
    rsi_overbought = float(os.getenv("RSI_OVERBOUGHT", 70))
    rsi_oversold = float(os.getenv("RSI_OVERSOLD", 30))

    coinex = CoinExAPI()
    candles = coinex.get_ohlcv(symbol, period=period, limit=300)
    if not candles:
        return "Erreur : impossible de récupérer les données."

    df = prepare_dataframe(candles)
    df["EMA_fast"] = calculate_ema(df, ema_fast)
    df["EMA_slow"] = calculate_ema(df, ema_slow)
    df["EMA_200"] = calculate_ema(df, 200)
    df["RSI"] = calculate_rsi(df, rsi_period)
    latest = df.iloc[-1]

    trend = "HAUSSIÈRE" if latest["EMA_fast"] > latest["EMA_slow"] else "BAISSIÈRE" if latest["EMA_fast"] < latest["EMA_slow"] else "NEUTRE"

    rsi_value = latest["RSI"]
    signal = ""
    if rsi_value < rsi_oversold and trend == "HAUSSIÈRE":
        signal = "Signal possible : LONG"
    elif rsi_value > rsi_overbought and trend == "BAISSIÈRE":
        signal = "Signal possible : SHORT"
    else:
        signal = "Pas de signal immédiat."

    return f"""[Signal manuel]
{symbol} ({period})
RSI({rsi_period}) : {rsi_value:.2f}
EMA{ema_fast} : {latest['EMA_fast']:.2f}
EMA{ema_slow} : {latest['EMA_slow']:.2f}
EMA200 : {latest['EMA_200']:.2f}
Tendance : {trend}
{signal}
"""

# Callback des boutons LONG/SHORT
def handle_manual_order(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    action = query.data  # 'manual_long' ou 'manual_short'
    side = 1 if action == 'manual_long' else 2
    coinex = CoinExAPI()
    symbol = os.getenv("TRADE_SYMBOL")
    period = os.getenv("TIMEFRAME")
    amount_usdt = float(os.getenv("TRADE_AMOUNT_USDT"))
    rsi_period = int(os.getenv("RSI_PERIOD"))
    ema_fast = int(os.getenv("EMA_FAST"))
    ema_slow = int(os.getenv("EMA_SLOW"))
    tp_atr_mult = float(os.getenv("TP_ATR_MULTIPLIER"))
    sl_atr_mult = float(os.getenv("SL_ATR_MULTIPLIER"))

    candles = coinex.get_ohlcv(symbol, period=period, limit=300)
    df = prepare_dataframe(candles)
    df["EMA_fast"] = calculate_ema(df, ema_fast)
    df["EMA_slow"] = calculate_ema(df, ema_slow)
    df["EMA_200"] = calculate_ema(df, 200)
    df["RSI"] = calculate_rsi(df, rsi_period)
    df["ATR"] = calculate_atr(df)
    latest = df.iloc[-1]

    price = coinex.get_last_price(symbol)
    if not price:
        query.edit_message_text("Erreur lors de la récupération du prix.")
        return

    qty = round(amount_usdt / price, 4)
    atr = latest["ATR"]
    entry = latest["close"]

    tp_pct = (atr / entry) * tp_atr_mult * 100
    sl_pct = (atr / entry) * sl_atr_mult * 100

    result = coinex.place_order(symbol, side=side, amount=qty)
    print("[DEBUG ORDER RESULT]", result)  # DEBUG

    if result and result.get("code") == 0:
        position = coinex.get_pending_position(symbol)
        print("[DEBUG POSITION STRUCTURE]", position)
        print("[DEBUG POSITION KEYS]", position.keys())
        if position:
            coinex.set_tp_sl(
                symbol,
                position["position_id"],
                float(position["avg_entry_price"]),
                tp_pct,
                sl_pct,
                side=side
            )
            pnl_estime = abs(tp_pct / 100 * float(position["avg_entry_price"])) * qty
            message = f"""✅ Ordre MANUEL {'LONG' if side == 1 else 'SHORT'} exécuté
Prix entrée : {position['avg_entry_price']}
Quantité : {qty}
TP/SL : {round(tp_pct,2)}% / {round(sl_pct,2)}%
PnL estimé si TP : {round(pnl_estime,2)} USDT"""
            context.bot.send_message(chat_id=query.message.chat_id, text=message)
        else:
            query.edit_message_text("❌ Position non retrouvée après ordre.")
    else:
        query.edit_message_text("❌ Erreur lors de l’exécution de l’ordre.")


# /transfer <montant>
def handle_transfer(update: Update, context: CallbackContext):
    try:
        if len(context.args) != 1:
            update.message.reply_text("Utilisation : /transfer <montant>")
            return
        amount = float(context.args[0])
        result = coinex.transfer_asset("USDT", amount, from_account="FUTURES", to_account="SPOT")
        if result and result.get("code") == 0:
            update.message.reply_text(f"✅ Transfert manuel de {amount} USDT effectué de FUTURES vers SPOT.")
        else:
            update.message.reply_text(f"❌ Erreur de transfert : {result}")
    except Exception as e:
        update.message.reply_text(f"❌ Erreur : {e}")


# Lancer le listener dans un thread
def run_telegram_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("pause", pause))
    dispatcher.add_handler(CommandHandler("resume", resume))
    dispatcher.add_handler(CommandHandler("signal", signal))
    dispatcher.add_handler(CallbackQueryHandler(handle_manual_order))
    dispatcher.add_handler(CommandHandler("pnl", handle_pnl))
    dispatcher.add_handler(CommandHandler("transfer", handle_transfer))


    updater.start_polling()

def start_telegram_listener():
    thread = threading.Thread(target=run_telegram_bot)
    thread.daemon = True
    thread.start()
