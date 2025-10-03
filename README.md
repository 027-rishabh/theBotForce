# LANDSHARE Market Maker Bot

Automated market making bot for LAND/USDT with dual reference price modes (DEX/CEX) and multi-exchange support.

## Features

- **Dual Reference Modes**
  - DEX Reference: Uses PancakeSwap price with immediate rebalancing
  - CEX Reference: Uses exchange mid-price with 2-minute delay

- **Multi-Exchange Support**
  - MEXC Global
  - Gate.io
  - BitMart (with memo support)
  - AscendEX (with group_id support)
  - BingX

- **Dynamic Refresh Interval**
  - Automatically adjusts refresh rate when price fluctuation exceeds spread
  - Fast refresh (10s) during high volatility
  - Normal refresh (60s) during stable periods

- **Real-Time Price Monitoring**
  - Live DEX price from PancakeSwap via DexScreener
  - Live CEX price from selected exchange
  - Price divergence tracking
  - Automatic order range calculation

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Credentials

Edit `config.yaml` and add your exchange API credentials:

```yaml
api_credentials:
  # For MEXC
  mexc_api_key: "your_api_key"
  mexc_secret: "your_secret"

  # For Gate.io
  gateio_api_key: "your_api_key"
  gateio_secret: "your_secret"
  gateio_password: "your_password"

  # For BitMart
  bitmart_api_key: "your_api_key"
  bitmart_secret: "your_secret"
  bitmart_uid: "your_uid"
  bitmart_memo: "your_memo"  # Required

  # For AscendEX
  ascendex_api_key: "your_api_key"
  ascendex_secret: "your_secret"
  ascendex_group_id: "your_group_id"  # Required

  # For BingX
  bingx_api_key: "your_api_key"
  bingx_secret: "your_secret"
```

### 3. Launch UI

```bash
streamlit run landshare_ui.py
```

### 4. Configure and Start

1. Select reference mode (DEX or CEX)
2. Choose your exchange
3. Enter API credentials in the UI
4. Set trading parameters (spread, order amount)
5. Click "Start Bot"

## Project Structure

```
├── landshare_ui.py              # Streamlit web interface
├── landshare_market_maker.py    # Market making engine
├── landshare_token_manager.py   # LAND price fetching
├── test_landshare_bot.py        # Testing framework
├── config.yaml                  # Configuration file
├── requirements.txt             # Python dependencies
└── archived_files/              # Old generic bot files
```

## API Credentials Required

### MEXC
- API Key
- API Secret

### Gate.io
- API Key
- API Secret
- API Password

### BitMart
- API Key
- API Secret
- UID
- **Memo** (Required for authentication)

### AscendEX
- API Key
- API Secret
- **Group ID** (Required for authentication)

### BingX
- API Key
- API Secret

## Trading Strategy

1. **Reference Price Selection**
   - DEX mode: Uses PancakeSwap LAND/USDT price
   - CEX mode: Uses exchange LAND/USDT mid-price

2. **Order Placement**
   - Buy order: Reference price × (1 - spread%)
   - Sell order: Reference price × (1 + spread%)
   - Post-only orders to ensure maker fees

3. **Dynamic Rebalancing**
   - Monitors price fluctuation vs spread threshold
   - Reduces refresh interval to 10s when price moves > spread
   - Returns to 60s during stable periods

4. **Fill Handling**
   - DEX mode: Immediate rebalance
   - CEX mode: 2-minute delay before rebalance

## Configuration Parameters

```yaml
# Market Making
spread_percentage: 1.5      # 1.5% spread around reference
order_amount_usd: 1000      # $1000 total ($500 per side)
post_only: true             # Maker-only orders

# Reference Mode
use_dex_reference: true     # true = DEX, false = CEX
sync_interval: 60           # Price sync interval (seconds)

# Fill Handling
dex_mode_delay: 0           # Immediate for DEX mode
cex_mode_delay: 120         # 2 minutes for CEX mode

# Risk Management
max_inventory_skew: 0.3     # 30% max imbalance
max_position_usd: 5000      # $5000 max position
max_daily_trades: 200       # 200 trades per day
```

## Testing

Run simulation without API keys:

```bash
python test_landshare_bot.py
```

## UI Features

### Price Monitoring
- Real-time DEX price (PancakeSwap)
- Real-time CEX price (selected exchange)
- Price divergence calculation
- Dynamic order range display

### Configuration
- Visual reference mode toggle
- Exchange-specific credential inputs
- Dynamic credential validation
- Trading parameter sliders

### Status Display
- Bot running/stopped indicator
- Current configuration summary
- Active orders table
- Real-time logs

### Dynamic Refresh
- Automatic interval adjustment
- Visual refresh indicator
- Based on price volatility

## Risk Management

- Position size limits
- Daily trade limits
- Inventory skew monitoring
- Circuit breaker for extreme price movements
- Post-only orders to minimize fees

## Important Notes

1. **BitMart**: Requires memo field for API authentication
2. **AscendEX**: Requires group_id for API authentication
3. **Sandbox Mode**: Enable in config.yaml for testing
4. **Price Source**: DEX prices from DexScreener, CEX from selected exchange
5. **Dynamic Refresh**: Interval adjusts automatically based on volatility

## Support

For issues or questions:
- Check configuration in `config.yaml`
- Review logs in UI when bot is running
- Test with small amounts first
- Ensure all required API credentials are provided

## Disclaimer

This bot is for educational purposes. Cryptocurrency trading involves substantial risk. Always:
- Test thoroughly before live trading
- Use only funds you can afford to lose
- Monitor the bot continuously
- Understand the strategy and risks

## License

Use at your own risk. No warranties provided.
