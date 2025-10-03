# Create the core trading bot implementation for DEX/CEX arbitrage
import os
import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

# Core trading bot class
class DEXCEXArbitrageBot:
    def __init__(self, config: Dict):
        """
        Initialize the DEX/CEX arbitrage bot
        
        Args:
            config: Configuration dictionary containing exchange settings, API keys, etc.
        """
        self.config = config
        self.running = False
        self.positions = {}
        self.orders = {}
        self.price_data = {}
        self.last_price_movement = {}
        self.order_shift_timers = {}
        
        # Risk management parameters
        self.max_position_size = config.get('max_position_size', 0.01)  # Max 1% of portfolio per position
        self.price_threshold = config.get('price_threshold', 0.02)  # 2% price movement threshold
        self.rebalance_delay = config.get('rebalance_delay', 120)  # 2 minutes wait time
        self.spread_range = config.get('spread_range', 0.02)  # 2% range for order placement
        
        # Initialize exchange connections (placeholder for CCXT integration)
        self.cex_exchange = None
        self.dex_price_source = None
        
        print("✅ DEX/CEX Arbitrage Bot initialized successfully")
    
    def connect_exchanges(self):
        """Connect to CEX and DEX data sources"""
        try:
            # This would integrate with CCXT for CEX connectivity
            # For now, we'll simulate the connection
            print("🔗 Connecting to exchanges...")
            
            # CEX connection simulation
            cex_config = {
                'apiKey': self.config.get('cex_api_key', ''),
                'secret': self.config.get('cex_secret', ''),
                'sandbox': self.config.get('sandbox_mode', True),
                'enableRateLimit': True
            }
            
            # DEX connection simulation (would use WebSocket APIs)
            dex_config = {
                'websocket_url': self.config.get('dex_websocket_url', ''),
                'api_key': self.config.get('dex_api_key', '')
            }
            
            print("✅ Connected to exchanges successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error connecting to exchanges: {e}")
            return False
    
    def get_dex_price(self, symbol: str) -> Optional[float]:
        """Get current DEX price for a symbol"""
        try:
            # Simulate DEX price fetching
            # In real implementation, this would connect to DEX APIs or WebSocket feeds
            base_price = 50000.0  # Simulate BTC price
            variation = np.random.uniform(-0.05, 0.05)  # ±5% variation
            current_price = base_price * (1 + variation)
            
            return current_price
            
        except Exception as e:
            print(f"❌ Error fetching DEX price for {symbol}: {e}")
            return None
    
    def get_cex_price(self, symbol: str) -> Optional[Dict]:
        """Get current CEX price and order book"""
        try:
            # Simulate CEX price fetching
            dex_price = self.get_dex_price(symbol)
            if not dex_price:
                return None
                
            # Simulate slight CEX price difference
            price_diff = np.random.uniform(-0.01, 0.01)  # ±1% difference
            cex_price = dex_price * (1 + price_diff)
            
            return {
                'bid': cex_price * 0.999,  # Slightly lower bid
                'ask': cex_price * 1.001,  # Slightly higher ask
                'last': cex_price
            }
            
        except Exception as e:
            print(f"❌ Error fetching CEX price for {symbol}: {e}")
            return None
    
    def calculate_price_difference(self, dex_price: float, cex_price: float) -> float:
        """Calculate percentage price difference between DEX and CEX"""
        if cex_price == 0:
            return 0
        return (dex_price - cex_price) / cex_price
    
    def should_place_orders(self, symbol: str, dex_price: float, cex_data: Dict) -> bool:
        """Determine if orders should be placed based on price conditions"""
        price_diff = self.calculate_price_difference(dex_price, cex_data['last'])
        
        # Check if price difference is within acceptable range
        if abs(price_diff) <= self.spread_range:
            return True
        
        return False
    
    def calculate_order_prices(self, dex_price: float) -> Tuple[float, float]:
        """Calculate buy and sell order prices within 2% range of DEX price"""
        # Buy order slightly below DEX price
        buy_price = dex_price * (1 - self.spread_range / 2)
        
        # Sell order slightly above DEX price  
        sell_price = dex_price * (1 + self.spread_range / 2)
        
        return buy_price, sell_price
    
    def place_cex_orders(self, symbol: str, buy_price: float, sell_price: float, quantity: float):
        """Place buy and sell orders on CEX"""
        try:
            # Cancel existing orders for this symbol
            self.cancel_existing_orders(symbol)
            
            # Simulate order placement
            buy_order_id = f"buy_{symbol}_{int(time.time())}"
            sell_order_id = f"sell_{symbol}_{int(time.time())}"
            
            # Store order information
            self.orders[buy_order_id] = {
                'symbol': symbol,
                'side': 'buy',
                'price': buy_price,
                'quantity': quantity,
                'status': 'open',
                'timestamp': datetime.now()
            }
            
            self.orders[sell_order_id] = {
                'symbol': symbol,
                'side': 'sell',
                'price': sell_price,
                'quantity': quantity,
                'status': 'open',
                'timestamp': datetime.now()
            }
            
            print(f"📊 Placed orders for {symbol}:")
            print(f"   🟢 Buy:  {quantity} @ ${buy_price:.2f}")
            print(f"   🔴 Sell: {quantity} @ ${sell_price:.2f}")
            
            return buy_order_id, sell_order_id
            
        except Exception as e:
            print(f"❌ Error placing orders for {symbol}: {e}")
            return None, None
    
    def cancel_existing_orders(self, symbol: str):
        """Cancel existing orders for a symbol"""
        try:
            orders_to_cancel = [
                order_id for order_id, order in self.orders.items() 
                if order['symbol'] == symbol and order['status'] == 'open'
            ]
            
            for order_id in orders_to_cancel:
                self.orders[order_id]['status'] = 'cancelled'
                print(f"❌ Cancelled order: {order_id}")
                
        except Exception as e:
            print(f"❌ Error cancelling orders for {symbol}: {e}")
    
    def check_price_movement(self, symbol: str, current_dex_price: float) -> bool:
        """Check if DEX price has moved by threshold amount"""
        if symbol not in self.last_price_movement:
            self.last_price_movement[symbol] = current_dex_price
            return False
        
        last_price = self.last_price_movement[symbol]
        price_change = abs(current_dex_price - last_price) / last_price
        
        if price_change >= self.price_threshold:
            print(f"📈 Price movement detected for {symbol}: {price_change:.2%}")
            return True
        
        return False
    
    def schedule_order_rebalance(self, symbol: str, new_dex_price: float):
        """Schedule order rebalancing after price movement"""
        if symbol in self.order_shift_timers:
            self.order_shift_timers[symbol].cancel()
        
        def rebalance_orders():
            print(f"⏰ Rebalancing orders for {symbol} after 2-minute delay")
            cex_data = self.get_cex_price(symbol)
            if cex_data and self.should_place_orders(symbol, new_dex_price, cex_data):
                buy_price, sell_price = self.calculate_order_prices(new_dex_price)
                quantity = self.calculate_position_size(symbol, new_dex_price)
                self.place_cex_orders(symbol, buy_price, sell_price, quantity)
        
        # Schedule rebalancing after delay
        timer = threading.Timer(self.rebalance_delay, rebalance_orders)
        timer.start()
        self.order_shift_timers[symbol] = timer
        
        # Update last movement price
        self.last_price_movement[symbol] = new_dex_price
    
    def calculate_position_size(self, symbol: str, price: float) -> float:
        """Calculate appropriate position size based on risk management"""
        # Simple position sizing: max 1% of portfolio value
        portfolio_value = self.config.get('portfolio_value', 10000)  # Default $10k
        max_position_value = portfolio_value * self.max_position_size
        quantity = max_position_value / price
        
        # Apply minimum and maximum constraints
        min_quantity = self.config.get('min_quantity', 0.001)
        max_quantity = self.config.get('max_quantity', 1.0)
        
        return max(min_quantity, min(quantity, max_quantity))
    
    def process_symbol(self, symbol: str):
        """Process a single trading symbol"""
        try:
            # Get current prices
            dex_price = self.get_dex_price(symbol)
            cex_data = self.get_cex_price(symbol)
            
            if not dex_price or not cex_data:
                return
            
            # Store price data for monitoring
            self.price_data[symbol] = {
                'dex_price': dex_price,
                'cex_data': cex_data,
                'timestamp': datetime.now(),
                'price_diff': self.calculate_price_difference(dex_price, cex_data['last'])
            }
            
            # Check for significant price movement
            if self.check_price_movement(symbol, dex_price):
                print(f"🔄 Scheduling order rebalance for {symbol}")
                self.schedule_order_rebalance(symbol, dex_price)
                return
            
            # Place orders if conditions are met
            if self.should_place_orders(symbol, dex_price, cex_data):
                buy_price, sell_price = self.calculate_order_prices(dex_price)
                quantity = self.calculate_position_size(symbol, dex_price)
                
                # Check if we already have active orders close to these prices
                if not self.has_similar_orders(symbol, buy_price, sell_price):
                    self.place_cex_orders(symbol, buy_price, sell_price, quantity)
            
        except Exception as e:
            print(f"❌ Error processing {symbol}: {e}")
    
    def has_similar_orders(self, symbol: str, target_buy_price: float, target_sell_price: float) -> bool:
        """Check if similar orders already exist to avoid duplicate placement"""
        price_tolerance = 0.001  # 0.1% tolerance
        
        for order_id, order in self.orders.items():
            if (order['symbol'] == symbol and order['status'] == 'open'):
                if order['side'] == 'buy':
                    if abs(order['price'] - target_buy_price) / target_buy_price < price_tolerance:
                        return True
                elif order['side'] == 'sell':
                    if abs(order['price'] - target_sell_price) / target_sell_price < price_tolerance:
                        return True
        
        return False
    
    async def run_bot(self):
        """Main bot execution loop"""
        print("🚀 Starting DEX/CEX Arbitrage Bot...")
        
        if not self.connect_exchanges():
            print("❌ Failed to connect to exchanges")
            return
        
        self.running = True
        symbols = self.config.get('symbols', ['BTC/USDT'])
        
        print(f"📊 Monitoring {len(symbols)} symbols: {symbols}")
        
        while self.running:
            try:
                for symbol in symbols:
                    self.process_symbol(symbol)
                    await asyncio.sleep(1)  # Small delay between symbols
                
                await asyncio.sleep(5)  # Main loop delay
                
            except KeyboardInterrupt:
                print("\n⏹️ Bot stopped by user")
                break
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
        
        self.stop_bot()
    
    def stop_bot(self):
        """Stop the bot and cleanup"""
        print("🛑 Stopping bot...")
        self.running = False
        
        # Cancel all pending timers
        for timer in self.order_shift_timers.values():
            timer.cancel()
        
        # Cancel all open orders
        for symbol in set(order['symbol'] for order in self.orders.values()):
            self.cancel_existing_orders(symbol)
        
        print("✅ Bot stopped successfully")
    
    def get_status_summary(self) -> Dict:
        """Get current bot status and metrics"""
        active_orders = sum(1 for order in self.orders.values() if order['status'] == 'open')
        total_orders = len(self.orders)
        
        return {
            'running': self.running,
            'active_orders': active_orders,
            'total_orders': total_orders,
            'monitored_symbols': len(self.config.get('symbols', [])),
            'price_data': self.price_data,
            'recent_orders': list(self.orders.values())[-5:]  # Last 5 orders
        }

# Save the bot implementation
print("✅ DEX/CEX Arbitrage Bot implementation created successfully")
print("📝 Key features implemented:")
print("  - Price monitoring for DEX and CEX")
print("  - Order placement within 2% range of DEX price")
print("  - 2-minute delay for order rebalancing after price movements")
print("  - Risk management and position sizing")
print("  - Order management and cancellation")
print("  - Real-time status monitoring")