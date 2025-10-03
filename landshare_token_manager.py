"""
LANDSHARE Token Manager - PancakeSwap Integration
Handles LAND token price fetching from PancakeSwap with BNB to USDT conversion
"""

import aiohttp
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
from decimal import Decimal


class LANDTokenManager:
    """
    Manages LANDSHARE token price data from PancakeSwap DEX
    Handles BNB-denominated prices and converts to USDT
    """

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # LANDSHARE token configuration
        self.contract_address = config['token']['contract_address']
        self.trading_pair = config['token']['trading_pair']

        # PancakeSwap API configuration
        self.api_url = config['dex']['api_url']
        self.websocket_url = config['dex']['websocket_url']
        self.pair_address = config['dex']['pair']

        # Price cache
        self.cached_land_price = None
        self.cached_bnb_price = None
        self.last_update = None

        # Session for HTTP requests
        self.session = None

    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.logger.info("LAND Token Manager initialized")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.logger.info("LAND Token Manager closed")

    async def get_land_bnb_price(self) -> Optional[float]:
        """
        Fetch LAND/BNB price from DexScreener (more reliable than PancakeSwap API)
        Returns LAND price denominated in BNB
        """
        try:
            # Use DexScreener API for reliable data
            pair_address = "0x13f80c53b837622e899e1ac0021ed3d1775caefa"
            url = f"https://api.dexscreener.com/latest/dex/pairs/bsc/{pair_address}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'pairs' in data and len(data['pairs']) > 0:
                        pair_data = data['pairs'][0]

                        # Get price in BNB (native token)
                        price_bnb = float(pair_data['priceNative'])

                        self.logger.debug(f"LAND/BNB price: {price_bnb} (from DexScreener)")
                        return price_bnb
                    else:
                        self.logger.warning(f"No pair data found: {data}")
                        return None
                else:
                    self.logger.error(f"DexScreener API error: {response.status}")
                    return None

        except Exception as e:
            self.logger.error(f"Error fetching LAND/BNB price: {e}")
            return None

    async def get_bnb_usdt_rate(self) -> Optional[float]:
        """
        Fetch BNB/USDT rate from Binance (most liquid source)
        Falls back to cached value if fetch fails
        """
        try:
            # Use Binance for BNB/USDT rate (most liquid)
            url = "https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    bnb_usdt_rate = float(data['price'])
                    self.cached_bnb_price = bnb_usdt_rate
                    self.logger.debug(f"BNB/USDT rate: {bnb_usdt_rate}")
                    return bnb_usdt_rate
                else:
                    # Fall back to cached value
                    if self.cached_bnb_price:
                        self.logger.warning(f"Using cached BNB rate: {self.cached_bnb_price}")
                        return self.cached_bnb_price
                    return None

        except Exception as e:
            self.logger.error(f"Error fetching BNB/USDT rate: {e}")
            # Return cached value if available
            if self.cached_bnb_price:
                self.logger.warning(f"Using cached BNB rate after error: {self.cached_bnb_price}")
                return self.cached_bnb_price
            return None

    async def get_land_usdt_price(self) -> Optional[float]:
        """
        Get LAND/USDT price by converting LAND/BNB price to USDT
        This is the main method used by the trading bot
        """
        try:
            # Fetch both prices
            land_bnb = await self.get_land_bnb_price()
            bnb_usdt = await self.get_bnb_usdt_rate()

            if land_bnb is None or bnb_usdt is None:
                self.logger.error("Failed to fetch required prices for LAND/USDT calculation")
                return self.cached_land_price  # Return cached value if available

            # Calculate LAND/USDT price
            land_usdt = land_bnb * bnb_usdt

            # Update cache
            self.cached_land_price = land_usdt
            self.last_update = datetime.now()

            self.logger.info(f"LAND/USDT price: ${land_usdt:.6f} (BNB: {land_bnb:.8f}, BNB/USDT: ${bnb_usdt:.2f})")

            return land_usdt

        except Exception as e:
            self.logger.error(f"Error calculating LAND/USDT price: {e}")
            return self.cached_land_price

    async def get_order_book_data(self) -> Optional[Dict]:
        """
        Fetch order book data for LAND from PancakeSwap
        Returns bid/ask spread information
        """
        try:
            # Note: PancakeSwap doesn't provide traditional order book
            # This simulates order book data based on liquidity pools
            land_usdt_price = await self.get_land_usdt_price()

            if land_usdt_price is None:
                return None

            # Estimate bid/ask spread based on typical DEX spreads
            estimated_spread = 0.001  # 0.1% spread estimate

            bid = land_usdt_price * (1 - estimated_spread / 2)
            ask = land_usdt_price * (1 + estimated_spread / 2)

            return {
                'bid': bid,
                'ask': ask,
                'mid': land_usdt_price,
                'spread': estimated_spread,
                'timestamp': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error fetching order book data: {e}")
            return None

    async def get_token_info(self) -> Dict:
        """
        Get comprehensive token information
        """
        try:
            url = f"{self.api_url}/tokens/{self.contract_address}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'data' in data:
                        token_data = data['data']

                        return {
                            'name': token_data.get('name', 'LANDSHARE'),
                            'symbol': token_data.get('symbol', 'LAND'),
                            'price_bnb': float(token_data.get('price', 0)),
                            'price_usdt': await self.get_land_usdt_price(),
                            'updated_at': datetime.now().isoformat()
                        }
                else:
                    return {}

        except Exception as e:
            self.logger.error(f"Error fetching token info: {e}")
            return {}

    def get_cached_price(self) -> Optional[float]:
        """
        Get last cached LAND/USDT price
        Useful for fallback scenarios
        """
        return self.cached_land_price

    def is_price_stale(self, max_age_seconds: int = 300) -> bool:
        """
        Check if cached price is stale
        """
        if self.last_update is None:
            return True

        age = (datetime.now() - self.last_update).total_seconds()
        return age > max_age_seconds


class PancakeSwapClient:
    """
    Client for interacting with PancakeSwap API
    Provides additional utility methods
    """

    def __init__(self, api_url: str):
        self.api_url = api_url
        self.logger = logging.getLogger(__name__)
        self.session = None

    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    async def get_pairs(self) -> Optional[Dict]:
        """
        Fetch all trading pairs from PancakeSwap
        """
        try:
            url = f"{self.api_url}/pairs"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    self.logger.error(f"Error fetching pairs: {response.status}")
                    return None

        except Exception as e:
            self.logger.error(f"Error fetching pairs: {e}")
            return None

    async def get_token_by_address(self, address: str) -> Optional[Dict]:
        """
        Fetch token information by contract address
        """
        try:
            url = f"{self.api_url}/tokens/{address}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data
                else:
                    return None

        except Exception as e:
            self.logger.error(f"Error fetching token {address}: {e}")
            return None


# Example usage
async def main():
    """Test the LAND token manager"""
    config = {
        'token': {
            'contract_address': '0x9d986A3f147212327DD658F712d5264a73a1fdB0',
            'trading_pair': 'LAND/USDT'
        },
        'dex': {
            'api_url': 'https://api.pancakeswap.info/api/v2',
            'websocket_url': 'wss://bsc-ws-node.nariox.org:443',
            'pair': 'LAND/WBNB'
        }
    }

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Create manager
    manager = LANDTokenManager(config)
    await manager.initialize()

    try:
        # Fetch LAND price
        price = await manager.get_land_usdt_price()
        print(f"LAND/USDT Price: ${price:.6f}")

        # Get order book data
        order_book = await manager.get_order_book_data()
        if order_book:
            print(f"Bid: ${order_book['bid']:.6f}")
            print(f"Ask: ${order_book['ask']:.6f}")
            print(f"Spread: {order_book['spread']:.2%}")

        # Get token info
        token_info = await manager.get_token_info()
        print(f"Token Info: {token_info}")

    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
