# LANDSHARE Market Maker Bot - Quick Start Guide v2

## 🚀 New Features

### ✅ All Requested Changes Implemented:

1. **User Authentication** - Login with username/password
2. **JSON Config Storage** - Saved credentials, no re-entering
3. **Exchange Management** - Connect, save, and switch between exchanges
4. **Portfolio Display** - View all balances from connected exchange
5. **Gate.io** - Removed password, uses LANDSHARE/USDT
6. **BitMart** - Removed memo, uses only UID
7. **Removed** - BingX and AscendEX
8. **Fixed** - Order placement on CEX now works!

---

## 🔐 Login

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

*(Change these in `auth_config.json` after first login)*

---

## 📝 Step-by-Step Usage

### 1. Start the Application

```bash
streamlit run landshare_ui_v2.py
```

Access at: **http://localhost:8501**

### 2. Login

Enter default credentials to access the dashboard.

### 3. Add an Exchange

**Configuration Tab:**

1. Click **"➕ Add Exchange"**
2. Select exchange: MEXC, Gate.io, or BitMart
3. Enter credentials:

   **MEXC:**
   - API Key
   - API Secret

   **Gate.io:**
   - API Key
   - API Secret
   *(No password needed, uses LANDSHARE/USDT pair)*

   **BitMart:**
   - API Key
   - API Secret
   - UID
   *(No memo needed)*

4. Click **"Connect & Save"**
5. System will test connection and fetch portfolio
6. If successful, credentials are saved to `cex_credentials.json`

### 4. View Portfolio

**Portfolio Tab:**

1. Select your exchange from dropdown
2. Click **"🔄 Refresh Portfolio"**
3. View all balances:
   - Free (available)
   - Used (in orders)
   - Total

### 5. Configure Trading

**Configuration Tab:**

1. **Reference Mode:**
   - DEX: PancakeSwap price, immediate rebalance
   - CEX: Exchange mid-price, 2-minute delay

2. **Trading Parameters:**
   - Spread Percentage: 1.5% (distance from reference)
   - Order Amount: $1000 ($500 per side)

### 6. Start Trading

1. Click **"🚀 Start Bot"**
2. Bot will:
   - Initialize connections
   - Place BUY and SELL orders
   - Monitor for fills
   - Rebalance based on mode

3. Monitor in **Trading Tab:**
   - Live DEX/CEX prices
   - Price divergence
   - Active orders (from exchange API)
   - Real-time logs

### 7. Check Your Orders

**On the Exchange:**
- Go to your exchange's order book
- Search for LAND/USDT (or LANDSHARE/USDT for Gate.io)
- You'll see your BUY and SELL orders placed by the bot

**In the UI:**
- Trading Tab → Active Orders section
- Shows real order IDs from exchange
- Live status updates

### 8. Stop Trading

Click **"🛑 Stop Bot"** to:
- Cancel all open orders
- Close connections
- Shutdown gracefully

---

## 🔄 Switching Between Exchanges

1. Stop the bot if running
2. Select different exchange from dropdown
3. Portfolio and prices update automatically
4. Start bot with new exchange

---

## 📊 Trading Tab Features

### Live Price Data
- **DEX Price:** From PancakeSwap (LAND/BNB → USDT)
- **CEX Price:** From selected exchange
- **Divergence:** Price difference between DEX and CEX
- **Order Range:** Current buy/sell prices

### Active Orders
- Real orders from exchange API
- Order ID, Side, Price, Amount, Filled, Status
- Updates every cycle

### Bot Logs
- Real-time operation logs
- Connection status
- Order placement confirmations
- Fill notifications
- Error messages

---

## 💼 Portfolio Tab

Shows your exchange balances:
- All assets with non-zero balance
- Free, Used, and Total amounts
- Verifies API connection is working

---

## 📁 Configuration Files

### `auth_config.json`
```json
{
  "users": {
    "admin": {
      "password": "admin123",
      "role": "admin"
    }
  }
}
```

### `cex_credentials.json` (auto-generated)
```json
{
  "exchanges": {
    "mexc": {
      "api_key": "your_key",
      "secret": "your_secret"
    },
    "gateio": {
      "api_key": "your_key",
      "secret": "your_secret"
    },
    "bitmart": {
      "api_key": "your_key",
      "secret": "your_secret",
      "uid": "your_uid"
    }
  }
}
```

---

## 🐛 Troubleshooting

### "Failed to connect"
- Check API key/secret are correct
- Verify API permissions (read + trade)
- Check exchange API status

### "No active orders"
- Bot may be waiting for price data
- Check logs for errors
- Verify sufficient balance

### "Failed to place orders"
- Check balance is sufficient
- Verify trading pair exists on exchange
- Check API rate limits

### Portfolio not loading
- Test connection with "Connect & Save"
- Check API permissions include balance read
- Verify exchange API is online

---

## 🔧 Advanced Configuration

Edit `config.yaml` for advanced settings:
- Fill handling delays
- Risk management limits
- Inventory skew thresholds
- Circuit breaker settings

---

## 🎯 Trading Pairs by Exchange

| Exchange | Trading Pair |
|----------|-------------|
| MEXC | LAND/USDT |
| Gate.io | **LANDSHARE/USDT** |
| BitMart | LAND/USDT |

---

## 📈 Example Trading Flow

1. **Login** with admin credentials
2. **Add MEXC** exchange with API credentials
3. **View Portfolio** to verify connection
4. **Set parameters:** 1.5% spread, $1000 amount
5. **Select DEX mode** for immediate rebalancing
6. **Start Bot** - orders placed on MEXC
7. **Monitor** live prices and orders
8. **Wait for fills** - bot rebalances automatically
9. **Stop Bot** when done trading

---

## 🚨 Important Notes

- **Real Trading:** This bot places real orders with real money
- **Test First:** Use small amounts to test functionality
- **Monitor:** Watch the bot and check exchange directly
- **API Permissions:** Ensure read + trade permissions
- **Security:** Keep credentials secure, never share
- **Backup:** Save `cex_credentials.json` securely

---

## 📞 Support

For issues or questions:
1. Check logs in the Trading tab
2. Review this guide
3. Verify API credentials and permissions
4. Test connection in Portfolio tab

---

**Happy Trading! 🚀**
