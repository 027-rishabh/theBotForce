# LANDSHARE Market Maker - Testing Guide

## Testing Methods

### Method 1: Simulation Mode (No API Keys Required)
Test the bot logic without connecting to real exchanges.

### Method 2: Sandbox Mode (Exchange Testnet)
Test with real exchange APIs using testnet/sandbox credentials.

### Method 3: Live Testing (Small Amounts)
Test with real funds using minimal order sizes.

---

## Method 1: Simulation Mode (RECOMMENDED FOR FIRST TEST)

### Quick Test (Already Available)
```bash
cd /mnt/c/ZuvomoProjects/BotANDDashboard/exported-assets
python3 test_landshare_bot.py
```

**What It Does:**
- Simulates LAND price fetching
- Places mock orders
- Tests fill detection
- Validates rebalance logic
- No API keys needed
- Safe to run anytime

**Expected Output:**
```
LANDSHARE Market Maker Bot - Test Mode

Choose test mode:
1. DEX Reference Mode (Immediate rebalance)
2. CEX Reference Mode (2-minute delay)
3. Quick test (5 cycles, DEX mode)

Select option (1-3) [3]: 3

============================================================
Cycle 1/5
============================================================
LAND/USDT price: $0.385092
Order placed: BUY 1318.16 LAND/USDT @ $0.379316
Order placed: SELL 1279.20 LAND/USDT @ $0.390868
...
Total Fills: 1
Total Profit: $1.50
```

---

## Method 2: Sandbox/Testnet Mode

### Step 1: Get Sandbox API Keys

#### MEXC Sandbox (Recommended for Testing)
1. Visit: https://www.mexc.com/
2. Create account
3. Go to API Management
4. Create API key with "Spot Trading" permission
5. Note: MEXC may not have separate sandbox, use minimal real amounts

#### Gate.io Testnet
1. Visit: https://www.gate.io/testnet
2. Create testnet account
3. Generate testnet API credentials
4. Get free testnet USDT from faucet

#### Binance Testnet (For BNB/USDT Rate Testing)
1. Visit: https://testnet.binance.vision/
2. Create testnet account
3. No real funds needed

### Step 2: Configure Bot with Testnet Keys

**Option A: Via UI**
1. Go to: http://103.208.68.233:8501
2. Select exchange from dropdown
3. Expand "API Credentials"
4. Enter testnet API key and secret
5. Set order amount to minimum ($10-$50)
6. Click "Start Bot"

**Option B: Via config.yaml**
```yaml
api_credentials:
  mexc_api_key: "your_testnet_key"
  mexc_secret: "your_testnet_secret"

system:
  sandbox_mode: true

market_making:
  order_amount_usd: 50  # Small amount for testing
```

### Step 3: Run Test
```bash
python3 landshare_market_maker.py
```

---

## Method 3: Live Testing (Use with Caution)

### Prerequisites
- Real exchange account with funds
- Verified account (KYC completed)
- Small amount of USDT ($50-$100)
- Understanding of risks

### Step 1: Create Exchange Account

**MEXC (Easiest for LAND Trading)**
1. Sign up: https://www.mexc.com/
2. Complete KYC verification
3. Deposit minimum USDT ($50-100)
4. Generate API keys:
   - Go to: Account → API Management
   - Create new API key
   - Enable "Spot Trading" only
   - Add IP whitelist (your server IP)
   - Save API key and secret securely

### Step 2: Verify LAND is Listed
Check if LAND/USDT pair is available:
```bash
curl -s "https://api.mexc.com/api/v3/exchangeInfo" | grep -i "LANDUSDT"
```

### Step 3: Configure for Live Trading

**Update config.yaml:**
```yaml
api_credentials:
  mexc_api_key: "YOUR_REAL_API_KEY"
  mexc_secret: "YOUR_REAL_SECRET"

system:
  sandbox_mode: false  # IMPORTANT: Set to false for live

market_making:
  order_amount_usd: 50  # Start small!
  spread_percentage: 2.0  # Wider spread for safety

risk_management:
  max_position_usd: 100
  max_daily_trades: 20
  circuit_breaker:
    enabled: true
```

### Step 4: Test Real Price Fetching
```bash
python3 -c "
import asyncio
from landshare_token_manager import LANDTokenManager

async def test():
    config = {
        'token': {'contract_address': '0x9d986a3f147212327dd658f712d5264a73a1fdb0', 'trading_pair': 'LAND/USDT'},
        'dex': {'api_url': '', 'websocket_url': '', 'pair': 'LAND/WBNB'}
    }

    manager = LANDTokenManager(config)
    await manager.initialize()

    print('Fetching current LAND price...')
    price = await manager.get_land_usdt_price()
    print(f'LAND/USDT: \${price:.6f}')

    await manager.close()

asyncio.run(test())
"
```

**Expected Output:**
```
Fetching current LAND price...
LAND/USDT: $0.409741
```

### Step 5: Dry Run Check
Before starting, verify configuration:
```bash
python3 -c "
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

print('Configuration Check:')
print(f'Sandbox Mode: {config[\"system\"][\"sandbox_mode\"]}')
print(f'Exchange: {config[\"cex\"][\"selected_exchange\"]}')
print(f'Order Amount: \${config[\"market_making\"][\"order_amount_usd\"]}')
print(f'Spread: {config[\"market_making\"][\"spread_percentage\"]}%')
print(f'Reference Mode: {\"DEX\" if config[\"reference_mode\"][\"use_dex_reference\"] else \"CEX\"}')
"
```

### Step 6: Start Bot with Monitoring
```bash
# Start in one terminal
python3 landshare_market_maker.py

# Monitor logs in another terminal
tail -f logs/bot_*.log
```

---

## Interactive Dashboard Testing

### Using the Web Interface

**Access:** http://103.208.68.233:8501

**Test Flow:**

1. **Configure Exchange**
   - Select "MEXC Global" from dropdown
   - Click "API Credentials" to expand
   - Enter your API key and secret
   - Leave blank for demo mode (simulated)

2. **Set Parameters**
   - Spread: Start with 2.0% (safer)
   - Order Amount: $50 (minimal)
   - Refresh Interval: 60 seconds

3. **Choose Reference Mode**
   - Select "DEX Reference" for immediate rebalancing
   - Or "CEX Reference" for 2-minute delay

4. **Monitor Before Starting**
   - Watch the "Price Monitoring" section
   - Verify LAND price updates
   - Check order range calculation

5. **Start Bot**
   - Click "Start Bot" button
   - Watch logs appear in real-time
   - Monitor "Active Orders" table
   - Check for fills

6. **Stop Bot**
   - Click "Stop Bot" when done testing
   - Review logs for any errors

---

## What to Monitor During Testing

### Price Accuracy
Check if prices make sense:
```
LAND/USDT: $0.40-0.42 range (as of Oct 2025)
BNB/USDT: ~$1130
Order spread: ±1.5% from reference
```

### Order Placement
Verify orders are placed correctly:
```
Reference: $0.4097
Buy:  $0.4035 (1.5% below)
Sell: $0.4158 (1.5% above)
```

### Fill Detection
When an order fills:
```
DEX Mode: Should rebalance immediately
CEX Mode: Should wait 2 minutes, then rebalance
```

### Logs to Watch For
```
INFO - LAND/USDT price: $0.409741
INFO - Reference price from DEX: $0.409741
INFO - Order placed: BUY 1239.43 LAND/USDT @ $0.403644
INFO - Order placed: SELL 1202.16 LAND/USDT @ $0.415837
INFO - Order filled: SELL 1202.16 @ $0.415837
INFO - DEX mode: Immediate rebalance
```

---

## Testing Checklist

### Phase 1: Simulation (No Risk)
- [ ] Run test_landshare_bot.py successfully
- [ ] Verify DEX mode rebalances immediately
- [ ] Verify CEX mode waits 2 minutes
- [ ] Check price calculations are correct
- [ ] Confirm logs are detailed and clear

### Phase 2: Price Fetching (No Risk)
- [ ] Test landshare_token_manager.py
- [ ] Verify LAND/BNB price fetched
- [ ] Verify BNB/USDT conversion
- [ ] Confirm final LAND/USDT price is accurate
- [ ] Check price updates every cycle

### Phase 3: UI Testing (No Risk)
- [ ] Access dashboard at http://103.208.68.233:8501
- [ ] Select each exchange from dropdown
- [ ] Verify correct credential fields appear
- [ ] Test start/stop buttons (without API keys)
- [ ] Confirm price monitoring works

### Phase 4: Sandbox Testing (Low Risk)
- [ ] Get testnet API credentials
- [ ] Configure bot with testnet keys
- [ ] Place first test order
- [ ] Verify order appears on exchange
- [ ] Test order cancellation
- [ ] Test fill handling

### Phase 5: Live Testing (High Risk - Minimal Amounts)
- [ ] Use real API keys with $50-100
- [ ] Verify orders placed correctly
- [ ] Monitor for fills
- [ ] Check rebalance logic
- [ ] Run for 1 hour
- [ ] Stop and review performance

---

## Troubleshooting

### Issue: "No API keys provided"
**Solution:** Enter API credentials in UI or update config.yaml

### Issue: "Failed to fetch LAND price"
**Solution:** Check internet connection, DexScreener API may be down

### Issue: "Order placement failed"
**Solution:**
- Verify API keys are correct
- Check exchange account has funds
- Ensure LAND/USDT pair is available
- Check API permissions include spot trading

### Issue: "Fill not detected"
**Solution:**
- Orders may not be filled yet (low liquidity)
- Check exchange directly for order status
- Increase spread for better fill rate

### Issue: Dashboard not loading
**Solution:**
```bash
# Restart Streamlit
streamlit run landshare_ui.py --server.port 8501
```

---

## Quick Test Commands

### Test 1: Price Fetching
```bash
python3 landshare_token_manager.py
```

### Test 2: Simulation (5 cycles)
```bash
python3 test_landshare_bot.py <<< "3"
```

### Test 3: Simulation (DEX mode, 10 cycles)
```bash
python3 test_landshare_bot.py <<< "1
10"
```

### Test 4: Simulation (CEX mode, 10 cycles)
```bash
python3 test_landshare_bot.py <<< "2
10"
```

### Test 5: Configuration Check
```bash
python3 -c "import yaml; c=yaml.safe_load(open('config.yaml')); print(c['market_making'])"
```

---

## Recommended Testing Sequence

**Day 1: Simulation**
- Run test_landshare_bot.py multiple times
- Test both DEX and CEX modes
- Verify all logic works correctly

**Day 2: Price Fetching**
- Test real price fetching
- Monitor for 24 hours
- Verify prices are accurate

**Day 3: UI Testing**
- Configure via dashboard
- Test all parameters
- Verify visual feedback

**Day 4-7: Sandbox (if available)**
- Run with testnet credentials
- Monitor for fills
- Test edge cases

**Week 2: Live (Minimal Amounts)**
- Start with $50 orders
- Monitor closely
- Scale up gradually if successful

---

## Success Criteria

### Simulation Tests
- All cycles complete without errors
- Fills detected and handled correctly
- Profit calculations accurate
- Logs detailed and informative

### Live Tests
- Orders placed at correct prices
- Spreads calculated accurately
- Fills detected within 60 seconds
- Rebalancing occurs per mode settings
- No unexpected errors in logs
- Positive net P&L after fees

---

## Safety Reminders

1. Always start with simulation mode
2. Use testnet when possible
3. Start with minimal real amounts ($50)
4. Monitor closely for first 24 hours
5. Set tight risk limits
6. Enable circuit breakers
7. Have stop-loss ready
8. Don't risk more than you can afford to lose

---

## Getting Help

If you encounter issues:
1. Check logs in logs/ directory
2. Review TEST_RESULTS.md for expected behavior
3. Compare with IMPLEMENTATION_COMPLETE.txt
4. Verify configuration in config.yaml
5. Test price fetching independently

---

**Ready to test? Start with Method 1 (Simulation) - it's completely safe!**

```bash
python3 test_landshare_bot.py
```
