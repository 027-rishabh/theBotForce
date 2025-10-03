"""
LANDSHARE Market Maker Bot
Implements market making strategy with dual reference price modes (DEX/CEX)
Supports multiple CEX exchanges with post-only orders
"""

import asyncio
import ccxt.async_support as ccxt
import logging
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import yaml

from landshare_token_manager import LANDTokenManager


class MultiCEXManager:
    """
    Manages connections to multiple CEX exchanges
    Supports MEXC, Gate.io, BitMart, AscendEX, and BingX
    """

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.exchanges = {}
        self.selected_exchange = config['cex']['selected_exchange']

    async def initialize(self):
        """Initialize selected CEX exchange"""
        try:
            exchange_name = self.selected_exchange
            api_creds = self.config['api_credentials']

            # Initialize based on selected exchange
            if exchange_name == 'mexc':
                self.exchanges['mexc'] = ccxt.mexc({
                    'apiKey': api_creds.get('mexc_api_key', ''),
                    'secret': api_creds.get('mexc_secret', ''),
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })

            elif exchange_name == 'gateio':
                self.exchanges['gateio'] = ccxt.gateio({
                    'apiKey': api_creds.get('gateio_api_key', ''),
                    'secret': api_creds.get('gateio_secret', ''),
                    'password': api_creds.get('gateio_password', ''),
                    'enableRateLimit': True
                })

            elif exchange_name == 'bitmart':
                self.exchanges['bitmart'] = ccxt.bitmart({
                    'apiKey': api_creds.get('bitmart_api_key', ''),
                    'secret': api_creds.get('bitmart_secret', ''),
                    'uid': api_creds.get('bitmart_uid', ''),
                    'password': api_creds.get('bitmart_memo', ''),  # BitMart uses 'password' for memo
                    'enableRateLimit': True
                })

            elif exchange_name == 'ascendex':
                self.exchanges['ascendex'] = ccxt.ascendex({
                    'apiKey': api_creds.get('ascendex_api_key', ''),
                    'secret': api_creds.get('ascendex_secret', ''),
                    'uid': api_creds.get('ascendex_group_id', ''),  # AscendEX requires group_id as uid
                    'enableRateLimit': True
                })

            elif exchange_name == 'bingx':
                self.exchanges['bingx'] = ccxt.bingx({
                    'apiKey': api_creds.get('bingx_api_key', ''),
                    'secret': api_creds.get('bingx_secret', ''),
                    'enableRateLimit': True
                })

            self.logger.info(f"Initialized {exchange_name} exchange")

        except Exception as e:
            self.logger.error(f"Error initializing CEX exchange: {e}")

    async def close(self):
        """Close all exchange connections"""
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                self.logger.info(f"Closed {name} connection")
            except Exception as e:
                self.logger.error(f"Error closing {name}: {e}")

    async def get_order_book(self, symbol: str) -> Optional[Dict]:
        """Fetch order book from selected CEX"""
        try:
            exchange = self.exchanges[self.selected_exchange]
            order_book = await exchange.fetch_order_book(symbol)

            return {
                'bids': order_book['bids'][:5] if order_book['bids'] else [],
                'asks': order_book['asks'][:5] if order_book['asks'] else [],
                'timestamp': order_book['timestamp']
            }

        except Exception as e:
            self.logger.error(f"Error fetching order book: {e}")
            return None

    async def get_mid_price(self, symbol: str) -> Optional[float]:
        """Calculate mid-price from order book"""
        try:
            order_book = await self.get_order_book(symbol)

            if not order_book or not order_book['bids'] or not order_book['asks']:
                return None

            best_bid = order_book['bids'][0][0]
            best_ask = order_book['asks'][0][0]
            mid_price = (best_bid + best_ask) / 2

            self.logger.debug(f"CEX mid-price: ${mid_price:.6f} (bid: ${best_bid:.6f}, ask: ${best_ask:.6f})")

            return mid_price

        except Exception as e:
            self.logger.error(f"Error calculating mid-price: {e}")
            return None

    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float, post_only: bool = True) -> Optional[Dict]:
        """Place limit order on CEX"""
        try:
            exchange = self.exchanges[self.selected_exchange]

            # Round to exchange precision
            await exchange.load_markets()
            amount = exchange.amount_to_precision(symbol, amount)
            price = exchange.price_to_precision(symbol, price)

            params = {}
            if post_only:
                params['postOnly'] = True

            order = await exchange.create_limit_order(symbol, side, amount, price, params)

            self.logger.info(f"Order placed: {side} {amount} {symbol} @ ${price} [ID: {order['id']}]")

            return order

        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            return None

    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order"""
        try:
            exchange = self.exchanges[self.selected_exchange]
            await exchange.cancel_order(order_id, symbol)
            self.logger.info(f"Order cancelled: {order_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return False

    async def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all open orders for symbol"""
        try:
            exchange = self.exchanges[self.selected_exchange]
            open_orders = await exchange.fetch_open_orders(symbol)

            cancelled_count = 0
            for order in open_orders:
                if await self.cancel_order(order['id'], symbol):
                    cancelled_count += 1

            self.logger.info(f"Cancelled {cancelled_count} orders for {symbol}")
            return cancelled_count

        except Exception as e:
            self.logger.error(f"Error cancelling all orders: {e}")
            return 0

    async def get_balance(self, currency: str) -> Optional[Dict]:
        """Get balance for currency"""
        try:
            exchange = self.exchanges[self.selected_exchange]
            balance = await exchange.fetch_balance()

            if currency in balance:
                return {
                    'free': balance[currency]['free'],
                    'used': balance[currency]['used'],
                    'total': balance[currency]['total']
                }

            return None

        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return None


class ReferencePriceEngine:
    """
    Manages reference price logic with dual-mode switching
    Mode 1: DEX reference (PancakeSwap)
    Mode 2: CEX reference (Selected CEX mid-price)
    """

    def __init__(self, config: Dict, land_manager: LANDTokenManager, cex_manager: MultiCEXManager):
        self.config = config
        self.land_manager = land_manager
        self.cex_manager = cex_manager
        self.logger = logging.getLogger(__name__)

        self.use_dex_reference = config['reference_mode']['use_dex_reference']
        self.trading_pair = config['token']['trading_pair']

    async def get_reference_price(self) -> Optional[float]:
        """
        Get reference price based on current mode
        Returns price in USDT
        """
        try:
            if self.use_dex_reference:
                # Mode 1: Use DEX (PancakeSwap) price
                price = await self.land_manager.get_land_usdt_price()
                self.logger.info(f"Reference price from DEX: ${price:.6f}")
                return price
            else:
                # Mode 2: Use CEX mid-price
                price = await self.cex_manager.get_mid_price(self.trading_pair)
                self.logger.info(f"Reference price from CEX: ${price:.6f}")
                return price

        except Exception as e:
            self.logger.error(f"Error getting reference price: {e}")
            return None

    def switch_mode(self, use_dex: bool):
        """Switch between DEX and CEX reference modes"""
        self.use_dex_reference = use_dex
        mode_name = "DEX" if use_dex else "CEX"
        self.logger.info(f"Switched to {mode_name} reference mode")


class MarketMakerEngine:
    """
    Core market making engine
    Places and manages buy/sell orders around reference price
    """

    def __init__(self, config: Dict, reference_engine: ReferencePriceEngine, cex_manager: MultiCEXManager):
        self.config = config
        self.reference_engine = reference_engine
        self.cex_manager = cex_manager
        self.logger = logging.getLogger(__name__)

        # Market making parameters
        self.spread_pct = config['market_making']['spread_percentage'] / 100
        self.order_amount_usd = config['market_making']['order_amount_usd']
        self.post_only = config['market_making']['post_only']
        self.trading_pair = config['token']['trading_pair']

        # Active orders tracking
        self.active_orders = {'buy': None, 'sell': None}

        # Fill handling
        self.fill_handler = FillHandler(config, self)

    async def calculate_order_prices(self, reference_price: float) -> Tuple[float, float]:
        """
        Calculate buy and sell prices based on reference price and spread
        """
        buy_price = reference_price * (1 - self.spread_pct)
        sell_price = reference_price * (1 + self.spread_pct)

        return buy_price, sell_price

    async def calculate_order_size(self, price: float) -> float:
        """
        Calculate order size based on USD amount
        """
        # Half of total amount per side
        order_value_usd = self.order_amount_usd / 2
        quantity = order_value_usd / price

        return quantity

    async def place_spread_orders(self):
        """
        Place buy and sell orders around reference price
        """
        try:
            # Get reference price
            reference_price = await self.reference_engine.get_reference_price()

            if reference_price is None:
                self.logger.error("Failed to get reference price")
                return False

            # Calculate order prices
            buy_price, sell_price = await self.calculate_order_prices(reference_price)

            # Calculate order sizes
            buy_size = await self.calculate_order_size(buy_price)
            sell_size = await self.calculate_order_size(sell_price)

            # Cancel existing orders
            await self.cex_manager.cancel_all_orders(self.trading_pair)

            # Place new orders
            buy_order = await self.cex_manager.place_limit_order(
                self.trading_pair, 'buy', buy_size, buy_price, self.post_only
            )

            sell_order = await self.cex_manager.place_limit_order(
                self.trading_pair, 'sell', sell_size, sell_price, self.post_only
            )

            # Track active orders
            self.active_orders['buy'] = buy_order
            self.active_orders['sell'] = sell_order

            self.logger.info(f"Spread orders placed - Buy: ${buy_price:.6f}, Sell: ${sell_price:.6f}, Ref: ${reference_price:.6f}")

            return True

        except Exception as e:
            self.logger.error(f"Error placing spread orders: {e}")
            return False

    async def check_fills(self) -> List[Dict]:
        """
        Check if any orders have been filled
        Returns list of filled orders
        """
        filled_orders = []

        try:
            for side, order in self.active_orders.items():
                if order is None:
                    continue

                # Fetch order status
                exchange = self.cex_manager.exchanges[self.cex_manager.selected_exchange]
                updated_order = await exchange.fetch_order(order['id'], self.trading_pair)

                if updated_order['status'] == 'closed' or updated_order['filled'] > 0:
                    filled_orders.append({
                        'side': side,
                        'order': updated_order,
                        'filled_amount': updated_order['filled'],
                        'filled_price': updated_order['average']
                    })

                    self.active_orders[side] = None

            return filled_orders

        except Exception as e:
            self.logger.error(f"Error checking fills: {e}")
            return []


class FillHandler:
    """
    Handles order fills with different logic based on reference mode
    DEX mode: Immediate rebalance
    CEX mode: 2-minute delay before rebalance
    """

    def __init__(self, config: Dict, market_maker: MarketMakerEngine):
        self.config = config
        self.market_maker = market_maker
        self.logger = logging.getLogger(__name__)

        self.dex_mode_delay = config['fill_handling']['dex_mode_delay']
        self.cex_mode_delay = config['fill_handling']['cex_mode_delay']

        self.pending_rebalances = []

    async def handle_fill(self, fill_data: Dict):
        """
        Handle filled order based on reference mode
        """
        try:
            side = fill_data['side']
            filled_amount = fill_data['filled_amount']
            filled_price = fill_data['filled_price']

            self.logger.info(f"Order filled: {side.upper()} {filled_amount} @ ${filled_price:.6f}")

            # Determine delay based on reference mode
            use_dex_reference = self.market_maker.reference_engine.use_dex_reference

            if use_dex_reference:
                # DEX mode: Immediate rebalance
                self.logger.info("DEX mode: Immediate rebalance")
                await self.market_maker.place_spread_orders()
            else:
                # CEX mode: Delayed rebalance
                self.logger.info(f"CEX mode: Rebalance in {self.cex_mode_delay} seconds")
                await asyncio.sleep(self.cex_mode_delay)
                await self.market_maker.place_spread_orders()

        except Exception as e:
            self.logger.error(f"Error handling fill: {e}")


class InventoryManager:
    """
    Manages inventory and implements inventory skew adjustments
    """

    def __init__(self, config: Dict, cex_manager: MultiCEXManager):
        self.config = config
        self.cex_manager = cex_manager
        self.logger = logging.getLogger(__name__)

        self.max_inventory_skew = config['risk_management']['max_inventory_skew']
        self.target_inventory = 0  # Neutral inventory target

    async def get_current_inventory(self) -> float:
        """
        Get current LAND token inventory
        Positive = long, Negative = short
        """
        try:
            balance = await self.cex_manager.get_balance('LAND')

            if balance:
                return balance['total']

            return 0

        except Exception as e:
            self.logger.error(f"Error getting inventory: {e}")
            return 0

    def calculate_inventory_skew(self, current_inventory: float) -> float:
        """
        Calculate inventory skew percentage
        """
        skew = (current_inventory - self.target_inventory) / abs(self.target_inventory) if self.target_inventory != 0 else current_inventory

        return skew

    def should_adjust_quotes(self, skew: float) -> bool:
        """
        Determine if quotes should be adjusted based on inventory
        """
        return abs(skew) > self.max_inventory_skew


# Load configuration and run
async def run_market_maker():
    """
    Main function to run the LANDSHARE market maker bot
    """
    # Load configuration
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    # Setup logging
    logging.basicConfig(
        level=config['system']['log_level'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)
    logger.info("Starting LANDSHARE Market Maker Bot")

    # Initialize components
    land_manager = LANDTokenManager(config)
    cex_manager = MultiCEXManager(config)

    await land_manager.initialize()
    await cex_manager.initialize()

    # Create engines
    reference_engine = ReferencePriceEngine(config, land_manager, cex_manager)
    market_maker = MarketMakerEngine(config, reference_engine, cex_manager)

    try:
        # Main trading loop
        refresh_interval = config['market_making']['refresh_interval']

        while True:
            # Place/refresh orders
            await market_maker.place_spread_orders()

            # Check for fills
            fills = await market_maker.check_fills()

            # Handle fills
            for fill in fills:
                await market_maker.fill_handler.handle_fill(fill)

            # Wait for next refresh
            await asyncio.sleep(refresh_interval)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await land_manager.close()
        await cex_manager.close()


if __name__ == "__main__":
    asyncio.run(run_market_maker())
