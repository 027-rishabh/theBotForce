#!/usr/bin/env python3
"""
DEX/CEX Arbitrage Trading Bot - Main Entry Point
Automated trading bot for exploiting price differences between DEX and CEX
"""

import os
import sys
import asyncio
import logging
import argparse
import yaml
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Import bot components
from exchange_integrations import ExchangeManager, DEXPriceHandler, WebSocketManager


class DEXCEXArbitrageBot:
    """
    Main trading bot that monitors DEX/CEX price differences and executes arbitrage strategy

    Strategy:
    1. Monitor DEX and CEX prices in real-time
    2. Place buy and sell orders on CEX within 2% range of DEX price
    3. Detect 2% price movements on DEX
    4. Wait 2 minutes after price movement
    5. Rebalance orders to new price levels
    """

    def __init__(self, config: Dict):
        self.config = config
        self.running = False

        # Initialize managers
        self.exchange_manager = ExchangeManager(config)
        self.dex_handler = DEXPriceHandler(config)
        self.websocket_manager = WebSocketManager(config)

        # Trading state
        self.active_orders = {}  # {symbol: {'buy': order_id, 'sell': order_id}}
        self.last_prices = {}    # {symbol: {'dex': price, 'cex': price, 'timestamp': dt}}
        self.rebalance_timers = {}  # {symbol: timer_task}

        # Strategy parameters
        self.price_threshold = config.get('price_threshold', 0.02)  # 2%
        self.rebalance_delay = config.get('rebalance_delay', 120)   # 2 minutes
        self.spread_range = config.get('spread_range', 0.02)        # 2%
        self.max_position_size = config.get('max_position_size', 0.01)  # 1%

        # Setup logging
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for the bot"""
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        log_level = self.config.get('log_level', 'INFO')
        log_file = log_dir / f"bot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )

        logger = logging.getLogger('DEXCEXBot')
        logger.info(f"📝 Logging initialized - Level: {log_level}")
        logger.info(f"📁 Log file: {log_file}")

        return logger

    async def initialize(self) -> bool:
        """Initialize exchange connections and data feeds"""
        try:
            self.logger.info("🚀 Initializing DEX/CEX Arbitrage Bot...")

            # Initialize CEX exchange
            cex_exchange = self.config.get('cex_exchange', 'binance')
            api_key = self.config.get('cex_api_key', '')
            secret = self.config.get('cex_secret', '')
            sandbox = self.config.get('sandbox_mode', True)

            if not api_key or not secret:
                self.logger.warning("⚠️  No API keys provided - running in simulation mode")

            success = self.exchange_manager.initialize_cex_exchange(
                cex_exchange, api_key, secret, sandbox
            )

            if not success:
                self.logger.error("❌ Failed to initialize CEX exchange")
                return False

            # Register price update callbacks
            self.dex_handler.add_price_callback(self.on_dex_price_update)
            self.websocket_manager.add_message_handler('ticker', self.on_cex_price_update)

            self.logger.info("✅ Bot initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"❌ Initialization failed: {e}")
            return False

    async def on_dex_price_update(self, price_data: Dict):
        """Handle DEX price updates"""
        try:
            symbol = price_data['symbol']
            dex_price = price_data['price']

            # Update price tracking
            if symbol not in self.last_prices:
                self.last_prices[symbol] = {}

            old_dex_price = self.last_prices[symbol].get('dex')
            self.last_prices[symbol]['dex'] = dex_price
            self.last_prices[symbol]['dex_timestamp'] = datetime.now()

            # Check for significant price movement
            if old_dex_price:
                price_change = abs(dex_price - old_dex_price) / old_dex_price

                if price_change >= self.price_threshold:
                    self.logger.info(f"📈 Significant price movement detected for {symbol}: {price_change:.2%}")
                    await self.schedule_rebalance(symbol, dex_price)

            # Check if we should place/update orders
            await self.manage_orders(symbol)

        except Exception as e:
            self.logger.error(f"❌ Error processing DEX price update: {e}")

    async def on_cex_price_update(self, price_data: Dict):
        """Handle CEX price updates"""
        try:
            symbol = price_data['symbol']

            if symbol not in self.last_prices:
                self.last_prices[symbol] = {}

            self.last_prices[symbol]['cex'] = price_data['last']
            self.last_prices[symbol]['cex_bid'] = price_data.get('bid')
            self.last_prices[symbol]['cex_ask'] = price_data.get('ask')
            self.last_prices[symbol]['cex_timestamp'] = datetime.now()

        except Exception as e:
            self.logger.error(f"❌ Error processing CEX price update: {e}")

    async def manage_orders(self, symbol: str):
        """Manage orders for a symbol based on current prices"""
        try:
            # Get current prices
            if symbol not in self.last_prices:
                return

            price_info = self.last_prices[symbol]
            dex_price = price_info.get('dex')
            cex_price = price_info.get('cex')

            if not dex_price or not cex_price:
                return

            # Calculate price difference
            price_diff = abs(dex_price - cex_price) / cex_price

            # Only place orders if prices are within acceptable range
            if price_diff > self.spread_range:
                self.logger.debug(f"⏸️  Price difference too large for {symbol}: {price_diff:.2%}")
                return

            # Calculate order prices
            buy_price = dex_price * (1 - self.spread_range / 2)   # 1% below DEX
            sell_price = dex_price * (1 + self.spread_range / 2)  # 1% above DEX

            # Calculate position size
            quantity = self.calculate_position_size(symbol, dex_price)

            # Check if we already have orders at these prices
            if await self.has_active_orders(symbol, buy_price, sell_price):
                return

            # Place new orders
            await self.place_spread_orders(symbol, buy_price, sell_price, quantity)

        except Exception as e:
            self.logger.error(f"❌ Error managing orders for {symbol}: {e}")

    async def place_spread_orders(self, symbol: str, buy_price: float, sell_price: float, quantity: float):
        """Place buy and sell orders on CEX"""
        try:
            # Cancel existing orders for this symbol
            await self.cancel_symbol_orders(symbol)

            cex_exchange = self.config.get('cex_exchange', 'binance')

            # Place buy order
            buy_order = await self.exchange_manager.place_limit_order(
                cex_exchange, symbol, 'buy', quantity, buy_price
            )

            # Place sell order
            sell_order = await self.exchange_manager.place_limit_order(
                cex_exchange, symbol, 'sell', quantity, sell_price
            )

            if buy_order and sell_order:
                self.active_orders[symbol] = {
                    'buy': buy_order,
                    'sell': sell_order,
                    'timestamp': datetime.now()
                }

                self.logger.info(f"📊 Orders placed for {symbol}:")
                self.logger.info(f"   🟢 BUY:  {quantity} @ ${buy_price:.2f}")
                self.logger.info(f"   🔴 SELL: {quantity} @ ${sell_price:.2f}")

        except Exception as e:
            self.logger.error(f"❌ Error placing spread orders for {symbol}: {e}")

    async def cancel_symbol_orders(self, symbol: str):
        """Cancel all orders for a symbol"""
        try:
            if symbol not in self.active_orders:
                return

            cex_exchange = self.config.get('cex_exchange', 'binance')
            orders = self.active_orders[symbol]

            # Cancel buy order
            if 'buy' in orders:
                await self.exchange_manager.cancel_order(
                    cex_exchange, orders['buy']['id'], symbol
                )

            # Cancel sell order
            if 'sell' in orders:
                await self.exchange_manager.cancel_order(
                    cex_exchange, orders['sell']['id'], symbol
                )

            # Remove from active orders
            del self.active_orders[symbol]

        except Exception as e:
            self.logger.error(f"❌ Error cancelling orders for {symbol}: {e}")

    async def has_active_orders(self, symbol: str, target_buy: float, target_sell: float) -> bool:
        """Check if we already have orders at similar price levels"""
        if symbol not in self.active_orders:
            return False

        orders = self.active_orders[symbol]
        tolerance = 0.001  # 0.1% tolerance

        buy_order = orders.get('buy')
        sell_order = orders.get('sell')

        if buy_order and sell_order:
            buy_price = buy_order['price']
            sell_price = sell_order['price']

            buy_close = abs(buy_price - target_buy) / target_buy < tolerance
            sell_close = abs(sell_price - target_sell) / target_sell < tolerance

            return buy_close and sell_close

        return False

    async def schedule_rebalance(self, symbol: str, new_price: float):
        """Schedule order rebalancing after delay"""
        try:
            # Cancel existing rebalance timer if any
            if symbol in self.rebalance_timers:
                self.rebalance_timers[symbol].cancel()

            self.logger.info(f"⏰ Scheduling rebalance for {symbol} in {self.rebalance_delay} seconds")

            # Create rebalance task
            async def rebalance():
                await asyncio.sleep(self.rebalance_delay)
                self.logger.info(f"🔄 Rebalancing orders for {symbol}")
                await self.manage_orders(symbol)

            # Schedule the task
            task = asyncio.create_task(rebalance())
            self.rebalance_timers[symbol] = task

        except Exception as e:
            self.logger.error(f"❌ Error scheduling rebalance for {symbol}: {e}")

    def calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate position size based on risk management rules"""
        portfolio_value = self.config.get('portfolio_value', 10000.0)
        max_position_value = portfolio_value * self.max_position_size

        quantity = max_position_value / price

        # Apply min/max constraints
        min_qty = self.config.get('min_quantity', 0.001)
        max_qty = self.config.get('max_quantity', 1.0)

        return max(min_qty, min(quantity, max_qty))

    async def run(self):
        """Main bot execution loop"""
        try:
            if not await self.initialize():
                self.logger.error("❌ Failed to initialize bot")
                return

            self.running = True
            symbols = self.config.get('symbols', ['BTC/USDT', 'ETH/USDT'])

            self.logger.info(f"🤖 Bot started - Monitoring {len(symbols)} symbols: {symbols}")

            # Start data feeds
            dex_source = self.config.get('dex_source', 'coingecko')
            cex_exchange = self.config.get('cex_exchange', 'binance')

            # Run concurrently
            await asyncio.gather(
                self.dex_handler.connect_dex_websocket(dex_source, symbols),
                self.websocket_manager.connect_exchange_websocket(cex_exchange, symbols),
                self.monitoring_loop()
            )

        except asyncio.CancelledError:
            self.logger.info("⏹️  Bot execution cancelled")
        except Exception as e:
            self.logger.error(f"❌ Error in main run loop: {e}")
        finally:
            await self.shutdown()

    async def monitoring_loop(self):
        """Periodic monitoring and health checks"""
        while self.running:
            try:
                # Log status
                self.logger.info(f"📊 Status: {len(self.active_orders)} active symbols")

                # Wait before next check
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                self.logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(10)

    async def shutdown(self):
        """Gracefully shutdown the bot"""
        self.logger.info("🛑 Shutting down bot...")
        self.running = False

        # Cancel all rebalance timers
        for task in self.rebalance_timers.values():
            task.cancel()

        # Cancel all active orders
        for symbol in list(self.active_orders.keys()):
            await self.cancel_symbol_orders(symbol)

        # Close exchange connections
        await self.exchange_manager.close_exchanges()
        await self.websocket_manager.close_all_connections()

        self.logger.info("✅ Bot shutdown complete")


def load_config(config_file: str) -> Dict:
    """Load configuration from YAML file"""
    try:
        # Load environment variables
        load_dotenv()

        # Load config file
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        # Override with environment variables if present
        config['cex_api_key'] = os.getenv('CEX_API_KEY', config.get('cex_api_key', ''))
        config['cex_secret'] = os.getenv('CEX_SECRET', config.get('cex_secret', ''))
        config['dex_api_key'] = os.getenv('DEX_API_KEY', config.get('dex_api_key', ''))

        return config

    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='DEX/CEX Arbitrage Trading Bot'
    )
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Override log level from config'
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    # Override log level if specified
    if args.log_level:
        config['log_level'] = args.log_level

    # Create bot instance
    bot = DEXCEXArbitrageBot(config)

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler(sig, frame):
        print("\n⚠️  Shutdown signal received...")
        loop.create_task(bot.shutdown())
        loop.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run the bot
    try:
        loop.run_until_complete(bot.run())
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")
    finally:
        loop.close()


if __name__ == "__main__":
    main()
