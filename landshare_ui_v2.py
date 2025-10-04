"""
LANDSHARE Market Maker Bot - Streamlit Interface v2
Enhanced with authentication, saved credentials, and portfolio display
"""

import streamlit as st
import pandas as pd
import yaml
import asyncio
import logging
import json
import hashlib
from datetime import datetime
from pathlib import Path
from landshare_token_manager import LANDTokenManager
from landshare_market_maker import MultiCEXManager, ReferencePriceEngine, MarketMakerEngine
import ccxt.async_support as ccxt

# Page configuration
st.set_page_config(
    page_title="LANDSHARE Market Maker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
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
    .portfolio-box {
        background-color: #f0f9ff;
        padding: 15px;
        border-radius: 8px;
        border: 2px solid #0ea5e9;
    }
</style>
""", unsafe_allow_html=True)

# Config file paths
AUTH_CONFIG_FILE = Path("auth_config.json")
CEX_CONFIG_FILE = Path("cex_credentials.json")

# Helper functions for config management
def load_json_config(file_path):
    """Load JSON configuration file"""
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_json_config(file_path, data):
    """Save JSON configuration file"""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    """Verify user credentials"""
    auth_config = load_json_config(AUTH_CONFIG_FILE)
    users = auth_config.get('users', {})

    if username in users:
        stored_hash = users[username].get('password_hash')
        if not stored_hash:
            # Legacy: plain password (convert to hash)
            if users[username].get('password') == password:
                return True
        else:
            if stored_hash == hash_password(password):
                return True
    return False

def save_cex_credentials(exchange_name, credentials):
    """Save CEX credentials to JSON file"""
    config = load_json_config(CEX_CONFIG_FILE)
    if 'exchanges' not in config:
        config['exchanges'] = {}
    config['exchanges'][exchange_name] = credentials
    save_json_config(CEX_CONFIG_FILE, config)

def load_cex_credentials(exchange_name):
    """Load CEX credentials from JSON file"""
    config = load_json_config(CEX_CONFIG_FILE)
    return config.get('exchanges', {}).get(exchange_name, {})

def get_all_saved_exchanges():
    """Get list of all saved exchange names"""
    config = load_json_config(CEX_CONFIG_FILE)
    return list(config.get('exchanges', {}).keys())

# Authentication state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Login page
if not st.session_state.authenticated:
    st.title("🔐 LANDSHARE Market Maker - Login")
    st.markdown("Please log in to access the trading bot")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)

            if submit:
                if verify_login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    st.stop()

# Initialize session state after authentication
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_config' not in st.session_state:
    st.session_state.bot_config = {
        'reference_mode': 'dex',
        'selected_exchange': None,
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
if 'active_orders' not in st.session_state:
    st.session_state.active_orders = []
if 'market_maker_instance' not in st.session_state:
    st.session_state.market_maker_instance = None
if 'bot_logs' not in st.session_state:
    st.session_state.bot_logs = []
if 'portfolio_data' not in st.session_state:
    st.session_state.portfolio_data = None
if 'exchange_connected' not in st.session_state:
    st.session_state.exchange_connected = False

# Helper functions
async def fetch_dex_price():
    """Fetch DEX price without credentials"""
    try:
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

async def fetch_cex_price(exchange_name, trading_pair='LANDSHARE/USDT'):
    """Fetch CEX price without credentials (public endpoints)"""
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({'enableRateLimit': True})

        try:
            await exchange.load_markets()

            pairs_to_try = [trading_pair, 'LAND/USDT', 'LANDSHARE/USD']
            ticker = None

            for pair in pairs_to_try:
                if pair in exchange.markets:
                    ticker = await exchange.fetch_ticker(pair)
                    break

            cex_price = ticker['last'] if ticker and 'last' in ticker else None

        except Exception as market_error:
            logging.warning(f"{exchange_name} market error: {market_error}")
            cex_price = None

        await exchange.close()
        return cex_price
    except Exception as e:
        logging.error(f"Error fetching CEX price from {exchange_name}: {e}")
        return None

async def fetch_portfolio(exchange_name, credentials):
    """Fetch portfolio balances from exchange"""
    try:
        exchange_class = getattr(ccxt, exchange_name)

        # Build exchange config based on exchange type
        exchange_config = {
            'apiKey': credentials.get('api_key', ''),
            'secret': credentials.get('secret', ''),
            'enableRateLimit': True
        }

        # Gate.io doesn't need password anymore (as per requirements)
        # BitMart uses UID
        if exchange_name == 'bitmart':
            exchange_config['uid'] = credentials.get('uid', '')

        exchange = exchange_class(exchange_config)
        await exchange.load_markets()

        balance = await exchange.fetch_balance()

        # Filter non-zero balances
        portfolio = {}
        for currency, amounts in balance.items():
            if currency not in ['free', 'used', 'total', 'info'] and isinstance(amounts, dict):
                total = amounts.get('total', 0)
                if total > 0:
                    portfolio[currency] = {
                        'free': amounts.get('free', 0),
                        'used': amounts.get('used', 0),
                        'total': total
                    }

        await exchange.close()
        return portfolio

    except Exception as e:
        logging.error(f"Error fetching portfolio from {exchange_name}: {e}")
        return None

def add_log(message):
    """Add a log message to the session state"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.bot_logs.append(log_entry)
    if len(st.session_state.bot_logs) > 50:
        st.session_state.bot_logs = st.session_state.bot_logs[-50:]

def create_bot_config():
    """Create configuration dict from session state and saved credentials"""
    exchange_name = st.session_state.bot_config['selected_exchange']
    credentials = load_cex_credentials(exchange_name)

    # Map trading pair based on exchange
    trading_pair = 'LANDSHARE/USDT' if exchange_name == 'gateio' else 'LAND/USDT'

    config = {
        'token': {
            'symbol': 'LAND',
            'trading_pair': trading_pair,
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
            'selected_exchange': exchange_name
        },
        'api_credentials': {
            f'{exchange_name}_api_key': credentials.get('api_key', ''),
            f'{exchange_name}_secret': credentials.get('secret', ''),
        },
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

    # Add exchange-specific credentials
    if exchange_name == 'bitmart':
        config['api_credentials'][f'{exchange_name}_uid'] = credentials.get('uid', '')

    return config

async def run_bot_cycle():
    """Run a single bot cycle - place orders and check fills"""
    try:
        if not st.session_state.market_maker_instance:
            return

        market_maker = st.session_state.market_maker_instance
        trading_pair = market_maker.trading_pair

        add_log("Placing spread orders...")
        success = await market_maker.place_spread_orders()

        if success:
            exchange = market_maker.cex_manager.exchanges[market_maker.cex_manager.selected_exchange]
            open_orders = await exchange.fetch_open_orders(trading_pair)

            st.session_state.active_orders = open_orders
            add_log(f"✅ Successfully placed {len(open_orders)} orders")

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

        config = create_bot_config()

        land_manager = LANDTokenManager(config)
        cex_manager = MultiCEXManager(config)

        await land_manager.initialize()
        await cex_manager.initialize()

        add_log(f"✅ Connected to {config['cex']['selected_exchange'].upper()}")

        reference_engine = ReferencePriceEngine(config, land_manager, cex_manager)
        market_maker = MarketMakerEngine(config, reference_engine, cex_manager)

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

            add_log("Cancelling all open orders...")
            trading_pair = market_maker.trading_pair
            cancelled = await market_maker.cex_manager.cancel_all_orders(trading_pair)
            add_log(f"✅ Cancelled {cancelled} orders")

            await market_maker.reference_engine.land_manager.close()
            await market_maker.cex_manager.close()

            st.session_state.market_maker_instance = None
            st.session_state.active_orders = []
            add_log("✅ Bot shutdown complete")

    except Exception as e:
        add_log(f"❌ Error shutting down bot: {str(e)}")
        logging.error(f"Bot shutdown error: {e}", exc_info=True)

# Sidebar - User info and logout
with st.sidebar:
    st.markdown(f"### 👤 Logged in as: **{st.session_state.username}**")
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.rerun()

    st.markdown("---")
    st.markdown("### 📊 Quick Stats")

    if st.session_state.dex_price:
        st.metric("DEX Price", f"${st.session_state.dex_price:.6f}")

    if st.session_state.cex_price:
        st.metric("CEX Price", f"${st.session_state.cex_price:.6f}")

    if st.session_state.bot_running:
        st.success("🟢 Bot Running")
    else:
        st.error("🔴 Bot Stopped")

# Title
st.title("LANDSHARE Market Maker Bot")
st.markdown("Automated market making for LAND/USDT with dual reference price modes")

# Main content tabs
tab1, tab2, tab3 = st.tabs(["🔧 Configuration", "📊 Trading", "💼 Portfolio"])

with tab1:
    st.subheader("Exchange Configuration")

    # Get saved exchanges
    saved_exchanges = get_all_saved_exchanges()
    available_exchanges = ['mexc', 'gateio', 'bitmart']

    col_exchange, col_add = st.columns([3, 1])

    with col_exchange:
        if saved_exchanges:
            selected_exchange = st.selectbox(
                "Select Exchange",
                options=saved_exchanges,
                format_func=lambda x: {
                    'mexc': 'MEXC Global',
                    'gateio': 'Gate.io',
                    'bitmart': 'BitMart'
                }.get(x, x.upper())
            )
            st.session_state.bot_config['selected_exchange'] = selected_exchange
        else:
            st.info("No exchanges configured. Please add an exchange below.")
            st.session_state.bot_config['selected_exchange'] = None

    with col_add:
        st.markdown("<br>", unsafe_allow_html=True)
        add_exchange = st.button("➕ Add Exchange", use_container_width=True)

    # Add new exchange
    if add_exchange or not saved_exchanges:
        st.markdown("### Add New Exchange")

        with st.form("add_exchange_form"):
            new_exchange = st.selectbox(
                "Exchange",
                options=[ex for ex in available_exchanges if ex not in saved_exchanges],
                format_func=lambda x: {
                    'mexc': 'MEXC Global',
                    'gateio': 'Gate.io',
                    'bitmart': 'BitMart'
                }[x]
            )

            api_key = st.text_input("API Key", type="password")
            api_secret = st.text_input("API Secret", type="password")

            # Exchange-specific fields
            if new_exchange == 'bitmart':
                api_uid = st.text_input("UID")

            connect_button = st.form_submit_button("Connect & Save", use_container_width=True)

            if connect_button:
                if not api_key or not api_secret:
                    st.error("Please provide API Key and Secret")
                elif new_exchange == 'bitmart' and not api_uid:
                    st.error("Please provide UID for BitMart")
                else:
                    # Test connection and save
                    credentials = {
                        'api_key': api_key,
                        'secret': api_secret
                    }
                    if new_exchange == 'bitmart':
                        credentials['uid'] = api_uid

                    with st.spinner("Testing connection..."):
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        portfolio = loop.run_until_complete(fetch_portfolio(new_exchange, credentials))
                        loop.close()

                        if portfolio is not None:
                            save_cex_credentials(new_exchange, credentials)
                            st.success(f"✅ Connected to {new_exchange.upper()} successfully!")
                            st.session_state.exchange_connected = True
                            st.session_state.portfolio_data = portfolio
                            st.rerun()
                        else:
                            st.error("❌ Failed to connect. Please check your credentials.")

    # Trading Parameters
    st.markdown("---")
    st.subheader("Trading Parameters")

    reference_mode = st.radio(
        "Reference Price Mode",
        options=['dex', 'cex'],
        format_func=lambda x: 'DEX Reference (PancakeSwap - Immediate rebalance)' if x == 'dex' else 'CEX Reference (Exchange mid-price - 2min delay)',
        horizontal=True
    )
    st.session_state.bot_config['reference_mode'] = reference_mode

    col_a, col_b = st.columns(2)

    with col_a:
        spread_pct = st.number_input(
            "Spread Percentage (%)",
            min_value=0.1,
            max_value=10.0,
            value=st.session_state.bot_config['spread_percentage'],
            step=0.1
        )
        st.session_state.bot_config['spread_percentage'] = spread_pct

    with col_b:
        order_amount = st.number_input(
            "Order Amount (USD)",
            min_value=10,
            max_value=10000,
            value=st.session_state.bot_config['order_amount_usd'],
            step=100
        )
        st.session_state.bot_config['order_amount_usd'] = order_amount

    # Bot Control
    st.markdown("---")
    st.subheader("Bot Control")

    col_start, col_stop = st.columns(2)

    with col_start:
        start_disabled = st.session_state.bot_running or st.session_state.bot_config['selected_exchange'] is None

        if st.button("🚀 Start Bot", type="primary", disabled=start_disabled, use_container_width=True):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(initialize_bot())
            loop.close()

            if success:
                st.session_state.bot_running = True
                st.success("Bot started successfully!")
                st.rerun()
            else:
                st.error("Failed to start bot. Check logs.")

    with col_stop:
        if st.button("🛑 Stop Bot", type="secondary", disabled=not st.session_state.bot_running, use_container_width=True):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(shutdown_bot())
            loop.close()

            st.session_state.bot_running = False
            st.info("Bot stopped")
            st.rerun()

with tab2:
    # Price Fetching
    with st.spinner("Fetching live prices..."):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        dex_price = loop.run_until_complete(fetch_dex_price())
        if dex_price:
            st.session_state.dex_price = dex_price

        if st.session_state.bot_config['selected_exchange']:
            trading_pair = 'LANDSHARE/USDT' if st.session_state.bot_config['selected_exchange'] == 'gateio' else 'LAND/USDT'
            cex_price = loop.run_until_complete(fetch_cex_price(st.session_state.bot_config['selected_exchange'], trading_pair))
            if cex_price:
                st.session_state.cex_price = cex_price

        loop.close()

    # Live Price Data
    st.subheader("💰 Live Price Data")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.session_state.dex_price:
            st.metric("DEX Price", f"${st.session_state.dex_price:.6f}")
        else:
            st.metric("DEX Price", "Loading...")

    with col2:
        if st.session_state.cex_price:
            st.metric("CEX Price", f"${st.session_state.cex_price:.6f}")
        else:
            st.metric("CEX Price", "N/A")

    with col3:
        if st.session_state.dex_price and st.session_state.cex_price:
            divergence = abs(st.session_state.dex_price - st.session_state.cex_price) / st.session_state.dex_price
            st.metric("Price Divergence", f"{divergence:.2%}")
        else:
            st.metric("Price Divergence", "N/A")

    with col4:
        reference_price = st.session_state.dex_price if reference_mode == 'dex' else st.session_state.cex_price
        if reference_price:
            spread = spread_pct / 100
            buy_price = reference_price * (1 - spread)
            sell_price = reference_price * (1 + spread)
            st.metric("Order Range", f"${buy_price:.6f} - ${sell_price:.6f}")
        else:
            st.metric("Order Range", "N/A")

    # Active Orders
    st.markdown("---")
    st.subheader("📊 Active Orders")

    if st.session_state.bot_running:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot_cycle())
        loop.close()

        if st.session_state.active_orders:
            orders_data = []
            for order in st.session_state.active_orders:
                orders_data.append({
                    'Order ID': order.get('id', 'N/A')[:12] + '...',
                    'Side': order.get('side', 'N/A').upper(),
                    'Price': f"${order.get('price', 0):.6f}",
                    'Amount': f"{order.get('amount', 0):.2f}",
                    'Filled': f"{order.get('filled', 0):.2f}",
                    'Status': order.get('status', 'N/A').upper(),
                    'Time': datetime.fromtimestamp(order.get('timestamp', 0) / 1000).strftime('%H:%M:%S') if order.get('timestamp') else 'N/A'
                })

            df_orders = pd.DataFrame(orders_data)
            st.dataframe(df_orders, use_container_width=True, hide_index=True)
        else:
            st.warning("No active orders")
    else:
        st.info("📌 Start the bot to place orders")

    # Logs
    st.markdown("---")
    st.subheader("📝 Bot Logs")

    if st.session_state.bot_logs:
        log_container = st.container()
        with log_container:
            for log in reversed(st.session_state.bot_logs[-20:]):
                st.text(log)
    else:
        st.info("No logs yet")

with tab3:
    st.subheader("💼 Portfolio Balance")

    if st.session_state.bot_config['selected_exchange']:
        if st.button("🔄 Refresh Portfolio", use_container_width=True):
            credentials = load_cex_credentials(st.session_state.bot_config['selected_exchange'])

            with st.spinner("Fetching portfolio..."):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                portfolio = loop.run_until_complete(fetch_portfolio(st.session_state.bot_config['selected_exchange'], credentials))
                loop.close()

                if portfolio:
                    st.session_state.portfolio_data = portfolio
                    st.session_state.exchange_connected = True
                else:
                    st.error("Failed to fetch portfolio")

        if st.session_state.portfolio_data:
            st.success(f"✅ Connected to {st.session_state.bot_config['selected_exchange'].upper()}")

            portfolio_list = []
            for currency, amounts in st.session_state.portfolio_data.items():
                portfolio_list.append({
                    'Asset': currency,
                    'Free': f"{amounts['free']:.8f}",
                    'Used': f"{amounts['used']:.8f}",
                    'Total': f"{amounts['total']:.8f}"
                })

            df_portfolio = pd.DataFrame(portfolio_list)
            st.dataframe(df_portfolio, use_container_width=True, hide_index=True)
        else:
            st.info("Click 'Refresh Portfolio' to view your balances")
    else:
        st.warning("Please select an exchange first")

# Auto-refresh
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

import time
if st.session_state.bot_running:
    time.sleep(st.session_state.dynamic_interval)
else:
    time.sleep(5)

st.rerun()
