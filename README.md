# 🤖 CoinEx Auto-Trader Bot (Telegram)

Ce bot automatise le trading de contrats FUTURES sur CoinEx, avec une stratégie technique robuste, gestion dynamique du risque, et un pilotage complet via Telegram.

---

## 📈 Stratégie de Trading

Le bot repose sur une combinaison d'indicateurs techniques et de logique conditionnelle, centrée sur :

- **Tendance (EMA200)** : pour filtrer la direction dominante
- **Momentum (EMV, RSI)** : pour détecter les opportunités de retournement ou de continuation
- **Volatilité (ATR)** : pour ajuster les niveaux de Take Profit et Stop Loss

### 🔍 Indicateurs utilisés

| Indicateur       | Description |
|------------------|-------------|
| **EMA (Exponential Moving Average)** | Moyenne mobile exponentielle, sensible aux changements récents de prix. Utilisée pour détecter des croisements de tendance (ex: EMA9/EMA21). |
| **EMA200**       | Indicateur de tendance long terme. Le bot ne prend des LONGs que si le prix est au-dessus de l'EMA200 (et SHORTs en dessous). |
| **RSI (Relative Strength Index)** | Mesure la force d’un mouvement. Seuils classiques : surachat > 70, survente < 30. |
| **EMV (Ease of Movement)** | Détecte les mouvements haussiers ou baissiers sans forte résistance. |
| **ATR (Average True Range)** | Indicateur de volatilité. Sert à calculer dynamiquement les TP/SL selon la volatilité du marché. |

### 🧠 Logique du Bot

- Un signal LONG est généré si :
  - RSI < 45
  - EMA rapide > EMA lente
  - Le prix est au-dessus de l’EMA200 (si filtre actif)

- Un signal SHORT est généré si :
  - RSI > 65
  - EMA rapide < EMA lente
  - Le prix est en-dessous de l’EMA200

- Le bot calcule un **TP et SL dynamiques** selon l’ATR (Take Profit = ATR * TP_MULT, Stop Loss = ATR * SL_MULT)

- Les signaux manuels (`/signal`) bypassent les filtres pour expérimenter librement.

---

## ⚙️ Configuration via `.env`

```env
COINEX_API_KEY=xxx
COINEX_API_SECRET=xxx

TRADE_SYMBOL=BTCUSDT
TRADE_AMOUNT_USDT=100
TP_ATR_MULTIPLIER=1.5
SL_ATR_MULTIPLIER=1.0
USE_EMA200_FILTER=true

ENABLE_PROFIT_LOCK=true
PROFIT_LOCK_THRESHOLD_PERCENT=1.5
PROFIT_LOCK_INTERVAL_MINUTES=60

TELEGRAM_BOT_TOKEN=xxx
TELEGRAM_CHAT_ID=xxx
```

---

## 💬 Commandes Telegram disponibles

| Commande              | Description |
|-----------------------|-------------|
| `/signal`             | Envoie un ordre **manuel** avec TP/SL calculés automatiquement |
| `/pnl`                | Affiche le résumé des trades (PnL cumulé, dernier trade) |
| `/balance`            | Affiche les soldes SPOT / FUTURES / MARGIN |
| `/transfer <montant>`| Transfère manuellement un montant de USDT de FUTURES → SPOT |
| `/set`                | Change une variable à chaud (ex: `/set TP_ATR_MULTIPLIER 2.0`) |
| `/pause` / `/resume`  | Pause ou relance le trading automatique |
| `/stop` / `/restart`  | Arrête ou redémarre entièrement le bot |

---

## 🔒 Fonction de Profit Lock automatique

- Le bot surveille le solde USDT sur le portefeuille **FUTURES**
- Dès qu’un profit dépasse le seuil (`PROFIT_LOCK_THRESHOLD_PERCENT`) :
  - ➜ Le montant est transféré automatiquement vers **SPOT**
  - ➜ Une alerte Telegram est envoyée pour confirmer
- Cette vérification se fait toutes les `PROFIT_LOCK_INTERVAL_MINUTES`

💡 Le but est de **sécuriser les gains** hors du marché actif (FUTURES).

---

## ▶️ Lancer le bot

```bash
pip install -r requirements.txt
python main.py
```

---

## 📌 Conseils

- Le bot ne gère qu’une seule position à la fois.
- Les ordres sont loggés dans un fichier CSV.
- Test recommandé sur environnement limité ou compte secondaire avant usage réel.

---

> Créé pour un usage pro, sécurisé et évolutif. Des modules complémentaires peuvent être ajoutés sur demande (UI, dashboard, reporting, backtest...)

