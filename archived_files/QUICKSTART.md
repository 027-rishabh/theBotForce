# 🚀 DEX/CEX Arbitrage Bot - Quick Start Guide

## ✅ Prerequisites Checklist

- [ ] Python 3.8+ installed
- [ ] Git installed (optional)
- [ ] Exchange account created (Binance/Coinbase/Kraken)
- [ ] API keys ready (start with sandbox/testnet keys)

---

## 📦 Installation

### Option 1: Automated Setup (Recommended)

```bash
# Run automated deployment script
python3 deploy.py
```

The script will:
- Create virtual environment
- Install all dependencies
- Set up configuration
- Create startup scripts
- Run tests

### Option 2: Manual Setup

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment file
cp .env.example .env
# Edit .env with your API keys
```

---

## ⚙️ Configuration

### 1. Configure API Keys

Edit `.env` file:

```bash
# CEX Exchange API
CEX_API_KEY=your_api_key_here
CEX_SECRET=your_secret_here

# Enable sandbox mode for testing
SANDBOX_MODE=true
```

### 2. Configure Trading Parameters

Edit `config.yaml`:

```yaml
# Trading symbols
symbols:
  - "BTC/USDT"
  - "ETH/USDT"

# Strategy parameters
price_threshold: 0.02      # 2% movement detection
rebalance_delay: 120       # 2 minutes wait
spread_range: 0.02         # 2% order placement range

# Risk management
max_position_size: 0.01    # 1% of portfolio
portfolio_value: 10000.0   # Portfolio size in USD

# Safety settings
sandbox_mode: true         # Paper trading mode
```

---

## 🎯 Running the Bot

### Demo Mode (No API Keys Needed)

Test the bot logic without real trading:

```bash
python3 demo.py
```

Choose option 1-3 for different demo lengths.

### Main Bot (Requires API Keys)

```bash
# Make sure .env is configured first!
python3 main_bot.py
```

**Command-line options:**

```bash
# Custom config file
python3 main_bot.py --config my_config.yaml

# Debug mode
python3 main_bot.py --log-level DEBUG
```

### Web Dashboard

Launch the Streamlit dashboard for visual monitoring:

```bash
streamlit run dex_cex_arbitrage_streamlit.py
```

Access at: http://localhost:8501

---

## 📊 Dashboard Features

Once running, the dashboard provides:

- **Real-time Control**: Start/Stop bot with buttons
- **Live Price Monitoring**: DEX vs CEX price charts
- **Order Management**: Track all active orders
- **Configuration**: Adjust parameters on-the-fly
- **Logs**: Real-time bot activity logs
- **Performance Metrics**: P&L, success rate, etc.

---

## 🔐 Security Best Practices

### Before Going Live:

1. **Always start with sandbox mode**
   ```yaml
   sandbox_mode: true
   ```

2. **Use testnet API keys first**
   - Binance Testnet: https://testnet.binance.vision/
   - Never use production keys for testing

3. **Enable IP restrictions**
   - Configure in exchange API settings
   - Whitelist only your server IP

4. **Secure your .env file**
   ```bash
   chmod 600 .env  # Linux/Mac only
   ```

5. **Never commit secrets**
   - .env is in .gitignore by default
   - Double-check before git push

---

## 📈 Trading Strategy Overview

**The bot implements this strategy:**

1. **Monitor** DEX and CEX prices continuously
2. **Place Orders** on CEX:
   - Buy order: DEX price - 1%
   - Sell order: DEX price + 1%
3. **Detect** 2%+ price movements on DEX
4. **Wait** 2 minutes after detection
5. **Rebalance** orders to new price levels

**Example:**

```
DEX Price: $50,000
CEX Buy Order:  $49,500 (1% below)
CEX Sell Order: $50,500 (1% above)

If DEX moves to $51,000 (2% increase):
→ Wait 2 minutes
→ Cancel old orders
→ Place new orders:
   Buy:  $50,490
   Sell: $51,510
```

---

## 🛠️ Troubleshooting

### Virtual Environment Issues (WSL/Linux)

```bash
# Install python3-venv if needed
sudo apt install python3.10-venv

# Then recreate venv
python3 -m venv venv
```

### API Connection Errors

```
❌ Error: Invalid API credentials
```

**Solution:**
1. Check API keys in `.env`
2. Verify sandbox mode matches your keys
3. Check API permissions on exchange

### Import Errors

```
❌ ModuleNotFoundError: No module named 'ccxt'
```

**Solution:**
```bash
# Make sure venv is activated
source venv/bin/activate  # or venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt
```

### WebSocket Connection Issues

```
❌ WebSocket connection failed
```

**Solution:**
- Bot falls back to simulation mode automatically
- Check network/firewall settings
- Verify exchange API status

---

## 📝 Recommended Testing Flow

### Phase 1: Demo (No Risk)
```bash
python3 demo.py
```
✅ Understand the strategy logic

### Phase 2: Sandbox Mode (No Real Money)
```bash
# Set in config.yaml:
sandbox_mode: true

python3 main_bot.py
```
✅ Test with exchange sandbox/testnet

### Phase 3: Paper Trading Dashboard
```bash
streamlit run dex_cex_arbitrage_streamlit.py
```
✅ Monitor performance for 24-48 hours

### Phase 4: Live (Small Positions)
```bash
# In config.yaml:
sandbox_mode: false
max_position_size: 0.001  # 0.1% instead of 1%
portfolio_value: 100      # Start very small
```
✅ Monitor closely for first week

---

## 🎓 Learning Resources

### Understand the Code

1. **`main_bot.py`** - Main trading logic
2. **`exchange_integrations.py`** - Exchange connectivity
3. **`dex_cex_arbitrage_streamlit.py`** - Dashboard UI
4. **`config.yaml`** - All configuration options

### Read the Guides

- `README.md` - Project overview
- `DEX-CEX-Bot-Guide.md` - Comprehensive guide
- `PRE_LAUNCH_CHECKLIST.md` - Go-live checklist

---

## ⚠️ Important Warnings

### This Bot Is For:
✅ Educational purposes
✅ Research and experimentation
✅ Learning automated trading concepts

### Remember:
❌ Cryptocurrency trading is HIGH RISK
❌ You can lose money
❌ Past performance ≠ future results
❌ No guarantees of profit

### Legal:
- Check local regulations
- Understand tax implications
- Comply with exchange ToS
- Use only funds you can afford to lose

---

## 🆘 Getting Help

### Check Logs
```bash
# Logs are in logs/ directory
tail -f logs/bot_*.log
```

### Common Issues
1. Review `PRE_LAUNCH_CHECKLIST.md`
2. Check exchange API status pages
3. Verify config.yaml syntax (YAML is whitespace-sensitive)
4. Ensure all dependencies installed

### Debug Mode
```bash
python3 main_bot.py --log-level DEBUG
```

---

## 🎉 Next Steps

Once comfortable with the basics:

1. **Optimize parameters** based on your testing
2. **Add more symbols** to monitor
3. **Adjust risk management** settings
4. **Monitor performance** metrics
5. **Review and refine** strategy

---

## 📞 Quick Reference

### Start Bot
```bash
python3 main_bot.py
```

### Start Dashboard
```bash
streamlit run dex_cex_arbitrage_streamlit.py
```

### Run Demo
```bash
python3 demo.py
```

### View Logs
```bash
tail -f logs/bot_*.log
```

### Check Configuration
```bash
cat config.yaml
```

---

**Happy Trading! 🤖📈**

*Remember: Start small, test thoroughly, and never risk more than you can afford to lose.*
