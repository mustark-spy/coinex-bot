import pandas as pd

def prepare_dataframe(ohlcv):
    df = pd.DataFrame(ohlcv, columns=[
        "timestamp", "open", "high", "low", "close", "volume", "amount"
    ])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df["open"] = df["open"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["close"] = df["close"].astype(float)
    df["volume"] = df["volume"].astype(float)
    df["amount"] = df["amount"].astype(float)
    return df

def calculate_ema(df, period, column="close"):
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_rsi(df, period=14, column="close"):
    delta = df[column].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(df, period=14):
    df["H-L"] = df["high"] - df["low"]
    df["H-C"] = abs(df["high"] - df["close"].shift())
    df["L-C"] = abs(df["low"] - df["close"].shift())
    tr = df[["H-L", "H-C", "L-C"]].max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr
