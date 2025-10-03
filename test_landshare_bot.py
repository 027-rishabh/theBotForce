"""
LANDSHARE Market Maker Bot - Test/Simulation Mode
Runs the bot with simulated price data for testing without API dependencies
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import Dict, Optional


class SimulatedLANDTokenManager:
    """Simulated LAND token manager for testing"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.base_price = 0.38  # Base LAND price in USDT

    async def initialize(self):
        self.logger.info("Simulated LAND Token Manager initialized")

    async def close(self):
        self.logger.info("Simulated LAND Token Manager closed")

    async def get_land_usdt_price(self) -> float:
        """Return simulated LAND/USDT price with realistic variation"""
        variation = random.uniform(-0.02, 0.02)  # ±2% variation
        price = self.base_price * (1 + variation)

        # Simulate BNB conversion for logging
        land_bnb = price / 1107  # Simulated BNB price

        self.logger.info(
            f"LAND/USDT price: ${price:.6f} "
            f"(Simulated BNB: {land_bnb:.8f}, BNB/USDT: $1107.00)"
        )

        return price

    async def get_order_book_data(self) -> Dict:
        """Return simulated order book data"""
        price = await self.get_land_usdt_price()
        spread = 0.001  # 0.1% spread

        return {
            'bid': price * (1 - spread / 2),
            'ask': price * (1 + spread / 2),
            'mid': price,
            'spread': spread,
            'timestamp': datetime.now().isoformat()
        }


class SimulatedCEXManager:
    """Simulated CEX manager for testing"""

    def __init__(self, exchange_name: str = "mexc"):
        self.logger = logging.getLogger(__name__)
        self.exchange_name = exchange_name
        self.orders = {}
        self.order_counter = 1000

    async def initialize(self):
        self.logger.info(f"Simulated {self.exchange_name} exchange initialized")

    async def close(self):
        self.logger.info(f"Simulated {self.exchange_name} connection closed")

    async def get_mid_price(self, symbol: str) -> float:
        """Return simulated mid-price"""
        base_price = 0.38
        variation = random.uniform(-0.01, 0.01)
        mid_price = base_price * (1 + variation)

        bid = mid_price * 0.999
        ask = mid_price * 1.001

        self.logger.debug(
            f"CEX mid-price: ${mid_price:.6f} "
            f"(bid: ${bid:.6f}, ask: ${ask:.6f})"
        )

        return mid_price

    async def place_limit_order(self, symbol: str, side: str, amount: float,
                                price: float, post_only: bool = True) -> Dict:
        """Place simulated order"""
        order_id = f"SIM_{self.order_counter}"
        self.order_counter += 1

        order = {
            'id': order_id,
            'symbol': symbol,
            'side': side,
            'amount': amount,
            'price': price,
            'status': 'open',
            'filled': 0,
            'timestamp': datetime.now().isoformat()
        }

        self.orders[order_id] = order

        self.logger.info(
            f"Order placed: {side.upper()} {amount:.2f} {symbol} @ "
            f"${price:.6f} [ID: {order_id}]"
        )

        return order

    async def cancel_all_orders(self, symbol: str) -> int:
        """Cancel all simulated orders"""
        cancelled = 0
        for order_id, order in list(self.orders.items()):
            if order['symbol'] == symbol and order['status'] == 'open':
                order['status'] = 'cancelled'
                cancelled += 1

        if cancelled > 0:
            self.logger.info(f"Cancelled {cancelled} orders for {symbol}")

        return cancelled

    async def check_fills(self) -> list:
        """Simulate random order fills"""
        fills = []

        for order_id, order in self.orders.items():
            if order['status'] == 'open':
                # 10% chance of fill per check
                if random.random() < 0.1:
                    order['status'] = 'closed'
                    order['filled'] = order['amount']
                    order['average'] = order['price']

                    fills.append({
                        'side': order['side'],
                        'order': order,
                        'filled_amount': order['amount'],
                        'filled_price': order['price']
                    })

        return fills


class SimulatedMarketMaker:
    """Simulated market maker for testing"""

    def __init__(self, use_dex_reference: bool = True):
        self.logger = logging.getLogger(__name__)
        self.land_manager = SimulatedLANDTokenManager()
        self.cex_manager = SimulatedCEXManager("mexc")
        self.use_dex_reference = use_dex_reference

        # Configuration
        self.spread_pct = 0.015  # 1.5%
        self.order_amount_usd = 1000
        self.trading_pair = "LAND/USDT"

        # State tracking
        self.active_orders = {'buy': None, 'sell': None}
        self.fills_count = 0
        self.total_profit = 0

    async def initialize(self):
        """Initialize components"""
        await self.land_manager.initialize()
        await self.cex_manager.initialize()

    async def close(self):
        """Close components"""
        await self.land_manager.close()
        await self.cex_manager.close()

    async def get_reference_price(self) -> float:
        """Get reference price based on mode"""
        if self.use_dex_reference:
            price = await self.land_manager.get_land_usdt_price()
            self.logger.info(f"Reference price from DEX: ${price:.6f}")
        else:
            price = await self.cex_manager.get_mid_price(self.trading_pair)
            self.logger.info(f"Reference price from CEX: ${price:.6f}")

        return price

    async def place_spread_orders(self):
        """Place buy and sell orders around reference price"""
        # Get reference price
        ref_price = await self.get_reference_price()

        # Calculate order prices
        buy_price = ref_price * (1 - self.spread_pct)
        sell_price = ref_price * (1 + self.spread_pct)

        # Calculate order sizes
        order_value_usd = self.order_amount_usd / 2
        buy_size = order_value_usd / buy_price
        sell_size = order_value_usd / sell_price

        # Cancel existing orders
        await self.cex_manager.cancel_all_orders(self.trading_pair)

        # Place new orders
        buy_order = await self.cex_manager.place_limit_order(
            self.trading_pair, 'buy', buy_size, buy_price, True
        )

        sell_order = await self.cex_manager.place_limit_order(
            self.trading_pair, 'sell', sell_size, sell_price, True
        )

        self.active_orders['buy'] = buy_order
        self.active_orders['sell'] = sell_order

        self.logger.info(
            f"Spread orders placed - Buy: ${buy_price:.6f}, "
            f"Sell: ${sell_price:.6f}, Ref: ${ref_price:.6f}"
        )

    async def handle_fill(self, fill_data: Dict):
        """Handle filled order based on mode"""
        side = fill_data['side']
        filled_amount = fill_data['filled_amount']
        filled_price = fill_data['filled_price']

        self.fills_count += 1

        # Calculate simulated profit
        profit = filled_amount * filled_price * 0.003  # 0.3% profit estimate
        self.total_profit += profit

        self.logger.info(
            f"Order filled: {side.upper()} {filled_amount:.2f} @ "
            f"${filled_price:.6f} (Est. profit: ${profit:.2f})"
        )

        # Rebalance based on mode
        if self.use_dex_reference:
            self.logger.info("DEX mode: Immediate rebalance")
            await self.place_spread_orders()
        else:
            delay = 120
            self.logger.info(f"CEX mode: Rebalance in {delay} seconds")
            await asyncio.sleep(delay)
            await self.place_spread_orders()

    async def run_cycle(self):
        """Run one trading cycle"""
        # Place spread orders
        await self.place_spread_orders()

        # Check for fills
        fills = await self.cex_manager.check_fills()

        # Handle fills
        for fill in fills:
            await self.handle_fill(fill)

    async def run(self, cycles: int = 10):
        """Run the market maker for specified cycles"""
        await self.initialize()

        try:
            mode = "DEX" if self.use_dex_reference else "CEX"
            self.logger.info(f"Starting LANDSHARE Market Maker - {mode} Reference Mode")
            self.logger.info(f"Running {cycles} cycles with 10-second intervals")

            for cycle in range(1, cycles + 1):
                print(f"\n{'='*60}")
                print(f"Cycle {cycle}/{cycles}")
                print(f"{'='*60}")

                await self.run_cycle()

                # Status summary
                print(f"\nCycle Summary:")
                print(f"  Fills: {self.fills_count}")
                print(f"  Total Profit: ${self.total_profit:.2f}")
                print(f"  Reference Mode: {mode}")

                if cycle < cycles:
                    print(f"\nWaiting 10 seconds for next cycle...")
                    await asyncio.sleep(10)

            # Final summary
            print(f"\n{'='*60}")
            print(f"Test Complete")
            print(f"{'='*60}")
            print(f"Total Cycles: {cycles}")
            print(f"Total Fills: {self.fills_count}")
            print(f"Total Profit: ${self.total_profit:.2f}")
            print(f"Avg Profit/Fill: ${self.total_profit/self.fills_count:.2f}" if self.fills_count > 0 else "N/A")

        finally:
            await self.close()


async def main():
    """Main test function"""
    print("LANDSHARE Market Maker Bot - Test Mode\n")
    print("Choose test mode:")
    print("1. DEX Reference Mode (Immediate rebalance)")
    print("2. CEX Reference Mode (2-minute delay)")
    print("3. Quick test (5 cycles, DEX mode)")

    try:
        choice = input("\nSelect option (1-3) [3]: ").strip() or "3"

        if choice == "1":
            use_dex = True
            cycles = int(input("Number of cycles [10]: ").strip() or "10")
        elif choice == "2":
            use_dex = False
            cycles = int(input("Number of cycles [10]: ").strip() or "10")
        else:
            use_dex = True
            cycles = 5

        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # Run market maker
        market_maker = SimulatedMarketMaker(use_dex_reference=use_dex)
        await market_maker.run(cycles)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
