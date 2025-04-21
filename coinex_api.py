import requests
import time
import hashlib
import hmac
import os
from dotenv import load_dotenv
from urllib.parse import urlencode

load_dotenv()

class CoinExAPI:
    def __init__(self):
        self.base_url = "https://api.coinex.com"
        self.api_key = os.getenv("COINEX_API_KEY")
        self.api_secret = os.getenv("COINEX_API_SECRET")

    def _generate_signature(self, method, path_with_query, body, timestamp):
        prepared_str = method.upper() + path_with_query
        if body:
            prepared_str += body
        prepared_str += timestamp

        signature = hmac.new(
            bytes(self.api_secret, 'latin-1'),
            msg=bytes(prepared_str, 'latin-1'),
            digestmod=hashlib.sha256
        ).hexdigest().lower()
        return signature

    def _signed_headers(self, method, path, params=None, body_dict=None):
        timestamp = str(int(time.time() * 1000))
        query_string = ""
        body_str = ""

        if params:
            query_string = "?" + "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        path_with_query = path + query_string

        if body_dict:
            import json
            body_str = json.dumps(body_dict, separators=(',', ':'))

        signature = self._generate_signature(method, path_with_query, body_str, timestamp)

        headers = {
            "X-COINEX-KEY": self.api_key,
            "X-COINEX-SIGN": signature,
            "X-COINEX-TIMESTAMP": timestamp,
            "Content-Type": "application/json"
        }
        return headers, query_string, body_str

    def get_ohlcv(self, symbol, period="15min", limit=300):
        path = "/v2/futures/kline"
        url = self.base_url + path
        params = {
            "market": symbol,
            "period": period,
            "limit": limit
        }
        try:
            headers, query_string, _ = self._signed_headers("GET", path, params)
            response = requests.get(url + query_string, headers=headers)
            response.raise_for_status()
            json_data = response.json()
            if json_data["code"] != 0 or not isinstance(json_data["data"], list):
                print("[Erreur get_ohlcv] Données manquantes ou réponse invalide")
                return []
            return json_data["data"]
        except Exception as e:
            print(f"[Erreur get_ohlcv] Exception : {e}")
            return []

    def get_balance(self):
        path = "/v2/assets/futures/balance"
        url = self.base_url + path
        try:
            headers, query_string, _ = self._signed_headers("GET", path)
            response = requests.get(url + query_string, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Erreur get_balance] {e}")
            return None

    def get_last_price(self, symbol):
        path = "/v2/futures/ticker"
        url = self.base_url + path
        params = {
            "market": symbol
        }
        try:
            headers, query_string, _ = self._signed_headers("GET", path, params)
            response = requests.get(url + query_string, headers=headers)
            response.raise_for_status()
            json_data = response.json()

            if json_data["code"] != 0 or not json_data["data"]:
                print(f"[Erreur get_last_price] Réponse vide ou code d'erreur")
                return None

            return float(json_data["data"][0]["last"])
        except Exception as e:
            print(f"[Erreur get_last_price] {e}")
            return None


    def get_finished_orders(self, market, limit=100):
        path = "/v2/futures/finished-order"
        url = self.base_url + path
        params = {
            "market": market,
            "market_type": "FUTURES",
            "page": 1,
            "limit": limit
        }
        headers, query_string, _ = self._signed_headers("GET", path, params=params)
        try:
            response = requests.get(url + query_string, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Erreur get_finished_orders] {e}")
            return None

    def get_closed_positions(self, market, limit=100):
        path = "/v2/futures/finished-position"
        url = self.base_url + path
        params = {
            "market": market,
            "market_type": "FUTURES",
            "page": 1,
            "limit": limit
        }
        headers, query_string, _ = self._signed_headers("GET", path, params=params)
        try:
            response = requests.get(url + query_string, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Erreur get_closed_positions] {e}")
            return None

    def get_pending_position(self, market: str):
        path = "/v2/futures/pending-position"
        params = {
            "market": market,
            "market_type": "FUTURES"
        }
        headers, query_string, _ = self._signed_headers("GET", path, params=params)
        url = self.base_url + path + query_string
        try:
            response = requests.get(url, headers=headers)
            response_json = response.json()
            if response and response_json.get("code") == 0:
                data = response_json.get("data", [])
                if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    return data[0]  # ✅ retourne la position (dictionnaire)
                else:
                    return None
            else:
                print("[Erreur get_pending_position]", response_json)
                return None
        except Exception as e:
            print(f"[Erreur get_pending_position] Exception : {e}")
            return None


    def get_pnl_summary(self, market="BTCUSDT"):
        response = self.get_closed_positions(market)
        if not response or response.get("code") != 0:
            return "Erreur lors de la récupération des positions clôturées."

        data = response.get("data", [])
        total_pnl = 0
        total_trades = 0
        wins = 0
        losses = 0
        last_trade = None

        for position in data:
            print("[DEBUG CLOSED POSITION]", position)
            pnl = float(position.get("realized_pnl", 0))
            total_pnl += pnl
            total_trades += 1
            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 1
            if last_trade is None:
                last_trade = position

        win_rate = (wins / total_trades) * 100 if total_trades else 0

        message = f"📊 Résumé PnL\n\n"
        message += f"Nombre de trades : {total_trades}\n"
        message += f"Total Profit : {round(total_pnl, 2)} USDT\n"
        message += f"Win Rate : {round(win_rate, 2)} %\n"
        if last_trade:
            message += f"Dernier trade : {last_trade['side'].upper()} {last_trade['market']} | PnL : {last_trade.get('realized_pnl', '?')} USDT"
        return message
        
    def transfer_asset(self, coin, amount, from_account="FUTURES", to_account="SPOT"):
        path = "/v2/assets/transfer"
        url = self.base_url + path
        body = {
            "coin": coin,
            "amount": str(round(amount, 6)),
            "from_account_type": from_account,
            "to_account_type": to_account
        }
        headers, _, body_str = self._signed_headers("POST", path, body_dict=body)
        try:
            response = requests.post(url, headers=headers, data=body_str)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[Erreur transfert automatique] {e}")
            return None

    def place_order(self, market, side, amount, leverage=1, client_id=None):
        path = "/v2/futures/order"
        url = self.base_url + path
        body = {
            "market": market,
            "market_type": "FUTURES",
            "side": "buy" if side == 1 else "sell",
            "type": "market",
            "amount": str(amount),
            "leverage": leverage,
            "client_id": client_id or f"manual_{int(time.time())}",
            "is_hide": False
        }
        headers, _, body_str = self._signed_headers("POST", path, body_dict=body)
        try:
            response = requests.post(url, headers=headers, data=body_str)
            print("[DEBUG ORDER BODY]", body)
            print("[DEBUG BODY STR]", body_str)
            print("[DEBUG RESPONSE STATUS]", response.status_code)
            print("[DEBUG RESPONSE TEXT]", response.text)
            return response.json()
        except Exception as e:
            print(f"[Erreur place_order] {e}")
            return None

    def calculate_safe_stop_loss(position: dict, atr: float, current_price: float, multiplier: float = 1.0):
        """
        Calcule un SL cohérent avec la position et évite les erreurs de placement.
        """
        avg_entry_price = float(position["avg_entry_price"])
        side = position["side"].lower()  # 'long' ou 'short'

        # Calcul théorique du SL
        if side == "long":
            sl_price = avg_entry_price - (atr * multiplier)
            # Mais il ne doit jamais être > au prix actuel
            sl_price = min(sl_price, current_price - (atr * 0.2))
        elif side == "short":
            sl_price = avg_entry_price + (atr * multiplier)
            # Mais il ne doit jamais être < au prix actuel
            sl_price = max(sl_price, current_price + (atr * 0.2))
        else:
            raise ValueError(f"[Erreur SL] Position inconnue: {side}")

        return round(sl_price, 4)

    def set_tp_sl(self, market, position_id, entry_price, tp_pct, sl_pct, side):
        current_price = self.get_last_price(market)
        if current_price is None:
            print("[Erreur set_tp_sl] Impossible de récupérer le prix actuel")
            return

        tp_price = entry_price * (1 - tp_pct / 100) if side == 2 else entry_price * (1 + tp_pct / 100)
        sl_price = entry_price * (1 + sl_pct / 100) if side == 2 else entry_price * (1 - sl_pct / 100)

        # Vérification du SL par rapport au prix actuel
        if side == 1 and sl_price > current_price:
            print(f"[WARNING] SL ({sl_price:.2f}) > current price ({current_price:.2f}) en position LONG — ajustement")
            sl_price = current_price * 0.995  # petite marge de sécurité
        elif side == 2 and sl_price < current_price:
            print(f"[WARNING] SL ({sl_price:.2f}) < current price ({current_price:.2f}) en position SHORT — ajustement")
            sl_price = current_price * 1.005

        tp_body = {
            "market": market,
            "market_type": "FUTURES",
            "position_id": position_id,
            "take_profit_price": f"{tp_price:.4f}",
            "take_profit_type": "mark_price"
        }

        sl_body = {
            "market": market,
            "market_type": "FUTURES",
            "position_id": position_id,
            "stop_loss_price": f"{sl_price:.4f}",
            "stop_loss_type": "mark_price"
        }

        tp_path = "/v2/futures/set-position-take-profit"
        sl_path = "/v2/futures/set-position-stop-loss"
        tp_headers, _, tp_body_str = self._signed_headers("POST", tp_path, body_dict=tp_body)
        sl_headers, _, sl_body_str = self._signed_headers("POST", sl_path, body_dict=sl_body)

        try:
            tp_response = requests.post(self.base_url + tp_path, headers=tp_headers, data=tp_body_str)
            print("[DEBUG TP BODY]", tp_body)
            print("[DEBUG TP RESPONSE]", tp_response.text)
            sl_response = requests.post(self.base_url + sl_path, headers=sl_headers, data=sl_body_str)
            print("[DEBUG SL BODY]", sl_body)
            print("[DEBUG SL RESPONSE]", sl_response.text)
        except Exception as e:
            print(f"[Erreur set_tp_sl] {e}")


