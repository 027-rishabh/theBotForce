# LANDSHARE Market Maker - Quick Start

## 3-Minute Setup

### 1. Install Dependencies (One-Time)
```bash
cd /mnt/c/ZuvomoProjects/BotANDDashboard/exported-assets
pip install ccxt pandas numpy aiohttp pyyaml streamlit plotly websockets python-dotenv
```

### 2. Test Without API Keys (Safe)
```bash
python3 test_landshare_bot.py
# Press 3 for quick test
```

Expected output: 5 cycles, simulated fills, profit tracking

### 3. Get Real LAND Price
```bash
python3 landshare_token_manager.py
```

Expected output: `LAND/USDT Price: $0.41xxxx`

### 4. Start Web Interface
```bash
streamlit run landshare_ui.py
```

Open browser to: http://localhost:8501

### 5. Configure in Browser
1. Select exchange (MEXC recommended)
2. Expand "API Credentials"
3. Enter your API Key and Secret
4. Set Order Amount: $100 (start small)
5. Set Spread: 2.0% (safer)
6. Click "Start Bot"

---

## Essential Commands

### Start Bot (Web Interface)
```bash
streamlit run landshare_ui.py
```

### Start Bot (Background)
```bash
nohup streamlit run landshare_ui.py --server.headless true --server.port 8501 &
```

### Stop Bot
```bash
# Press Ctrl+C if running in foreground

# Or kill background process
pkill -f streamlit
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

## Get Exchange API Keys

### MEXC (Easiest)
1. https://www.mexc.com/ → Sign up
2. Account → API Management
3. Create API Key (Spot Trading only)
4. Save Key + Secret

### Gate.io
1. https://www.gate.io/ → Sign up
2. API Management → Create
3. Save Key + Secret + Password

### Others
Similar process for BitMart, AscendEX, BingX

---

## Safety Checklist

- [ ] Start with $50-100 order size
- [ ] Use 2%+ spread initially
- [ ] Test in simulation first
- [ ] Monitor for first hour
- [ ] Check logs regularly
- [ ] Verify orders on exchange

---

## Troubleshooting

**"Module not found"**
```bash
pip install -r requirements.txt
```

**"API authentication failed"**
- Check API key is correct
- Enable "Spot Trading" permission
- Add IP to whitelist

**"Failed to fetch LAND price"**
- Check internet connection
- Wait a few minutes, retry

**Dashboard won't load**
```bash
# Use different port
streamlit run landshare_ui.py --server.port 8502
```

---

## Current Status

Bot is ready to run. Current LAND price: ~$0.41

**Simulation tested:** Working
**Price fetching:** Working
**Web interface:** Working
**Multi-exchange:** Ready (needs your API keys)

---

## Next Steps

1. Get exchange API credentials
2. Run simulation test (safe)
3. Start web interface
4. Enter credentials
5. Begin with small amounts ($50-100)
6. Monitor closely
7. Scale up gradually

**Full documentation:** See SETUP_YOUR_OWN.md
**Testing guide:** See TESTING_GUIDE.md
**Latest updates:** See FINAL_UPDATE.md
