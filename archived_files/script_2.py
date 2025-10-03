# Create the CCXT integration and WebSocket handler for real exchange connectivity
ccxt_integration_code = """
import ccxt
import ccxt.async_support as ccxt_async
import asyncio
import websockets
import json
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import aiohttp

class ExchangeManager:
    \"\"\"
    Manages connections to multiple exchanges using CCXT library
    \"\"\"
    
    def __init__(self, config: Dict):
        self.config = config
        self.exchanges = {}
        self.websocket_connections = {}
        self.price_callbacks = {}
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def initialize_cex_exchange(self, exchange_name: str, api_key: str, secret: str, sandbox: bool = True):
        \"\"\"Initialize CEX exchange connection using CCXT\"\"\"
        try:
            exchange_class = getattr(ccxt, exchange_name.lower())
            
            exchange_config = {
                'apiKey': api_key,
                'secret': secret,
                'sandbox': sandbox,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot'  # spot trading
                }
            }
            
            self.exchanges[exchange_name] = exchange_class(exchange_config)
            self.logger.info(f"✅ Initialized {exchange_name} exchange")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize {exchange_name}: {e}")
            return False
    
    async def fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict]:
        \"\"\"Fetch current ticker data from CEX\"\"\"
        try:
            if exchange_name not in self.exchanges:
                return None
                
            exchange = self.exchanges[exchange_name]
            ticker = await exchange.fetch_ticker(symbol)
            
            return {
                'symbol': symbol,
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'last': ticker['last'],
                'timestamp': ticker['timestamp'],
                'datetime': ticker['datetime']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching ticker for {symbol} from {exchange_name}: {e}")
            return None
    
    async def fetch_order_book(self, exchange_name: str, symbol: str, limit: int = 20) -> Optional[Dict]:
        \"\"\"Fetch order book from CEX\"\"\"
        try:
            if exchange_name not in self.exchanges:
                return None
                
            exchange = self.exchanges[exchange_name]
            order_book = await exchange.fetch_order_book(symbol, limit)
            
            return {
                'symbol': symbol,
                'bids': order_book['bids'][:5],  # Top 5 bids
                'asks': order_book['asks'][:5],  # Top 5 asks
                'timestamp': order_book['timestamp']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching order book for {symbol}: {e}")
            return None
    
    async def place_limit_order(self, exchange_name: str, symbol: str, side: str, 
                              amount: float, price: float) -> Optional[Dict]:
        \"\"\"Place limit order on CEX\"\"\"
        try:
            if exchange_name not in self.exchanges:
                return None
                
            exchange = self.exchanges[exchange_name]
            
            # Validate parameters
            markets = await exchange.load_markets()
            market = markets.get(symbol)
            if not market:
                self.logger.error(f"❌ Symbol {symbol} not found")
                return None
            
            # Round amount and price to market precision
            amount = exchange.amount_to_precision(symbol, amount)
            price = exchange.price_to_precision(symbol, price)
            
            order = await exchange.create_limit_order(symbol, side, amount, price)
            
            self.logger.info(f"✅ Order placed: {side} {amount} {symbol} @ {price}")
            
            return {
                'id': order['id'],
                'symbol': symbol,
                'side': side,
                'amount': amount,
                'price': price,
                'status': order['status'],
                'timestamp': order['timestamp']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error placing {side} order: {e}")
            return None
    
    async def cancel_order(self, exchange_name: str, order_id: str, symbol: str) -> bool:
        \"\"\"Cancel an order\"\"\"
        try:
            if exchange_name not in self.exchanges:
                return False
                
            exchange = self.exchanges[exchange_name]
            await exchange.cancel_order(order_id, symbol)
            
            self.logger.info(f"✅ Order cancelled: {order_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error cancelling order {order_id}: {e}")
            return False
    
    async def get_balance(self, exchange_name: str) -> Optional[Dict]:
        \"\"\"Get account balance\"\"\"
        try:
            if exchange_name not in self.exchanges:
                return None
                
            exchange = self.exchanges[exchange_name]
            balance = await exchange.fetch_balance()
            
            return {
                'free': balance['free'],
                'used': balance['used'],
                'total': balance['total']
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching balance: {e}")
            return None
    
    async def close_exchanges(self):
        \"\"\"Close all exchange connections\"\"\"
        for exchange_name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                self.logger.info(f"✅ Closed {exchange_name} connection")
            except Exception as e:
                self.logger.error(f"❌ Error closing {exchange_name}: {e}")


class DEXPriceHandler:
    \"\"\"
    Handles DEX price data from various sources
    \"\"\"
    
    def __init__(self, config: Dict):
        self.config = config
        self.websocket_urls = {
            'uniswap': 'wss://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3',
            '1inch': 'wss://pathfinder-api.1inch.exchange/ws',
            'coingecko': 'wss://ws.coincap.io/prices'
        }
        
        self.price_callbacks = []
        self.logger = logging.getLogger(__name__)
    
    def add_price_callback(self, callback: Callable):
        \"\"\"Add callback function to receive price updates\"\"\"
        self.price_callbacks.append(callback)
    
    async def connect_dex_websocket(self, source: str, symbols: List[str]):
        \"\"\"Connect to DEX WebSocket for real-time price data\"\"\"
        try:
            if source.lower() == 'coingecko':
                await self._connect_coingecko_websocket(symbols)
            elif source.lower() == '1inch':
                await self._connect_1inch_websocket(symbols)
            else:
                self.logger.warning(f"DEX source {source} not implemented, using simulation")
                await self._simulate_dex_prices(symbols)
                
        except Exception as e:
            self.logger.error(f"❌ Error connecting to {source} WebSocket: {e}")
            # Fallback to simulation
            await self._simulate_dex_prices(symbols)
    
    async def _connect_coingecko_websocket(self, symbols: List[str]):
        \"\"\"Connect to CoinGecko WebSocket for price data\"\"\"
        uri = "wss://ws.coincap.io/prices"
        
        try:
            async with websockets.connect(uri) as websocket:
                self.logger.info(f"✅ Connected to CoinGecko WebSocket")
                
                # Subscribe to symbols
                subscribe_msg = {
                    "id": 1,
                    "method": "SUBSCRIBE",
                    "params": [f"{symbol.replace('/', '').lower()}@ticker" for symbol in symbols]
                }
                
                await websocket.send(json.dumps(subscribe_msg))
                
                while True:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        data = json.loads(message)
                        
                        # Process price update
                        await self._process_price_update(data)
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.ping()
                        
        except Exception as e:
            self.logger.error(f"❌ WebSocket connection error: {e}")
            # Fallback to simulation
            await self._simulate_dex_prices(symbols)
    
    async def _simulate_dex_prices(self, symbols: List[str]):
        \"\"\"Simulate DEX price data for testing\"\"\"
        self.logger.info("📊 Starting DEX price simulation")
        
        base_prices = {
            'BTC/USDT': 50000,
            'ETH/USDT': 3000,
            'ADA/USDT': 0.5,
            'DOT/USDT': 8.0,
            'LINK/USDT': 15.0,
            'UNI/USDT': 7.0
        }
        
        import numpy as np
        
        while True:
            for symbol in symbols:
                base_price = base_prices.get(symbol, 100.0)
                
                # Add random price movement
                price_change = np.random.uniform(-0.02, 0.02)  # ±2% variation
                current_price = base_price * (1 + price_change)
                
                price_data = {
                    'symbol': symbol,
                    'price': current_price,
                    'timestamp': datetime.now().isoformat(),
                    'source': 'simulation'
                }
                
                # Notify all callbacks
                for callback in self.price_callbacks:
                    try:
                        await callback(price_data)
                    except Exception as e:
                        self.logger.error(f"❌ Error in price callback: {e}")
            
            await asyncio.sleep(5)  # Update every 5 seconds
    
    async def _process_price_update(self, data: Dict):
        \"\"\"Process incoming price update from WebSocket\"\"\"
        try:
            # Extract price information from WebSocket data
            # This would vary based on the specific API format
            
            if 'symbol' in data and 'price' in data:
                price_data = {
                    'symbol': data['symbol'],
                    'price': float(data['price']),
                    'timestamp': data.get('timestamp', datetime.now().isoformat()),
                    'source': 'dex_websocket'
                }
                
                # Notify all callbacks
                for callback in self.price_callbacks:
                    await callback(price_data)
                    
        except Exception as e:
            self.logger.error(f"❌ Error processing price update: {e}")


class WebSocketManager:
    \"\"\"
    Manages all WebSocket connections for real-time data
    \"\"\"
    
    def __init__(self, config: Dict):
        self.config = config
        self.connections = {}
        self.message_handlers = {}
        self.logger = logging.getLogger(__name__)
    
    async def connect_exchange_websocket(self, exchange_name: str, symbols: List[str]):
        \"\"\"Connect to exchange WebSocket for real-time data\"\"\"
        try:
            if exchange_name.lower() == 'binance':
                await self._connect_binance_websocket(symbols)
            elif exchange_name.lower() == 'coinbase':
                await self._connect_coinbase_websocket(symbols)
            else:
                self.logger.warning(f"WebSocket for {exchange_name} not implemented")
                
        except Exception as e:
            self.logger.error(f"❌ Error connecting to {exchange_name} WebSocket: {e}")
    
    async def _connect_binance_websocket(self, symbols: List[str]):
        \"\"\"Connect to Binance WebSocket stream\"\"\"
        # Convert symbols to Binance format (btcusdt, ethusdt, etc.)
        binance_symbols = [s.replace('/', '').lower() for s in symbols]
        streams = [f"{symbol}@ticker" for symbol in binance_symbols]
        
        uri = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
        
        try:
            async with websockets.connect(uri) as websocket:
                self.logger.info(f"✅ Connected to Binance WebSocket")
                self.connections['binance'] = websocket
                
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    # Process ticker data
                    if 'stream' in data and 'data' in data:
                        await self._process_binance_ticker(data['data'])
                        
        except Exception as e:
            self.logger.error(f"❌ Binance WebSocket error: {e}")
    
    async def _process_binance_ticker(self, ticker_data: Dict):
        \"\"\"Process Binance ticker data\"\"\"
        try:
            symbol = ticker_data['s']  # Symbol like BTCUSDT
            # Convert back to standard format
            formatted_symbol = f"{symbol[:-4]}/{symbol[-4:]}"  # BTC/USDT
            
            price_data = {
                'symbol': formatted_symbol,
                'bid': float(ticker_data['b']),
                'ask': float(ticker_data['a']),
                'last': float(ticker_data['c']),
                'volume': float(ticker_data['v']),
                'timestamp': int(ticker_data['E']),
                'source': 'binance_websocket'
            }
            
            # Call registered handlers
            if 'ticker' in self.message_handlers:
                for handler in self.message_handlers['ticker']:
                    await handler(price_data)
                    
        except Exception as e:
            self.logger.error(f"❌ Error processing Binance ticker: {e}")
    
    def add_message_handler(self, message_type: str, handler: Callable):
        \"\"\"Add message handler for specific message types\"\"\"
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
    
    async def close_all_connections(self):
        \"\"\"Close all WebSocket connections\"\"\"
        for name, connection in self.connections.items():
            try:
                await connection.close()
                self.logger.info(f"✅ Closed {name} WebSocket connection")
            except Exception as e:
                self.logger.error(f"❌ Error closing {name} connection: {e}")


# Example usage and integration
async def main():
    \"\"\"Example of how to use the exchange manager and WebSocket handlers\"\"\"
    
    config = {
        'cex_exchange': 'binance',
        'dex_source': 'coingecko',
        'symbols': ['BTC/USDT', 'ETH/USDT'],
        'cex_api_key': 'your_api_key_here',
        'cex_secret': 'your_secret_here',
        'sandbox_mode': True
    }
    
    # Initialize managers
    exchange_manager = ExchangeManager(config)
    dex_handler = DEXPriceHandler(config)
    websocket_manager = WebSocketManager(config)
    
    # Initialize CEX
    await exchange_manager.initialize_cex_exchange(
        config['cex_exchange'],
        config['cex_api_key'],
        config['cex_secret'],
        config['sandbox_mode']
    )
    
    # Add price callback for DEX data
    async def handle_dex_price(price_data):
        print(f"📊 DEX Price Update: {price_data['symbol']} = ${price_data['price']:.2f}")
    
    dex_handler.add_price_callback(handle_dex_price)
    
    # Add WebSocket handler for CEX data
    async def handle_cex_price(price_data):
        print(f"💹 CEX Price Update: {price_data['symbol']} = ${price_data['last']:.2f}")
    
    websocket_manager.add_message_handler('ticker', handle_cex_price)
    
    # Start connections
    await asyncio.gather(
        dex_handler.connect_dex_websocket(config['dex_source'], config['symbols']),
        websocket_manager.connect_exchange_websocket(config['cex_exchange'], config['symbols'])
    )

if __name__ == "__main__":
    asyncio.run(main())
"""

# Save the CCXT integration code
with open('exchange_integrations.py', 'w') as f:
    f.write(ccxt_integration_code)

print("✅ CCXT Integration and WebSocket handlers created successfully!")
print("📁 File saved as: exchange_integrations.py")
print("\n🔧 Key Components:")
print("  - ExchangeManager: CCXT integration for CEX operations")
print("  - DEXPriceHandler: DEX price data via WebSocket")
print("  - WebSocketManager: Real-time exchange data streams")
print("  - Async/await support for high performance")
print("  - Error handling and connection management")
print("\n📦 Required packages:")
print("  pip install ccxt websockets aiohttp")