# How to Run LANDSHARE Market Maker on Your Own

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Internet connection
- 2GB RAM minimum
- Operating System: Windows, Linux, or macOS

### Required Accounts
- Exchange account (MEXC, Gate.io, BitMart, AscendEX, or BingX)
- API credentials from your chosen exchange

---

## Step-by-Step Setup

### 1. Install Python Dependencies

```bash
cd /mnt/c/ZuvomoProjects/BotANDDashboard/exported-assets

# Install required packages
pip install -r requirements.txt
```

**If requirements.txt is missing, install manually:**
```bash
pip install ccxt pandas numpy aiohttp asyncio pyyaml streamlit plotly websockets python-dotenv
```

### 2. Get Exchange API Credentials

#### For MEXC (Recommended - Easy Setup):
1. Sign up at https://www.mexc.com/
2. Complete KYC verification
3. Go to **Account → API Management**
4. Click **Create API Key**
5. Enable **"Spot Trading"** permission only
6. **Important:** Add your IP address to whitelist for security
7. Save your API Key and Secret securely

#### For Gate.io:
1. Sign up at https://www.gate.io/
2. Go to **API Management**
3. Create API key with **Spot Trading** permission
4. You'll get: API Key, Secret, and Password (all 3 required)

#### For BitMart:
1. Sign up at https://www.bitmart.com/
2. Get API Key, Secret, and your UID

#### For AscendEX or BingX:
Similar process - get API Key and Secret from their API management sections.

### 3. Configure Your Bot

**Option A: Using the Web Interface (Easiest)**

1. Start the dashboard:
```bash
streamlit run landshare_ui.py
```

2. Open your browser to the URL shown (usually http://localhost:8501)

3. In the interface:
   - Select your exchange from dropdown
   - Click "API Credentials" to expand
   - Enter your API Key and Secret
   - Set your trading parameters:
     - Spread: 1.5% (recommended for start)
     - Order Amount: $100 (start small!)
     - Refresh Interval: 60 seconds
   - Choose Reference Mode:
     - **DEX Reference:** Immediate rebalancing (faster)
     - **CEX Reference:** 2-minute delay (safer)
   - Click **"Start Bot"**

**Option B: Using Configuration File**

1. Create a `.env` file:
```bash
nano .env
```

2. Add your credentials:
```env
# For MEXC
MEXC_API_KEY=your_api_key_here
MEXC_SECRET=your_secret_here

# For Gate.io
GATEIO_API_KEY=your_api_key_here
GATEIO_SECRET=your_secret_here
GATEIO_PASSWORD=your_password_here

# For BitMart
BITMART_API_KEY=your_api_key_here
BITMART_SECRET=your_secret_here
BITMART_UID=your_uid_here

# For AscendEX
ASCENDEX_API_KEY=your_api_key_here
ASCENDEX_SECRET=your_secret_here

# For BingX
BINGX_API_KEY=your_api_key_here
BINGX_SECRET=your_secret_here
```

3. Edit config.yaml:
```bash
nano config.yaml
```

4. Update these sections:
```yaml
cex:
  selected_exchange: "mexc"  # Change to your exchange

market_making:
  order_amount_usd: 100  # Start with small amount
  spread_percentage: 1.5  # Recommended starting spread

reference_mode:
  use_dex_reference: true  # true = DEX mode, false = CEX mode

system:
  sandbox_mode: false  # Set to true if testing with testnet
```

---

## Running the Bot

### Method 1: Web Interface (Recommended)

```bash
streamlit run landshare_ui.py
```

Then open http://localhost:8501 in your browser.

**To make it accessible from other devices on your network:**
```bash
streamlit run landshare_ui.py --server.address 0.0.0.0 --server.port 8501
```

**To run in background:**
```bash
nohup streamlit run landshare_ui.py --server.headless true --server.port 8501 &
```

### Method 2: Direct Python Execution

```bash
python3 landshare_market_maker.py
```

---

## Testing Before Going Live

### Test 1: Simulation Mode (No Risk)
Test all logic without connecting to real exchange:
```bash
python3 test_landshare_bot.py
# Select option 3 for quick test
```

### Test 2: Price Fetching
Verify real LAND price is being fetched correctly:
```bash
python3 landshare_token_manager.py
```

You should see:
```
LAND/USDT Price: $0.410473
Bid: $0.410268
Ask: $0.410678
```

### Test 3: Small Live Test
1. Start with **$50-100** order amount
2. Use **2.0% spread** (wider = safer)
3. Enable DEX reference mode
4. Monitor for 1 hour
5. Check logs in `logs/` directory

---

## Monitoring Your Bot

### View Logs
```bash
# Real-time log monitoring
tail -f logs/bot_*.log

# View all recent logs
cat logs/bot_*.log | tail -100
```

### Check Bot Status
The web interface shows:
- Current LAND/USDT price
- Active orders
- Fill events
- Profit/loss
- Bot status (Running/Stopped)

### Manual Order Check
Log into your exchange and check:
- Open orders for LAND/USDT
- Recent trades
- Account balance

---

## Stopping the Bot

### From Web Interface
Click the **"Stop Bot"** button

### From Command Line
```bash
# If running in foreground
Press Ctrl+C

# If running in background
ps aux | grep streamlit
kill <process_id>

# Or kill all streamlit processes
pkill -f streamlit
```

---

## Important Safety Tips

### Start Small
- Begin with $50-100 order amounts
- Use wider spreads (2-3%) initially
- Test for 24 hours before increasing size

### Monitor Closely
- Check every few hours for first 24 hours
- Watch for unexpected price movements
- Verify orders are being placed correctly

### Risk Management
The bot has built-in protections:
- Maximum position size limits
- Circuit breakers on large price moves (10%)
- Daily trade limits
- Post-only orders (avoid taker fees)

### Verify Configuration
Before starting, always verify:
```bash
# Check your config
python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print('Exchange:', c['cex']['selected_exchange']); print('Order Amount:', c['market_making']['order_amount_usd']); print('Spread:', c['market_making']['spread_percentage'])"
```

---

## Troubleshooting

### Issue: "Module not found"
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "API authentication failed"
**Solution:**
- Verify API key and secret are correct
- Check API permissions include "Spot Trading"
- Ensure IP whitelist includes your IP
- For Gate.io: verify password is correct

### Issue: "Failed to fetch LAND price"
**Solution:**
- Check internet connection
- DexScreener API might be temporarily down
- Wait a few minutes and retry

### Issue: "Order placement failed"
**Solution:**
- Check exchange account has sufficient USDT
- Verify LAND/USDT pair is available on exchange
- Check minimum order size requirements
- Ensure account is verified (KYC complete)

### Issue: Dashboard won't load
**Solution:**
```bash
# Check if port 8501 is already in use
lsof -i :8501

# Use different port
streamlit run landshare_ui.py --server.port 8502
```

---

## Expected Performance

### Typical Metrics (DEX Reference Mode)
- **Order Refresh:** Every 60 seconds
- **Fill Rate:** 5-20% depending on market volatility
- **Profit per Fill:** $0.50 - $3.00 (on $500 orders)
- **Daily Trades:** 10-50 depending on activity

### Cost Considerations
- Exchange maker fees: Usually 0.1% or less
- Network fees: Minimal (CEX trading, not DEX)
- Slippage: Minimal (post-only orders)

---

## Advanced Configuration

### Running on VPS/Cloud Server

**Deploy to AWS, DigitalOcean, or similar:**

1. Rent a VPS (Ubuntu recommended)
2. Install Python 3.8+
3. Clone/upload your bot files
4. Install dependencies
5. Configure firewall for port 8501
6. Run with nohup or systemd service

**Example systemd service:**
```bash
sudo nano /etc/systemd/system/landshare-bot.service
```

```ini
[Unit]
Description=LANDSHARE Market Maker Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/exported-assets
ExecStart=/usr/bin/python3 landshare_market_maker.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable landshare-bot
sudo systemctl start landshare-bot
sudo systemctl status landshare-bot
```

### Using Docker (Optional)

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "landshare_ui.py", "--server.headless", "true", "--server.port", "8501"]
```

Build and run:
```bash
docker build -t landshare-bot .
docker run -d -p 8501:8501 --env-file .env landshare-bot
```

---

## Getting Help

### Check Logs First
```bash
tail -100 logs/bot_*.log
```

### Verify Configuration
```bash
cat config.yaml
```

### Test Individual Components
```bash
# Test price fetching
python3 landshare_token_manager.py

# Test simulation
python3 test_landshare_bot.py
```

### Documentation Files
- `TESTING_GUIDE.md` - Comprehensive testing instructions
- `FINAL_UPDATE.md` - Latest features and changes
- `TEST_RESULTS.md` - Expected test results
- `IMPLEMENTATION_COMPLETE.txt` - Complete feature list

---

## Quick Start Checklist

- [ ] Python 3.8+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Exchange account created and verified
- [ ] API credentials obtained
- [ ] Deposited small amount ($100-200 USDT)
- [ ] Ran simulation test successfully
- [ ] Tested price fetching
- [ ] Configured bot (web interface or config.yaml)
- [ ] Started with small order size ($50-100)
- [ ] Set wider spread (2%+) for safety
- [ ] Monitoring logs and orders

---

## Summary

**To get started right now:**

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Get your exchange API credentials

3. Start the dashboard:
   ```bash
   streamlit run landshare_ui.py
   ```

4. Open http://localhost:8501

5. Enter your API credentials

6. Start with $100 orders and 2% spread

7. Monitor closely for first 24 hours

**You're ready to run the LANDSHARE Market Maker on your own system!**
