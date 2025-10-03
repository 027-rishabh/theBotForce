#!/usr/bin/env python3
"""
DEX/CEX Arbitrage Bot Demo Script
Quick demonstration of bot functionality without real trading
"""

import asyncio
import json
from datetime import datetime
import random
import time

class BotDemo:
    def __init__(self):
        self.running = False
        self.demo_data = {
            'BTC/USDT': {'dex': 50000, 'cex': 50100},
            'ETH/USDT': {'dex': 3000, 'cex': 3010}
        }
        self.orders = []
        self.price_movements = 0

    def print_banner(self):
        print("""
╔════════════════════════════════════════════════╗
║      DEX/CEX Arbitrage Bot Demo 🤖              ║
║      Simulated Trading Environment             ║
╚════════════════════════════════════════════════╝
        """)

    def simulate_price_update(self, symbol):
        """Simulate price changes"""
        # Random price movement
        dex_change = random.uniform(-0.03, 0.03)  # ±3%
        cex_change = random.uniform(-0.025, 0.025)  # ±2.5%

        base_dex = self.demo_data[symbol]['dex']
        base_cex = self.demo_data[symbol]['cex']

        new_dex_price = base_dex * (1 + dex_change)
        new_cex_price = base_cex * (1 + cex_change)

        self.demo_data[symbol] = {
            'dex': new_dex_price,
            'cex': new_cex_price
        }

        return new_dex_price, new_cex_price

    def check_arbitrage_opportunity(self, symbol, dex_price, cex_price):
        """Check if arbitrage opportunity exists"""
        price_diff_pct = (dex_price - cex_price) / cex_price

        # Check if within 2% range
        if abs(price_diff_pct) <= 0.02:  # Within 2% range
            return True, price_diff_pct

        return False, price_diff_pct

    def calculate_order_prices(self, dex_price):
        """Calculate buy/sell order prices"""
        spread = 0.02  # 2% spread
        buy_price = dex_price * (1 - spread/2)   # 1% below DEX
        sell_price = dex_price * (1 + spread/2)  # 1% above DEX

        return buy_price, sell_price

    def place_simulated_order(self, symbol, side, quantity, price):
        """Place a simulated order"""
        order = {
            'id': f"{side}_{symbol.replace('/', '')}_{int(time.time())}",
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'status': 'open',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }

        self.orders.append(order)
        return order

    def check_price_movement(self, symbol, current_price, threshold=0.02):
        """Check for significant price movement"""
        # Simulate random significant movements
        if random.random() < 0.1:  # 10% chance of significant movement
            self.price_movements += 1
            return True
        return False

    async def run_demo_cycle(self):
        """Run one demo cycle"""
        for symbol in self.demo_data.keys():
            # Simulate new prices
            dex_price, cex_price = self.simulate_price_update(symbol)

            # Display current prices
            price_diff = (dex_price - cex_price) / cex_price * 100
            print(f"\n📊 {symbol}:")
            print(f"   DEX: ${dex_price:8.2f}")
            print(f"   CEX: ${cex_price:8.2f}")
            print(f"   Diff: {price_diff:+6.2f}%")

            # Check for arbitrage opportunity
            can_arbitrage, diff_pct = self.check_arbitrage_opportunity(symbol, dex_price, cex_price)

            if can_arbitrage:
                print(f"   ✅ Arbitrage opportunity detected!")

                # Calculate order prices
                buy_price, sell_price = self.calculate_order_prices(dex_price)
                quantity = 0.01  # Demo quantity

                # Place orders
                buy_order = self.place_simulated_order(symbol, 'BUY', quantity, buy_price)
                sell_order = self.place_simulated_order(symbol, 'SELL', quantity, sell_price)

                print(f"   📋 Orders placed:")
                print(f"      🟢 BUY:  {quantity} @ ${buy_price:8.2f}")
                print(f"      🔴 SELL: {quantity} @ ${sell_price:8.2f}")

            else:
                print(f"   ⏸️  Price difference too large: {diff_pct:.2%}")

            # Check for price movement
            if self.check_price_movement(symbol, dex_price):
                print(f"   📈 Significant price movement detected!")
                print(f"   ⏰ Scheduling rebalance in 2 minutes...")
                # In real bot, this would trigger rebalancing

        # Show order summary
        open_orders = [o for o in self.orders if o['status'] == 'open']
        if open_orders:
            print(f"\n📋 Active Orders: {len(open_orders)}")
            for order in open_orders[-3:]:  # Show last 3 orders
                print(f"   {order['side']:4} {order['symbol']:8} @ ${order['price']:8.2f} [{order['timestamp']}]")

    async def run_demo(self, cycles=10):
        """Run the demo for specified cycles"""
        self.print_banner()

        print(f"🚀 Starting demo simulation...")
        print(f"📊 Will run for {cycles} cycles (about {cycles*3} seconds)")
        print(f"💡 This simulates the bot's trading logic without real trades\n")

        self.running = True

        try:
            for cycle in range(1, cycles + 1):
                print(f"\n{'='*50}")
                print(f"Demo Cycle {cycle}/{cycles}")
                print(f"{'='*50}")

                await self.run_demo_cycle()

                # Summary stats
                open_orders = len([o for o in self.orders if o['status'] == 'open'])
                print(f"\n📈 Cycle Summary:")
                print(f"   Active orders: {open_orders}")
                print(f"   Total orders placed: {len(self.orders)}")
                print(f"   Price movements detected: {self.price_movements}")

                if cycle < cycles:
                    print("\n⏳ Waiting 3 seconds for next cycle...")
                    await asyncio.sleep(3)

        except KeyboardInterrupt:
            print("\n\n⏹️ Demo stopped by user")

        self.print_final_summary()

    def print_final_summary(self):
        """Print final demo summary"""
        print("""
╔════════════════════════════════════════════════╗
║              Demo Complete! 🎉                 ║
╚════════════════════════════════════════════════╝

📊 Demo Statistics:
""")

        open_orders = len([o for o in self.orders if o['status'] == 'open'])
        buy_orders = len([o for o in self.orders if o['side'] == 'BUY'])
        sell_orders = len([o for o in self.orders if o['side'] == 'SELL'])

        print(f"   Total orders placed: {len(self.orders)}")
        print(f"   Active orders: {open_orders}")
        print(f"   Buy orders: {buy_orders}")
        print(f"   Sell orders: {sell_orders}")
        print(f"   Price movements: {self.price_movements}")

        print("""
💡 What you just saw:
   - Real-time price monitoring simulation
   - Arbitrage opportunity detection
   - Automatic order placement within 2% spread
   - Price movement detection and rebalancing logic

🚀 Ready to run the real bot?
   1. Configure your API keys in config.yaml
   2. Set sandbox_mode: true for paper trading
   3. Run: python main_bot.py
   4. Monitor with: streamlit run dex_cex_arbitrage_streamlit.py

⚠️  Remember:
   - This was just a simulation
   - Real trading involves financial risk
   - Always test with paper trading first
   - Start with small position sizes

Happy trading! 🤖📈
        """)

async def main():
    demo = BotDemo()

    print("Welcome to the DEX/CEX Arbitrage Bot Demo!")
    print("\nOptions:")
    print("1. Quick demo (5 cycles)")
    print("2. Standard demo (10 cycles)")
    print("3. Extended demo (20 cycles)")
    print("4. Custom cycles")

    try:
        choice = input("\nSelect option (1-4) [2]: ").strip() or "2"

        cycles_map = {'1': 5, '2': 10, '3': 20}

        if choice in cycles_map:
            cycles = cycles_map[choice]
        elif choice == '4':
            cycles = int(input("Enter number of cycles: "))
        else:
            cycles = 10

        await demo.run_demo(cycles)

    except (ValueError, KeyboardInterrupt):
        print("\n⏹️ Demo cancelled")
    except Exception as e:
        print(f"\n❌ Demo error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
