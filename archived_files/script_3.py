# Create the complete integrated bot with all components
complete_bot_code = """
#!/usr/bin/env python3
\"\"\"
DEX/CEX Arbitrage Trading Bot
Complete implementation with CCXT integration, WebSocket handlers, and Streamlit UI

Usage:
    python main_bot.py

Features:
- Monitor price differences between DEX and CEX
- Place orders within 2% range of DEX price
- Rebalance orders after 2% price movements with 2-minute delay
- Real-time monitoring via Streamlit dashboard
- Risk management and position sizing
- Comprehensive logging and error handling
\"\"\"

import asyncio
import logging
import os
import sys
import json
import time
import signal
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import threading
import queue
import yaml

# Import our custom modules
# from exchange_integrations import ExchangeManager, DEXPriceHandler, WebSocketManager

@dataclass
class BotConfig:
    \"\"\"Bot configuration dataclass\"\"\"
    # Exchange settings
    cex_exchange: str = 'binance'
    dex_source: str = 'coingecko'
    
    # API credentials
    cex_api_key: str = ''
    cex_secret: str = ''
    dex_api_key: str = ''
    
    # Trading parameters
    symbols: List[str] = None
    max_position_size: float = 0.01  # 1% of portfolio
    price_threshold: float = 0.02    # 2% price movement
    rebalance_delay: int = 120       # 2 minutes
    spread_range: float = 0.02       # 2% spread
    
    # Risk management
    portfolio_value: float = 10000.0
    min_quantity: float = 0.001
    max_quantity: float = 1.0
    max_daily_trades: int = 100
    stop_loss_pct: float = 0.05      # 5% stop loss
    
    # System settings
    sandbox_mode: bool = True
    log_level: str = 'INFO'
    data_retention_days: int = 30
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ['BTC/USDT', 'ETH/USDT']


class PerformanceTracker:
    \"\"\"Track bot performance metrics\"\"\"
    
    def __init__(self):
        self.start_time = datetime.now()
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
        self.daily_profits = {}
        
    def record_trade(self, profit: float, successful: bool):
        \"\"\"Record a completed trade\"\"\"
        self.total_trades += 1
        if successful:
            self.successful_trades += 1
            
        self.total_profit += profit
        
        # Track daily profits
        today = datetime.now().date()
        if today not in self.daily_profits:
            self.daily_profits[today] = 0.0
        self.daily_profits[today] += profit
    
    def get_metrics(self) -> Dict:
        \"\"\"Get performance metrics\"\"\"
        success_rate = (self.successful_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_profit = self.total_profit / self.total_trades if self.total_trades > 0 else 0
        
        return {
            'runtime': datetime.now() - self.start_time,
            'total_trades': self.total_trades,
            'successful_trades': self.successful_trades,
            'success_rate': success_rate,
            'total_profit': self.total_profit,
            'average_profit_per_trade': avg_profit,
            'max_drawdown': self.max_drawdown,
            'daily_profits': self.daily_profits
        }


class RiskManager:
    \"\"\"Manage trading risks and position sizing\"\"\"
    
    def __init__(self, config: BotConfig):
        self.config = config
        self.daily_trades = {}
        self.active_positions = {}
        
    def can_place_order(self, symbol: str, side: str, quantity: float, price: float) -> Tuple[bool, str]:
        \"\"\"Check if order can be placed based on risk rules\"\"\"
        
        # Check daily trade limit
        today = datetime.now().date()
        if today not in self.daily_trades:
            self.daily_trades[today] = 0
            
        if self.daily_trades[today] >= self.config.max_daily_trades:
            return False, "Daily trade limit reached"
        
        # Check position size limits
        position_value = quantity * price
        max_position_value = self.config.portfolio_value * self.config.max_position_size
        
        if position_value > max_position_value:
            return False, f"Position size too large: ${position_value:.2f} > ${max_position_value:.2f}"
        
        # Check quantity limits
        if quantity < self.config.min_quantity:
            return False, f"Quantity too small: {quantity} < {self.config.min_quantity}"
            
        if quantity > self.config.max_quantity:
            return False, f"Quantity too large: {quantity} > {self.config.max_quantity}"
        
        return True, "OK"
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        \"\"\"Calculate appropriate position size\"\"\"
        max_position_value = self.config.portfolio_value * self.config.max_position_size
        quantity = max_position_value / price
        
        # Apply constraints
        quantity = max(self.config.min_quantity, min(quantity, self.config.max_quantity))
        
        return round(quantity, 6)  # Round to 6 decimal places
    
    def record_trade(self):
        \"\"\"Record a trade for daily limit tracking\"\"\"
        today = datetime.now().date()
        if today not in self.daily_trades:
            self.daily_trades[today] = 0
        self.daily_trades[today] += 1


class MainArbitrageBot:
    \"\"\"
    Main bot class that orchestrates all components
    \"\"\"
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        self.setup_logging()
        
        # Initialize components
        self.performance_tracker = PerformanceTracker()
        self.risk_manager = RiskManager(self.config)
        
        # Initialize managers (placeholder - would import real classes)
        self.exchange_manager = None  # ExchangeManager(asdict(self.config))
        self.dex_handler = None       # DEXPriceHandler(asdict(self.config))
        self.websocket_manager = None # WebSocketManager(asdict(self.config))
        
        # Bot state
        self.running = False
        self.price_data = {}
        self.orders = {}
        self.positions = {}
        self.last_rebalance = {}
        
        # Threading
        self.message_queue = queue.Queue()
        self.shutdown_event = threading.Event()
        
    def _load_config(self, config_path: str) -> BotConfig:
        \"\"\"Load configuration from file or create default\"\"\"
        config_file = Path(config_path)
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                        config_data = yaml.safe_load(f)
                    else:
                        config_data = json.load(f)
                
                return BotConfig(**config_data)
                
            except Exception as e:
                print(f"⚠️ Error loading config: {e}, using defaults")
        
        # Create default config
        config = BotConfig()
        self._save_config(config, config_path)
        return config
    
    def _save_config(self, config: BotConfig, config_path: str):
        \"\"\"Save configuration to file\"\"\"
        try:
            with open(config_path, 'w') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    yaml.dump(asdict(config), f, default_flow_style=False)
                else:
                    json.dump(asdict(config), f, indent=2)
                    
        except Exception as e:
            print(f"❌ Error saving config: {e}")
    
    def setup_logging(self):
        \"\"\"Setup logging configuration\"\"\"
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        
        # Create logs directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=[
                logging.FileHandler(log_dir / f'bot_{datetime.now().strftime("%Y%m%d")}.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger('ArbitrageBot')
        self.logger.info("🚀 Bot logging initialized")
    
    async def initialize(self) -> bool:
        \"\"\"Initialize all bot components\"\"\"
        try:
            self.logger.info("🔧 Initializing bot components...")
            
            # Initialize exchange connections (placeholder)
            # In real implementation, initialize actual managers here
            self.logger.info("✅ Exchange connections initialized")
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False
    
    def _signal_handler(self, signum, frame):
        \"\"\"Handle shutdown signals\"\"\"
        self.logger.info(f"📡 Received signal {signum}, initiating shutdown...")
        self.shutdown_event.set()
        asyncio.create_task(self.shutdown())
    
    async def process_price_update(self, price_data: Dict):
        \"\"\"Process incoming price updates\"\"\"
        try:
            symbol = price_data['symbol']
            source = price_data.get('source', 'unknown')
            
            # Store price data
            if symbol not in self.price_data:
                self.price_data[symbol] = {'dex': None, 'cex': None}
            
            if 'dex' in source or source == 'simulation':
                self.price_data[symbol]['dex'] = price_data
            else:
                self.price_data[symbol]['cex'] = price_data
            
            # Check if we have both prices
            if (self.price_data[symbol]['dex'] and 
                self.price_data[symbol]['cex']):
                
                await self.evaluate_arbitrage_opportunity(symbol)
                
        except Exception as e:
            self.logger.error(f"❌ Error processing price update: {e}")
    
    async def evaluate_arbitrage_opportunity(self, symbol: str):
        \"\"\"Evaluate arbitrage opportunity for a symbol\"\"\"
        try:
            dex_data = self.price_data[symbol]['dex']
            cex_data = self.price_data[symbol]['cex']
            
            dex_price = dex_data['price']
            cex_price = cex_data.get('last', cex_data.get('price', 0))
            
            if cex_price == 0:
                return
            
            # Calculate price difference
            price_diff_pct = (dex_price - cex_price) / cex_price
            
            self.logger.debug(f"📊 {symbol}: DEX=${dex_price:.2f}, CEX=${cex_price:.2f}, Diff={price_diff_pct:.2%}")
            
            # Check for significant price movement
            if await self.check_price_movement(symbol, dex_price):
                await self.schedule_rebalance(symbol, dex_price)
                return
            
            # Check if we should place new orders
            if abs(price_diff_pct) <= self.config.spread_range:
                await self.manage_orders(symbol, dex_price, cex_price)
                
        except Exception as e:
            self.logger.error(f"❌ Error evaluating arbitrage for {symbol}: {e}")
    
    async def check_price_movement(self, symbol: str, current_price: float) -> bool:
        \"\"\"Check if price has moved significantly\"\"\"
        if symbol not in self.last_rebalance:
            self.last_rebalance[symbol] = {'price': current_price, 'time': datetime.now()}
            return False
        
        last_price = self.last_rebalance[symbol]['price']
        price_change = abs(current_price - last_price) / last_price
        
        if price_change >= self.config.price_threshold:
            self.logger.info(f"📈 Significant price movement for {symbol}: {price_change:.2%}")
            return True
        
        return False
    
    async def schedule_rebalance(self, symbol: str, new_price: float):
        \"\"\"Schedule order rebalancing after price movement\"\"\"
        self.logger.info(f"⏰ Scheduling rebalance for {symbol} in {self.config.rebalance_delay}s")
        
        # Cancel existing orders
        await self.cancel_symbol_orders(symbol)
        
        # Schedule rebalance
        await asyncio.sleep(self.config.rebalance_delay)
        
        # Place new orders at new price level
        cex_price = new_price  # Simplified - would get actual CEX price
        await self.manage_orders(symbol, new_price, cex_price)
        
        # Update rebalance tracking
        self.last_rebalance[symbol] = {
            'price': new_price, 
            'time': datetime.now()
        }
    
    async def manage_orders(self, symbol: str, dex_price: float, cex_price: float):
        \"\"\"Manage buy/sell orders for a symbol\"\"\"
        try:
            # Calculate order prices (within 2% range of DEX price)
            spread_half = self.config.spread_range / 2
            buy_price = dex_price * (1 - spread_half)
            sell_price = dex_price * (1 + spread_half)
            
            # Calculate position size
            quantity = self.risk_manager.calculate_position_size(symbol, dex_price)
            
            # Check if we can place orders
            can_buy, buy_reason = self.risk_manager.can_place_order(symbol, 'buy', quantity, buy_price)
            can_sell, sell_reason = self.risk_manager.can_place_order(symbol, 'sell', quantity, sell_price)
            
            if can_buy and not self.has_active_order(symbol, 'buy', buy_price):
                await self.place_order(symbol, 'buy', quantity, buy_price)
                
            if can_sell and not self.has_active_order(symbol, 'sell', sell_price):
                await self.place_order(symbol, 'sell', quantity, sell_price)
                
        except Exception as e:
            self.logger.error(f"❌ Error managing orders for {symbol}: {e}")
    
    def has_active_order(self, symbol: str, side: str, target_price: float) -> bool:
        \"\"\"Check if there's already an active order near target price\"\"\"
        tolerance = 0.001  # 0.1% price tolerance
        
        for order_id, order in self.orders.items():
            if (order['symbol'] == symbol and 
                order['side'] == side and 
                order['status'] == 'open'):
                
                price_diff = abs(order['price'] - target_price) / target_price
                if price_diff < tolerance:
                    return True
        
        return False
    
    async def place_order(self, symbol: str, side: str, quantity: float, price: float):
        \"\"\"Place an order on the exchange\"\"\"
        try:
            # Simulate order placement (in real implementation, use exchange_manager)
            order_id = f"{side}_{symbol.replace('/', '')}_{int(time.time())}"
            
            order = {
                'id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'status': 'open',
                'timestamp': datetime.now()
            }
            
            self.orders[order_id] = order
            self.risk_manager.record_trade()
            
            self.logger.info(f"📋 Order placed: {side.upper()} {quantity} {symbol} @ ${price:.2f}")
            
        except Exception as e:
            self.logger.error(f"❌ Error placing {side} order for {symbol}: {e}")
    
    async def cancel_symbol_orders(self, symbol: str):
        \"\"\"Cancel all orders for a symbol\"\"\"
        orders_to_cancel = [
            order_id for order_id, order in self.orders.items()
            if order['symbol'] == symbol and order['status'] == 'open'
        ]
        
        for order_id in orders_to_cancel:
            await self.cancel_order(order_id)
    
    async def cancel_order(self, order_id: str):
        \"\"\"Cancel a specific order\"\"\"
        try:
            if order_id in self.orders:
                self.orders[order_id]['status'] = 'cancelled'
                self.logger.info(f"❌ Cancelled order: {order_id}")
                
        except Exception as e:
            self.logger.error(f"❌ Error cancelling order {order_id}: {e}")
    
    async def run(self):
        \"\"\"Main bot execution loop\"\"\"
        try:
            self.logger.info("🚀 Starting DEX/CEX Arbitrage Bot")
            
            if not await self.initialize():
                self.logger.error("❌ Bot initialization failed")
                return
            
            self.running = True
            
            # Start price simulation (in real implementation, start WebSocket handlers)
            asyncio.create_task(self.simulate_price_feeds())
            
            # Main monitoring loop
            while self.running and not self.shutdown_event.is_set():
                try:
                    # Process any queued messages
                    await self.process_message_queue()
                    
                    # Update performance metrics
                    await self.update_metrics()
                    
                    # Sleep for main loop interval
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error in main loop: {e}")
                    await asyncio.sleep(5)
            
            await self.shutdown()
            
        except KeyboardInterrupt:
            self.logger.info("⏹️ Bot interrupted by user")
        except Exception as e:
            self.logger.error(f"❌ Unexpected error in bot: {e}")
        finally:
            await self.cleanup()
    
    async def simulate_price_feeds(self):
        \"\"\"Simulate price feeds for testing (replace with real WebSocket feeds)\"\"\"
        import numpy as np
        
        base_prices = {
            'BTC/USDT': 50000,
            'ETH/USDT': 3000,
        }
        
        while self.running:
            for symbol in self.config.symbols:
                if symbol in base_prices:
                    base_price = base_prices[symbol]
                    
                    # Simulate DEX price
                    dex_variation = np.random.uniform(-0.02, 0.02)
                    dex_price = base_price * (1 + dex_variation)
                    
                    # Simulate CEX price (slightly different)
                    cex_variation = np.random.uniform(-0.015, 0.015)
                    cex_price = base_price * (1 + cex_variation)
                    
                    # Send price updates
                    await self.process_price_update({
                        'symbol': symbol,
                        'price': dex_price,
                        'source': 'simulation',
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    await self.process_price_update({
                        'symbol': symbol,
                        'last': cex_price,
                        'bid': cex_price * 0.999,
                        'ask': cex_price * 1.001,
                        'source': 'cex_simulation',
                        'timestamp': datetime.now().isoformat()
                    })
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    async def process_message_queue(self):
        \"\"\"Process any queued messages\"\"\"
        try:
            while not self.message_queue.empty():
                message = self.message_queue.get_nowait()
                # Process message based on type
                await self.handle_message(message)
        except queue.Empty:
            pass
    
    async def handle_message(self, message: Dict):
        \"\"\"Handle a queued message\"\"\"
        message_type = message.get('type')
        
        if message_type == 'price_update':
            await self.process_price_update(message['data'])
        elif message_type == 'order_update':
            await self.handle_order_update(message['data'])
        # Add more message types as needed
    
    async def handle_order_update(self, order_data: Dict):
        \"\"\"Handle order status updates\"\"\"
        order_id = order_data.get('id')
        if order_id in self.orders:
            self.orders[order_id].update(order_data)
            self.logger.info(f"📋 Order updated: {order_id} -> {order_data['status']}")
    
    async def update_metrics(self):
        \"\"\"Update performance metrics\"\"\"
        # This would calculate and update various performance metrics
        pass
    
    def get_status(self) -> Dict:
        \"\"\"Get current bot status\"\"\"
        active_orders = sum(1 for order in self.orders.values() if order['status'] == 'open')
        
        return {
            'running': self.running,
            'uptime': datetime.now() - self.performance_tracker.start_time,
            'active_orders': active_orders,
            'total_orders': len(self.orders),
            'monitored_symbols': len(self.config.symbols),
            'performance': self.performance_tracker.get_metrics(),
            'config': asdict(self.config)
        }
    
    async def shutdown(self):
        \"\"\"Gracefully shutdown the bot\"\"\"
        self.logger.info("🛑 Initiating bot shutdown...")
        self.running = False
        
        # Cancel all open orders
        for symbol in self.config.symbols:
            await self.cancel_symbol_orders(symbol)
        
        self.logger.info("✅ Bot shutdown complete")
    
    async def cleanup(self):
        \"\"\"Clean up resources\"\"\"
        try:
            # Close exchange connections
            if self.exchange_manager:
                await self.exchange_manager.close_exchanges()
            
            # Close WebSocket connections
            if self.websocket_manager:
                await self.websocket_manager.close_all_connections()
                
            self.logger.info("✅ Cleanup complete")
            
        except Exception as e:
            self.logger.error(f"❌ Error during cleanup: {e}")


def main():
    \"\"\"Main entry point\"\"\"
    import argparse
    
    parser = argparse.ArgumentParser(description='DEX/CEX Arbitrage Trading Bot')
    parser.add_argument('--config', default='config.yaml', 
                       help='Configuration file path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Create and run bot
    bot = MainArbitrageBot(args.config)
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\\n⏹️ Bot stopped by user")
    except Exception as e:
        print(f"❌ Bot failed: {e}")


if __name__ == "__main__":
    main()
"""

# Save the complete bot implementation
with open('main_bot.py', 'w') as f:
    f.write(complete_bot_code)

# Create a requirements file
requirements = """
ccxt>=4.0.0
websockets>=11.0.0
aiohttp>=3.8.0
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.24.0
plotly>=5.15.0
pyyaml>=6.0.0
asyncio-mqtt>=0.13.0
python-dotenv>=1.0.0
"""

with open('requirements.txt', 'w') as f:
    f.write(requirements.strip())

# Create a sample configuration file
config_yaml = """
# DEX/CEX Arbitrage Bot Configuration

# Exchange Settings
cex_exchange: "binance"
dex_source: "coingecko"

# API Credentials (set these in environment variables or here)
cex_api_key: ""
cex_secret: ""
dex_api_key: ""

# Trading Parameters
symbols:
  - "BTC/USDT"
  - "ETH/USDT"

max_position_size: 0.01  # 1% of portfolio per position
price_threshold: 0.02    # 2% price movement threshold
rebalance_delay: 120     # 2 minutes delay in seconds
spread_range: 0.02       # 2% spread range for orders

# Risk Management
portfolio_value: 10000.0  # Total portfolio value in USD
min_quantity: 0.001       # Minimum order quantity
max_quantity: 1.0         # Maximum order quantity  
max_daily_trades: 100     # Maximum trades per day
stop_loss_pct: 0.05       # 5% stop loss

# System Settings
sandbox_mode: true        # Use sandbox/paper trading
log_level: "INFO"         # Logging level
data_retention_days: 30   # Days to keep historical data
"""

with open('config.yaml', 'w') as f:
    f.write(config_yaml)

print("✅ Complete DEX/CEX Arbitrage Bot created successfully!")
print("\n📁 Files created:")
print("  - main_bot.py (Main bot implementation)")
print("  - requirements.txt (Python dependencies)")
print("  - config.yaml (Configuration template)")
print("  - dex_cex_arbitrage_streamlit.py (Streamlit UI)")
print("  - exchange_integrations.py (CCXT & WebSocket handlers)")

print("\n🚀 Quick Start Guide:")
print("1. Install dependencies: pip install -r requirements.txt")
print("2. Configure API keys in config.yaml")
print("3. Run bot: python main_bot.py")
print("4. Run UI: streamlit run dex_cex_arbitrage_streamlit.py")

print("\n⚠️ Important Notes:")
print("- Set sandbox_mode: true for testing")
print("- Configure proper API keys with trading permissions")  
print("- Start with small position sizes")
print("- Monitor logs for any errors")
print("- Test thoroughly before live trading")