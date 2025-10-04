"""
LANDSHARE Market Maker Bot - Streamlit Interface
User-friendly interface for configuring and running the LANDSHARE market maker
"""

import streamlit as st
import pandas as pd
import yaml
import asyncio
import logging
from datetime import datetime
from landshare_token_manager import LANDTokenManager
from landshare_market_maker import MultiCEXManager, ReferencePriceEngine, MarketMakerEngine
import threading

# Page configuration
st.set_page_config(
    page_title="LANDSHARE Market Maker",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .price-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_config' not in st.session_state:
    st.session_state.bot_config = {
        'reference_mode': 'dex',
        'selected_exchange': 'mexc',
        'spread_percentage': 1.5,
        'order_amount_usd': 1000,
        'refresh_interval': 60
    }
if 'dex_price' not in st.session_state:
    st.session_state.dex_price = None
if 'cex_price' not in st.session_state:
    st.session_state.cex_price = None
if 'last_dex_price' not in st.session_state:
    st.session_state.last_dex_price = None
if 'last_cex_price' not in st.session_state:
    st.session_state.last_cex_price = None
if 'dynamic_interval' not in st.session_state:
    st.session_state.dynamic_interval = 60
if 'price_fetch_interval' not in st.session_state:
    st.session_state.price_fetch_interval = 5  # Always fetch prices every 5 seconds
if 'active_orders' not in st.session_state:
    st.session_state.active_orders = []
if 'market_maker_instance' not in st.session_state:
    st.session_state.market_maker_instance = None
if 'bot_logs' not in st.session_state:
    st.session_state.bot_logs = []
if 'api_credentials' not in st.session_state:
    st.session_state.api_credentials = {}

# Helper function to fetch prices (works without credentials)
async def fetch_dex_price():
    """Fetch DEX price without credentials"""
    try:
        # Load minimal config for price fetching
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

        land_manager = LANDTokenManager(config)
        await land_manager.initialize()
        dex_price = await land_manager.get_land_usdt_price()
        await land_manager.close()

        return dex_price
    except Exception as e:
        logging.error(f"Error fetching DEX price: {e}")
        return None

async def fetch_cex_price(exchange_name):
    """Fetch CEX price without credentials (public endpoints)"""
    try:
        import ccxt.async_support as ccxt

        # Initialize exchange without credentials (public data only)
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({
            'enableRateLimit': True
        })

        # Check if exchange has LAND/USDT market
        try:
            await exchange.load_markets()

            # Try different trading pair formats
            pairs_to_try = ['LAND/USDT', 'LANDSHARE/USDT', 'LAND/USD']
            ticker = None

            for pair in pairs_to_try:
                if pair in exchange.markets:
                    ticker = await exchange.fetch_ticker(pair)
                    break

            if ticker:
                cex_price = ticker['last'] if 'last' in ticker else None
            else:
                cex_price = None

        except Exception as market_error:
            logging.warning(f"{exchange_name} does not have LAND trading pair: {market_error}")
            cex_price = None

        await exchange.close()
        return cex_price
    except Exception as e:
        logging.error(f"Error fetching CEX price from {exchange_name}: {e}")
        return None

def calculate_dynamic_interval(current_price, last_price, spread_pct):
    """
    Calculate refresh interval based on price fluctuation
    If price change exceeds spread, reduce interval to 10 seconds
    Otherwise use default interval
    """
    if last_price is None or current_price is None:
        return 60

    price_change_pct = abs(current_price - last_price) / last_price
    spread_threshold = spread_pct / 100

    if price_change_pct >= spread_threshold:
        return 10  # Fast refresh when price exceeds spread
    else:
        return 60  # Normal refresh

def add_log(message):
    """Add a log message to the session state"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.bot_logs.append(log_entry)
    # Keep only last 50 logs
    if len(st.session_state.bot_logs) > 50:
        st.session_state.bot_logs = st.session_state.bot_logs[-50:]

def create_bot_config():
    """Create configuration dict from session state and credentials"""
    config = {
        'token': {
            'symbol': 'LAND',
            'trading_pair': 'LAND/USDT',
            'contract_address': '0x9d986A3f147212327DD658F712d5264a73a1fdB0',
            'blockchain': 'BSC'
        },
        'dex': {
            'name': 'pancakeswap',
            'api_url': 'https://api.pancakeswap.info/api/v2',
            'websocket_url': 'wss://bsc-ws-node.nariox.org:443',
            'pair': 'LAND/WBNB'
        },
        'cex': {
            'selected_exchange': st.session_state.bot_config['selected_exchange']
        },
        'api_credentials': st.session_state.api_credentials,
        'reference_mode': {
            'use_dex_reference': st.session_state.bot_config['reference_mode'] == 'dex',
            'sync_interval': 60
        },
        'market_making': {
            'spread_percentage': st.session_state.bot_config['spread_percentage'],
            'order_amount_usd': st.session_state.bot_config['order_amount_usd'],
            'order_count': 1,
            'post_only': True,
            'refresh_interval': st.session_state.dynamic_interval
        },
        'fill_handling': {
            'dex_mode_delay': 0,
            'cex_mode_delay': 120,
            'immediate_rebalance': True
        },
        'risk_management': {
            'max_inventory_skew': 0.3,
            'max_position_usd': 5000,
            'max_daily_trades': 200
        },
        'system': {
            'log_level': 'INFO'
        }
    }
    return config

async def run_bot_cycle():
    """Run a single bot cycle - place orders and check fills"""
    try:
        if not st.session_state.market_maker_instance:
            return

        market_maker = st.session_state.market_maker_instance

        # Place spread orders
        add_log("Placing spread orders...")
        success = await market_maker.place_spread_orders()

        if success:
            # Fetch active orders from exchange
            exchange = market_maker.cex_manager.exchanges[market_maker.cex_manager.selected_exchange]
            open_orders = await exchange.fetch_open_orders('LAND/USDT')

            # Store active orders in session state
            st.session_state.active_orders = open_orders
            add_log(f"✅ Successfully placed {len(open_orders)} orders")

            # Check for fills
            fills = await market_maker.check_fills()

            if fills:
                for fill in fills:
                    add_log(f"🎯 Order filled: {fill['side'].upper()} {fill['filled_amount']:.2f} @ ${fill['filled_price']:.6f}")
                    await market_maker.fill_handler.handle_fill(fill)
        else:
            add_log("❌ Failed to place orders")

    except Exception as e:
        add_log(f"❌ Error in bot cycle: {str(e)}")
        logging.error(f"Bot cycle error: {e}", exc_info=True)

async def initialize_bot():
    """Initialize the bot components"""
    try:
        add_log("🚀 Initializing bot components...")

        # Create config
        config = create_bot_config()

        # Initialize managers
        land_manager = LANDTokenManager(config)
        cex_manager = MultiCEXManager(config)

        await land_manager.initialize()
        await cex_manager.initialize()

        add_log(f"✅ Connected to {config['cex']['selected_exchange'].upper()}")

        # Create engines
        reference_engine = ReferencePriceEngine(config, land_manager, cex_manager)
        market_maker = MarketMakerEngine(config, reference_engine, cex_manager)

        # Store in session state
        st.session_state.market_maker_instance = market_maker

        add_log("✅ Bot initialized successfully")
        return True

    except Exception as e:
        add_log(f"❌ Failed to initialize bot: {str(e)}")
        logging.error(f"Bot initialization error: {e}", exc_info=True)
        return False

async def shutdown_bot():
    """Shutdown the bot and close connections"""
    try:
        if st.session_state.market_maker_instance:
            market_maker = st.session_state.market_maker_instance

            # Cancel all orders
            add_log("Cancelling all open orders...")
            cancelled = await market_maker.cex_manager.cancel_all_orders('LAND/USDT')
            add_log(f"✅ Cancelled {cancelled} orders")

            # Close connections
            await market_maker.reference_engine.land_manager.close()
            await market_maker.cex_manager.close()

            st.session_state.market_maker_instance = None
            st.session_state.active_orders = []
            add_log("✅ Bot shutdown complete")

    except Exception as e:
        add_log(f"❌ Error shutting down bot: {str(e)}")
        logging.error(f"Bot shutdown error: {e}", exc_info=True)

# Title and description
st.title("LANDSHARE Market Maker Bot")
st.markdown("Automated market making for LAND/USDT with dual reference price modes")

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Bot Configuration")

    # Reference Mode Selection
    reference_mode = st.radio(
        "Reference Price Mode",
        options=['dex', 'cex'],
        format_func=lambda x: 'DEX Reference (PancakeSwap - Immediate rebalance)' if x == 'dex' else 'CEX Reference (Exchange mid-price - 2min delay)',
        index=0 if st.session_state.bot_config['reference_mode'] == 'dex' else 1
    )
    st.session_state.bot_config['reference_mode'] = reference_mode

    # Exchange Selection
    st.markdown("### Exchange Configuration")

    selected_exchange = st.selectbox(
        "Select CEX Exchange",
        options=['mexc', 'gateio', 'bitmart', 'ascendex', 'bingx'],
        format_func=lambda x: {
            'mexc': 'MEXC Global',
            'gateio': 'Gate.io',
            'bitmart': 'BitMart',
            'ascendex': 'AscendEX',
            'bingx': 'BingX'
        }[x],
        index=['mexc', 'gateio', 'bitmart', 'ascendex', 'bingx'].index(st.session_state.bot_config['selected_exchange'])
    )
    st.session_state.bot_config['selected_exchange'] = selected_exchange

    # API Credentials - Exchange specific
    with st.expander("API Credentials (Required for Trading)", expanded=False):
        if selected_exchange == 'mexc':
            api_key = st.text_input("MEXC API Key", type="password", key="mexc_key")
            api_secret = st.text_input("MEXC API Secret", type="password", key="mexc_secret")
            # Store credentials
            st.session_state.api_credentials['mexc_api_key'] = api_key
            st.session_state.api_credentials['mexc_secret'] = api_secret

        elif selected_exchange == 'gateio':
            api_key = st.text_input("Gate.io API Key", type="password", key="gateio_key")
            api_secret = st.text_input("Gate.io API Secret", type="password", key="gateio_secret")
            api_password = st.text_input("Gate.io API Password", type="password", key="gateio_pass")
            # Store credentials
            st.session_state.api_credentials['gateio_api_key'] = api_key
            st.session_state.api_credentials['gateio_secret'] = api_secret
            st.session_state.api_credentials['gateio_password'] = api_password

        elif selected_exchange == 'bitmart':
            api_key = st.text_input("BitMart API Key", type="password", key="bitmart_key")
            api_secret = st.text_input("BitMart API Secret", type="password", key="bitmart_secret")
            api_uid = st.text_input("BitMart UID", key="bitmart_uid")
            api_memo = st.text_input("BitMart Memo", type="password", key="bitmart_memo", help="Required for BitMart API authentication")
            # Store credentials
            st.session_state.api_credentials['bitmart_api_key'] = api_key
            st.session_state.api_credentials['bitmart_secret'] = api_secret
            st.session_state.api_credentials['bitmart_uid'] = api_uid
            st.session_state.api_credentials['bitmart_memo'] = api_memo

        elif selected_exchange == 'ascendex':
            api_key = st.text_input("AscendEX API Key", type="password", key="ascendex_key")
            api_secret = st.text_input("AscendEX API Secret", type="password", key="ascendex_secret")
            api_group_id = st.text_input("AscendEX Group ID", key="ascendex_group_id", help="Required for AscendEX API authentication")
            # Store credentials
            st.session_state.api_credentials['ascendex_api_key'] = api_key
            st.session_state.api_credentials['ascendex_secret'] = api_secret
            st.session_state.api_credentials['ascendex_group_id'] = api_group_id

        elif selected_exchange == 'bingx':
            api_key = st.text_input("BingX API Key", type="password", key="bingx_key")
            api_secret = st.text_input("BingX API Secret", type="password", key="bingx_secret")
            # Store credentials
            st.session_state.api_credentials['bingx_api_key'] = api_key
            st.session_state.api_credentials['bingx_secret'] = api_secret

    # Trading Parameters
    st.markdown("### Trading Parameters")

    col_a, col_b = st.columns(2)

    with col_a:
        spread_pct = st.number_input(
            "Spread Percentage (%)",
            min_value=0.1,
            max_value=10.0,
            value=st.session_state.bot_config['spread_percentage'],
            step=0.1,
            help="Distance from reference price for buy/sell orders"
        )
        st.session_state.bot_config['spread_percentage'] = spread_pct

    with col_b:
        order_amount = st.number_input(
            "Order Amount (USD)",
            min_value=10,
            max_value=10000,
            value=st.session_state.bot_config['order_amount_usd'],
            step=100,
            help="Total order amount ($500 per side for $1000 total)"
        )
        st.session_state.bot_config['order_amount_usd'] = order_amount

    if st.session_state.bot_running:
        st.info(f"⏱️ Dynamic Refresh: {st.session_state.dynamic_interval}s (adjusts automatically when price fluctuation exceeds spread)")

    # Control Buttons
    st.markdown("### Bot Control")

    col_start, col_stop = st.columns(2)

    with col_start:
        if st.button("Start Bot", type="primary", disabled=st.session_state.bot_running):
            # Validate credentials based on exchange
            credentials_valid = False

            if selected_exchange == 'mexc':
                credentials_valid = bool(api_key and api_secret)
            elif selected_exchange == 'gateio':
                credentials_valid = bool(api_key and api_secret and api_password)
            elif selected_exchange == 'bitmart':
                credentials_valid = bool(api_key and api_secret and api_uid and api_memo)
            elif selected_exchange == 'ascendex':
                credentials_valid = bool(api_key and api_secret and api_group_id)
            elif selected_exchange == 'bingx':
                credentials_valid = bool(api_key and api_secret)

            if not credentials_valid:
                st.error(f"Please provide all required {selected_exchange.upper()} API credentials")
            else:
                # Initialize bot
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(initialize_bot())
                loop.close()

                if success:
                    st.session_state.bot_running = True
                    st.success("Bot started successfully!")
                    st.rerun()
                else:
                    st.error("Failed to start bot. Check logs for details.")

    with col_stop:
        if st.button("Stop Bot", type="secondary", disabled=not st.session_state.bot_running):
            # Shutdown bot
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(shutdown_bot())
            loop.close()

            st.session_state.bot_running = False
            st.info("Bot stopped")
            st.rerun()

with col2:
    st.subheader("Bot Status")

    # Status indicator
    if st.session_state.bot_running:
        st.success("🟢 Status: RUNNING")
    else:
        st.error("🔴 Status: STOPPED")

    # Current Configuration Summary
    st.markdown("### Current Settings")

    st.metric("Reference Mode",
              "DEX (PancakeSwap)" if st.session_state.bot_config['reference_mode'] == 'dex' else "CEX (Exchange)")

    st.metric("Selected Exchange",
              st.session_state.bot_config['selected_exchange'].upper())

    st.metric("Spread",
              f"{st.session_state.bot_config['spread_percentage']}%")

    st.metric("Order Amount",
              f"${st.session_state.bot_config['order_amount_usd']}")

# Fetch prices ALWAYS (even when bot is stopped)
with st.spinner("Fetching live prices..."):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Fetch DEX price
    dex_price = loop.run_until_complete(fetch_dex_price())
    if dex_price:
        st.session_state.dex_price = dex_price

    # Fetch CEX price (without credentials)
    cex_price = loop.run_until_complete(fetch_cex_price(selected_exchange))
    if cex_price:
        st.session_state.cex_price = cex_price

    loop.close()

# Price Monitoring Section (ALWAYS VISIBLE)
st.markdown("---")
st.subheader("💰 Live Price Data")

col_price1, col_price2, col_price3, col_price4 = st.columns(4)

with col_price1:
    if st.session_state.dex_price:
        st.metric("DEX Price (PancakeSwap)", f"${st.session_state.dex_price:.6f}",
                 help="LAND/USDT price from PancakeSwap DEX")
    else:
        st.metric("DEX Price (PancakeSwap)", "Loading...")

with col_price2:
    if st.session_state.cex_price:
        st.metric(f"CEX Price ({selected_exchange.upper()})", f"${st.session_state.cex_price:.6f}",
                 help=f"LAND/USDT mid-price from {selected_exchange.upper()}")
    else:
        st.metric(f"CEX Price ({selected_exchange.upper()})", "N/A",
                 help="CEX price requires LAND/USDT trading pair")

with col_price3:
    # Calculate price divergence
    if st.session_state.dex_price and st.session_state.cex_price:
        divergence = abs(st.session_state.dex_price - st.session_state.cex_price) / st.session_state.dex_price
        st.metric("Price Divergence", f"{divergence:.2%}",
                 help="Price difference between DEX and CEX")
    else:
        st.metric("Price Divergence", "N/A")

with col_price4:
    # Show active reference price
    reference_price = st.session_state.dex_price if reference_mode == 'dex' else st.session_state.cex_price
    if reference_price:
        spread = spread_pct / 100
        buy_price = reference_price * (1 - spread)
        sell_price = reference_price * (1 + spread)

        st.metric("Order Range",
                 f"${buy_price:.6f} - ${sell_price:.6f}",
                 help=f"Buy and sell order prices based on {reference_mode.upper()} reference")
    else:
        st.metric("Order Range", "N/A")

# Calculate dynamic interval if bot is running
if st.session_state.bot_running:
    reference_price = st.session_state.dex_price if reference_mode == 'dex' else st.session_state.cex_price
    last_reference_price = st.session_state.last_dex_price if reference_mode == 'dex' else st.session_state.last_cex_price

    st.session_state.dynamic_interval = calculate_dynamic_interval(
        reference_price,
        last_reference_price,
        spread_pct
    )

# Update last prices
st.session_state.last_dex_price = st.session_state.dex_price
st.session_state.last_cex_price = st.session_state.cex_price

# Active Orders Section
st.markdown("---")
st.subheader("📊 Active Orders")

if st.session_state.bot_running:
    # Run bot cycle if bot is running
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_bot_cycle())
    loop.close()

    # Display real orders from exchange
    if st.session_state.active_orders:
        orders_data = []
        for order in st.session_state.active_orders:
            orders_data.append({
                'Order ID': order.get('id', 'N/A'),
                'Side': order.get('side', 'N/A').upper(),
                'Price': f"${order.get('price', 0):.6f}",
                'Amount': f"{order.get('amount', 0):.2f} LAND",
                'Filled': f"{order.get('filled', 0):.2f}",
                'Status': order.get('status', 'N/A').upper(),
                'Exchange': selected_exchange.upper(),
                'Time': datetime.fromtimestamp(order.get('timestamp', 0) / 1000).strftime('%H:%M:%S') if order.get('timestamp') else 'N/A'
            })

        df_orders = pd.DataFrame(orders_data)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
    else:
        st.warning("No active orders. Waiting for next cycle...")

else:
    st.info("📌 Start the bot to place orders. Prices are shown above for monitoring.")

# Logs Section
st.markdown("---")
st.subheader("📝 Bot Logs")

if st.session_state.bot_logs:
    # Display logs in reverse chronological order (newest first)
    log_container = st.container()
    with log_container:
        for log in reversed(st.session_state.bot_logs[-20:]):  # Show last 20 logs
            st.text(log)
else:
    if st.session_state.bot_running:
        st.info("Waiting for bot activity...")
    else:
        st.info("💡 Prices are fetched live every 5 seconds. Start the bot to begin trading.")

# Footer
st.markdown("---")
st.markdown(
    "**LANDSHARE Market Maker Bot** | "
    "Real-time market making for LAND/USDT | "
    "⚠️ Trading carries risk - use at your own discretion"
)

# Auto-refresh for live prices (always refresh every 5 seconds)
import time
if st.session_state.bot_running:
    # Use dynamic interval when bot is running
    time.sleep(st.session_state.dynamic_interval)
else:
    # Use fixed 5 second interval for price monitoring when bot is stopped
    time.sleep(5)

st.rerun()
