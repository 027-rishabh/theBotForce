# DEX/CEX Arbitrage Trading Bot - Complete Implementation Guide

## Overview

This comprehensive trading bot monitors price differences between Decentralized Exchanges (DEX) and Centralized Exchanges (CEX), automatically placing buy and sell orders within a 2% range of DEX prices. When DEX prices move by 2% or more, the bot waits 2 minutes before rebalancing orders to new price levels.

## Key Features

### 🤖 Automated Trading Logic
- **Price Monitoring**: Real-time monitoring of DEX and CEX prices
- **Order Placement**: Places buy/sell orders on CEX within 2% range of DEX price
- **Price Movement Detection**: Detects 2% price movements on DEX
- **Delayed Rebalancing**: Waits 2 minutes after price movement before rebalancing orders
- **Risk Management**: Position sizing, daily trade limits, stop-loss protection

### 📊 Advanced Features
- **Multi-Exchange Support**: CCXT integration for 100+ exchanges
- **WebSocket Connectivity**: Real-time price feeds and order updates
- **Performance Tracking**: Comprehensive metrics and analytics
- **Streamlit Dashboard**: Real-time monitoring and control interface
- **Configuration Management**: YAML-based configuration with hot-reloading

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   Main Bot      │    │  Exchange APIs  │
│   Dashboard     │◄──►│   Controller    │◄──►│   (CCXT)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  WebSocket      │
                    │  Handlers       │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Price Data     │
                    │  Processing     │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Risk Manager   │
                    │  & Order Logic  │
                    └─────────────────┘
```

## File Structure

```
dex-cex-arbitrage-bot/
├── main_bot.py                      # Main bot implementation
├── exchange_integrations.py         # CCXT & WebSocket handlers
├── dex_cex_arbitrage_streamlit.py  # Streamlit UI
├── config.yaml                     # Configuration file
├── requirements.txt                # Python dependencies
├── logs/                          # Log files directory
└── data/                         # Historical data storage
```

## Installation & Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config.yaml` with your settings:

```yaml
# Exchange Settings
cex_exchange: "binance"        # Target CEX for trading
dex_source: "coingecko"       # DEX data source

# API Credentials
cex_api_key: "your_api_key"
cex_secret: "your_secret"
dex_api_key: "optional_key"

# Trading Parameters
symbols:
  - "BTC/USDT"
  - "ETH/USDT"

max_position_size: 0.01    # 1% of portfolio per position
price_threshold: 0.02      # 2% price movement threshold
rebalance_delay: 120       # 2 minutes delay
spread_range: 0.02         # 2% spread range

# Risk Management
portfolio_value: 10000.0   # Portfolio value in USD
max_daily_trades: 100      # Daily trade limit
stop_loss_pct: 0.05       # 5% stop loss

# System Settings
sandbox_mode: true         # Use paper trading
log_level: "INFO"
```

### 3. API Key Setup

#### Binance API Setup
1. Go to [Binance API Management](https://www.binance.com/en/my/settings/api-management)
2. Create new API key
3. Enable "Spot & Margin Trading" (for live trading)
4. Add IP restrictions for security
5. Copy API Key and Secret to config.yaml

#### Other Exchanges
- **Coinbase Pro**: [API Settings](https://pro.coinbase.com/profile/api)
- **Kraken**: [API Settings](https://www.kraken.com/u/security/api)
- **KuCoin**: [API Management](https://www.kucoin.com/account/api)

## Running the Bot

### 1. Command Line Mode

```bash
# Run with default config
python main_bot.py

# Run with custom config
python main_bot.py --config my_config.yaml

# Run with debug logging
python main_bot.py --log-level DEBUG
```

### 2. Streamlit Dashboard

```bash
# Start the web interface
streamlit run dex_cex_arbitrage_streamlit.py
```

Access the dashboard at `http://localhost:8501`

## Trading Strategy Details

### Core Logic Flow

1. **Price Monitoring**
   - Continuously monitor DEX and CEX prices
   - Calculate price differences in real-time
   - Store price history for analysis

2. **Order Placement Conditions**
   ```python
   # Place orders when price difference is within acceptable range
   if abs(price_difference_pct) <= spread_range:
       buy_price = dex_price * (1 - spread_range/2)  # 1% below DEX
       sell_price = dex_price * (1 + spread_range/2) # 1% above DEX
       place_orders(buy_price, sell_price)
   ```

3. **Price Movement Detection**
   ```python
   # Detect significant price movements
   price_change_pct = abs(current_price - last_price) / last_price
   if price_change_pct >= price_threshold:  # 2%
       schedule_rebalance(new_price, delay=120)  # 2 minutes
   ```

4. **Order Rebalancing**
   - Cancel existing orders
   - Wait for configured delay (2 minutes)
   - Place new orders at updated price levels

### Risk Management Features

#### Position Sizing
```python
max_position_value = portfolio_value * max_position_size  # 1%
quantity = max_position_value / current_price
quantity = max(min_quantity, min(quantity, max_quantity))
```

#### Daily Trade Limits
- Tracks trades per day per symbol
- Stops trading when daily limit reached
- Resets counter at midnight

#### Stop-Loss Protection
- Monitors unrealized losses on positions
- Automatically closes positions exceeding stop-loss threshold
- Configurable stop-loss percentage (default 5%)

## Monitoring & Analytics

### Performance Metrics

The bot tracks comprehensive performance data:

- **Trade Statistics**: Total trades, success rate, average profit
- **Risk Metrics**: Maximum drawdown, Sharpe ratio, volatility
- **System Metrics**: Uptime, API call counts, error rates
- **Daily P&L**: Profit/loss tracking by day and symbol

### Logging System

Comprehensive logging at multiple levels:

```
2025-10-03 16:30:15 - INFO - 🚀 Bot started successfully
2025-10-03 16:30:20 - INFO - 📊 Monitoring BTC/USDT - DEX: $50,000, CEX: $49,950
2025-10-03 16:30:21 - INFO - 📋 Order placed: BUY 0.002 BTC/USDT @ $49,850
2025-10-03 16:32:45 - INFO - 📈 Price movement detected: 2.1%
2025-10-03 16:32:45 - INFO - ⏰ Scheduling rebalance in 120 seconds
```

### Alerts & Notifications

Configure alerts for:
- Large price movements
- Order execution errors
- Risk limit breaches
- System connectivity issues

## Advanced Configuration

### Exchange-Specific Settings

```yaml
exchanges:
  binance:
    sandbox: true
    rate_limit: 10  # requests per second
    order_types: ["limit", "market"]
    
  coinbase:
    sandbox: true
    rate_limit: 5
    order_types: ["limit"]
```

### Trading Pair Configuration

```yaml
symbols:
  BTC/USDT:
    min_quantity: 0.001
    max_quantity: 1.0
    tick_size: 0.01
    
  ETH/USDT:
    min_quantity: 0.01
    max_quantity: 10.0
    tick_size: 0.01
```

## Troubleshooting

### Common Issues

#### 1. API Connection Errors
```
❌ Error: Invalid API credentials
```
**Solution**: Verify API keys and permissions in exchange settings

#### 2. Insufficient Balance
```
❌ Error: Insufficient balance for order
```
**Solution**: Check account balance and reduce position sizes

#### 3. Rate Limit Exceeded
```
❌ Error: Rate limit exceeded
```
**Solution**: Increase delays between API calls or upgrade API plan

#### 4. WebSocket Connection Issues
```
❌ Error: WebSocket connection failed
```
**Solution**: Check network connectivity and firewall settings

### Debug Mode

Enable detailed debugging:

```bash
python main_bot.py --log-level DEBUG
```

This provides detailed information about:
- API request/response details
- Order placement logic
- Price calculation steps
- WebSocket message flow

## Security Best Practices

### API Key Security
- Use read-only keys for monitoring
- Enable IP restrictions
- Store keys in environment variables
- Never commit keys to version control

### Network Security
- Use VPN for trading connections
- Enable firewall rules
- Monitor for unusual API activity

### Operational Security
- Start with paper trading
- Use small position sizes initially
- Monitor bot performance closely
- Have manual override procedures

## Performance Optimization

### Latency Optimization
- Use WebSocket connections for real-time data
- Deploy bot close to exchange servers
- Optimize order placement logic
- Use async/await for concurrent operations

### Resource Management
- Limit historical data retention
- Compress log files
- Monitor memory usage
- Implement connection pooling

## Legal and Compliance

### Regulatory Considerations
- Check local regulations for automated trading
- Understand tax implications of trades
- Comply with exchange terms of service
- Consider market maker agreements

### Risk Disclaimers
- Cryptocurrency trading carries high risk
- Past performance doesn't guarantee future results
- Use only funds you can afford to lose
- Test thoroughly before live trading

## Support and Maintenance

### Regular Maintenance Tasks
- Update dependencies monthly
- Review and adjust risk parameters
- Monitor exchange API changes
- Backup configuration and logs

### Performance Review
- Weekly performance analysis
- Risk metric evaluation
- Strategy parameter optimization
- Market condition adjustments

## Deployment Options

### Local Deployment
- Run on personal computer
- Suitable for development and testing
- Manual monitoring required

### Cloud Deployment
```bash
# Docker deployment
docker build -t dex-cex-bot .
docker run -d --name trading-bot dex-cex-bot

# AWS/GCP deployment
# Use cloud instances with persistent storage
# Configure auto-restart and monitoring
```

### VPS Deployment
- 24/7 operation
- Better connectivity to exchanges
- Remote monitoring capabilities

This comprehensive guide provides everything needed to deploy and operate the DEX/CEX arbitrage trading bot successfully. Remember to always start with paper trading and gradually scale up after thorough testing.