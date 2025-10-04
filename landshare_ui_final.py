"""
LANDSHARE Market Maker Bot - Final UI
Single-page layout with authentication, all 5 exchanges, and public CEX data
"""

import streamlit as st
import pandas as pd
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
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
    .section-header {
        background: linear-gradient(90deg, #1f77b4 0%, #0ea5e9 100%);
        color: white;
        padding: 10px 15px;
        border-radius: 5px;
        margin: 15px 0 10px 0;
        font-weight: bold;
    }
    .cex-card {
        background-color: #f0f9ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #0ea5e9;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Config files
AUTH_CONFIG_FILE = Path("auth_config.json")
CEX_CONFIG_FILE = Path("cex_credentials.json")

# Helper functions
def load_json_config(file_path):
    if file_path.exists():
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_json_config(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2)

def verify_login(username, password):
    auth_config = load_json_config(AUTH_CONFIG_FILE)
    users = auth_config.get('users', {})
    if username in users:
        if users[username].get('password') == password:
            return True
    return False

def save_cex_credentials(exchange_name, credentials):
    config = load_json_config(CEX_CONFIG_FILE)
    if 'exchanges' not in config:
        config['exchanges'] = {}
    config['exchanges'][exchange_name] = credentials
    save_json_config(CEX_CONFIG_FILE, config)

def load_cex_credentials(exchange_name):
    config = load_json_config(CEX_CONFIG_FILE)
    return config.get('exchanges', {}).get(exchange_name, {})

def get_all_saved_exchanges():
    config = load_json_config(CEX_CONFIG_FILE)
    return list(config.get('exchanges', {}).keys())

# Session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Login
if not st.session_state.authenticated:
    st.title("🔐 LANDSHARE Market Maker - Login")
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
                    st.error("Invalid credentials")
    st.stop()

# Initialize session after authentication
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'bot_config' not in st.session_state:
    st.session_state.bot_config = {
        'reference_mode': 'dex',
        'selected_exchange': None,
        'spread_percentage': 1.5,
        'order_amount_usd': 1000
    }
if 'dex_price' not in st.session_state:
    st.session_state.dex_price = None
if 'cex_prices' not in st.session_state:
    st.session_state.cex_prices = {}
if 'portfolio_data' not in st.session_state:
    st.session_state.portfolio_data = None
if 'active_orders' not in st.session_state:
    st.session_state.active_orders = []
if 'market_maker_instance' not in st.session_state:
    st.session_state.market_maker_instance = None
if 'bot_logs' not in st.session_state:
    st.session_state.bot_logs = []
if 'dynamic_interval' not in st.session_state:
    st.session_state.dynamic_interval = 60

# Helper functions
async def fetch_dex_price():
    try:
        config = {
            'token': {'contract_address': '0x9d986A3f147212327DD658F712d5264a73a1fdB0', 'trading_pair': 'LAND/USDT'},
            'dex': {'api_url': 'https://api.pancakeswap.info/api/v2', 'websocket_url': 'wss://bsc-ws-node.nariox.org:443', 'pair': 'LAND/WBNB'}
        }
        land_manager = LANDTokenManager(config)
        await land_manager.initialize()
        dex_price = await land_manager.get_land_usdt_price()
        await land_manager.close()
        return dex_price
    except Exception as e:
        logging.error(f"DEX price error: {e}")
        return None

async def fetch_cex_price(exchange_name, trading_pair='LAND/USDT'):
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({'enableRateLimit': True})
        await exchange.load_markets()

        pairs_to_try = [trading_pair, 'LANDSHARE/USDT', 'LAND/USD']
        ticker = None

        for pair in pairs_to_try:
            if pair in exchange.markets:
                ticker = await exchange.fetch_ticker(pair)
                break

        cex_price = ticker['last'] if ticker and 'last' in ticker else None
        await exchange.close()
        return cex_price
    except Exception as e:
        return None

async def fetch_portfolio(exchange_name, credentials):
    try:
        exchange_class = getattr(ccxt, exchange_name)
        exchange_config = {
            'apiKey': credentials.get('api_key', ''),
            'secret': credentials.get('secret', ''),
            'enableRateLimit': True
        }

        if exchange_name == 'gateio' and credentials.get('password'):
            exchange_config['password'] = credentials['password']
        elif exchange_name == 'bitmart':
            exchange_config['uid'] = credentials.get('uid', '')
            if credentials.get('memo'):
                exchange_config['password'] = credentials['memo']
        elif exchange_name == 'ascendex':
            exchange_config['uid'] = credentials.get('group_id', '')

        exchange = exchange_class(exchange_config)
        await exchange.load_markets()
        balance = await exchange.fetch_balance()

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
        logging.error(f"Portfolio fetch error for {exchange_name}: {e}")
        return None

def add_log(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    log_entry = f"[{timestamp}] {message}"
    st.session_state.bot_logs.append(log_entry)
    if len(st.session_state.bot_logs) > 50:
        st.session_state.bot_logs = st.session_state.bot_logs[-50:]

def create_bot_config():
    exchange_name = st.session_state.bot_config['selected_exchange']
    credentials = load_cex_credentials(exchange_name)

    trading_pair = 'LANDSHARE/USDT' if exchange_name == 'gateio' else 'LAND/USDT'

    config = {
        'token': {'symbol': 'LAND', 'trading_pair': trading_pair, 'contract_address': '0x9d986A3f147212327DD658F712d5264a73a1fdB0', 'blockchain': 'BSC'},
        'dex': {'name': 'pancakeswap', 'api_url': 'https://api.pancakeswap.info/api/v2', 'websocket_url': 'wss://bsc-ws-node.nariox.org:443', 'pair': 'LAND/WBNB'},
        'cex': {'selected_exchange': exchange_name},
        'api_credentials': {
            f'{exchange_name}_api_key': credentials.get('api_key', ''),
            f'{exchange_name}_secret': credentials.get('secret', ''),
        },
        'reference_mode': {'use_dex_reference': st.session_state.bot_config['reference_mode'] == 'dex', 'sync_interval': 60},
        'market_making': {'spread_percentage': st.session_state.bot_config['spread_percentage'], 'order_amount_usd': st.session_state.bot_config['order_amount_usd'], 'order_count': 1, 'post_only': True, 'refresh_interval': st.session_state.dynamic_interval},
        'fill_handling': {'dex_mode_delay': 0, 'cex_mode_delay': 120, 'immediate_rebalance': True},
        'risk_management': {'max_inventory_skew': 0.3, 'max_position_usd': 5000, 'max_daily_trades': 200},
        'system': {'log_level': 'INFO'}
    }

    if exchange_name == 'gateio' and credentials.get('password'):
        config['api_credentials'][f'{exchange_name}_password'] = credentials['password']
    elif exchange_name == 'bitmart':
        config['api_credentials'][f'{exchange_name}_uid'] = credentials.get('uid', '')
        if credentials.get('memo'):
            config['api_credentials'][f'{exchange_name}_memo'] = credentials['memo']
    elif exchange_name == 'ascendex':
        config['api_credentials'][f'{exchange_name}_group_id'] = credentials.get('group_id', '')

    return config

async def run_bot_cycle():
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
            add_log(f"✅ Placed {len(open_orders)} orders")

            fills = await market_maker.check_fills()
            if fills:
                for fill in fills:
                    add_log(f"🎯 Filled: {fill['side'].upper()} {fill['filled_amount']:.2f} @ ${fill['filled_price']:.6f}")
                    await market_maker.fill_handler.handle_fill(fill)
        else:
            add_log("❌ Failed to place orders")
    except Exception as e:
        add_log(f"❌ Cycle error: {str(e)}")

async def initialize_bot():
    try:
        add_log("🚀 Initializing bot...")
        config = create_bot_config()

        land_manager = LANDTokenManager(config)
        cex_manager = MultiCEXManager(config)

        await land_manager.initialize()
        await cex_manager.initialize()

        add_log(f"✅ Connected to {config['cex']['selected_exchange'].upper()}")

        reference_engine = ReferencePriceEngine(config, land_manager, cex_manager)
        market_maker = MarketMakerEngine(config, reference_engine, cex_manager)

        st.session_state.market_maker_instance = market_maker
        add_log("✅ Bot initialized")
        return True
    except Exception as e:
        add_log(f"❌ Init failed: {str(e)}")
        return False

async def shutdown_bot():
    try:
        if st.session_state.market_maker_instance:
            market_maker = st.session_state.market_maker_instance
            add_log("Cancelling orders...")
            trading_pair = market_maker.trading_pair
            cancelled = await market_maker.cex_manager.cancel_all_orders(trading_pair)
            add_log(f"✅ Cancelled {cancelled} orders")

            await market_maker.reference_engine.land_manager.close()
            await market_maker.cex_manager.close()

            st.session_state.market_maker_instance = None
            st.session_state.active_orders = []
            add_log("✅ Shutdown complete")
    except Exception as e:
        add_log(f"❌ Shutdown error: {str(e)}")

# Sidebar
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

    st.markdown("---")
    if st.session_state.bot_running:
        st.success("🟢 Bot Running")
    else:
        st.error("🔴 Bot Stopped")

    if st.session_state.dex_price:
        st.metric("DEX Price", f"${st.session_state.dex_price:.6f}")

# Main content
st.title("LANDSHARE Market Maker Bot")
st.markdown("Automated market making with multi-exchange support")

# SECTION 1: CEX PRICES (PUBLIC - NO KEYS NEEDED)
st.markdown('<div class="section-header">📊 Live CEX Prices (Public Data)</div>', unsafe_allow_html=True)

with st.spinner("Fetching CEX prices..."):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    exchanges = ['mexc', 'gateio', 'bitmart', 'ascendex', 'bingx']
    for ex in exchanges:
        trading_pair = 'LANDSHARE/USDT' if ex == 'gateio' else 'LAND/USDT'
        price = loop.run_until_complete(fetch_cex_price(ex, trading_pair))
        st.session_state.cex_prices[ex] = price

    loop.close()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    price = st.session_state.cex_prices.get('mexc')
    st.metric("MEXC", f"${price:.6f}" if price else "N/A")
with col2:
    price = st.session_state.cex_prices.get('gateio')
    st.metric("Gate.io", f"${price:.6f}" if price else "N/A")
with col3:
    price = st.session_state.cex_prices.get('bitmart')
    st.metric("BitMart", f"${price:.6f}" if price else "N/A")
with col4:
    price = st.session_state.cex_prices.get('ascendex')
    st.metric("AscendEX", f"${price:.6f}" if price else "N/A")
with col5:
    price = st.session_state.cex_prices.get('bingx')
    st.metric("BingX", f"${price:.6f}" if price else "N/A")

# SECTION 2: EXCHANGE CONFIGURATION
st.markdown('<div class="section-header">🔧 Exchange Configuration</div>', unsafe_allow_html=True)

saved_exchanges = get_all_saved_exchanges()

col_sel, col_add = st.columns([3, 1])
with col_sel:
    if saved_exchanges:
        selected_exchange = st.selectbox(
            "Select Exchange",
            options=saved_exchanges,
            format_func=lambda x: {'mexc': 'MEXC', 'gateio': 'Gate.io', 'bitmart': 'BitMart', 'ascendex': 'AscendEX', 'bingx': 'BingX'}.get(x, x.upper())
        )
        st.session_state.bot_config['selected_exchange'] = selected_exchange
    else:
        st.info("No exchanges configured")
        st.session_state.bot_config['selected_exchange'] = None

with col_add:
    st.markdown("<br>", unsafe_allow_html=True)
    add_new = st.button("➕ Add Exchange", use_container_width=True)

# Add Exchange Form
if add_new or not saved_exchanges:
    st.markdown("#### Add New Exchange")
    with st.form("add_exchange_form"):
        new_ex = st.selectbox("Exchange", ['mexc', 'gateio', 'bitmart', 'ascendex', 'bingx'],
                               format_func=lambda x: {'mexc': 'MEXC', 'gateio': 'Gate.io', 'bitmart': 'BitMart', 'ascendex': 'AscendEX', 'bingx': 'BingX'}[x])

        api_key = st.text_input("API Key", type="password")
        api_secret = st.text_input("Secret Key", type="password")

        # Exchange-specific fields
        api_password, api_uid, api_memo, api_group_id = None, None, None, None

        if new_ex == 'gateio':
            api_password = st.text_input("Password (optional)", type="password")
        elif new_ex == 'bitmart':
            api_uid = st.text_input("UID")
            api_memo = st.text_input("Memo", type="password")
        elif new_ex == 'ascendex':
            api_group_id = st.text_input("Group ID")

        connect_btn = st.form_submit_button("Connect & Save", use_container_width=True)

        if connect_btn:
            if not api_key or not api_secret:
                st.error("API Key and Secret required")
            elif new_ex == 'bitmart' and (not api_uid or not api_memo):
                st.error("UID and Memo required for BitMart")
            elif new_ex == 'ascendex' and not api_group_id:
                st.error("Group ID required for AscendEX")
            else:
                credentials = {'api_key': api_key, 'secret': api_secret}
                if api_password:
                    credentials['password'] = api_password
                if api_uid:
                    credentials['uid'] = api_uid
                if api_memo:
                    credentials['memo'] = api_memo
                if api_group_id:
                    credentials['group_id'] = api_group_id

                with st.spinner("Testing connection..."):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    portfolio = loop.run_until_complete(fetch_portfolio(new_ex, credentials))
                    loop.close()

                    if portfolio is not None:
                        save_cex_credentials(new_ex, credentials)
                        st.success(f"✅ Connected to {new_ex.upper()}!")
                        st.session_state.portfolio_data = portfolio
                        st.rerun()
                    else:
                        st.error("❌ Connection failed")

# SECTION 3: PORTFOLIO
if st.session_state.bot_config['selected_exchange']:
    st.markdown('<div class="section-header">💼 Portfolio Balance</div>', unsafe_allow_html=True)

    if st.button("🔄 Refresh Portfolio", use_container_width=True):
        credentials = load_cex_credentials(st.session_state.bot_config['selected_exchange'])

        with st.spinner("Fetching portfolio..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            portfolio = loop.run_until_complete(fetch_portfolio(st.session_state.bot_config['selected_exchange'], credentials))
            loop.close()

            if portfolio:
                st.session_state.portfolio_data = portfolio
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

# SECTION 4: TRADING CONFIGURATION
st.markdown('<div class="section-header">⚙️ Trading Parameters</div>', unsafe_allow_html=True)

col_ref, col_spread, col_amount = st.columns(3)

with col_ref:
    ref_mode = st.radio("Reference Mode", ['dex', 'cex'],
                        format_func=lambda x: 'DEX (Immediate)' if x == 'dex' else 'CEX (2min delay)',
                        horizontal=True)
    st.session_state.bot_config['reference_mode'] = ref_mode

with col_spread:
    spread = st.number_input("Spread %", min_value=0.1, max_value=10.0, value=1.5, step=0.1)
    st.session_state.bot_config['spread_percentage'] = spread

with col_amount:
    amount = st.number_input("Order Amount $", min_value=10, max_value=10000, value=1000, step=100)
    st.session_state.bot_config['order_amount_usd'] = amount

# Bot Control
col_start, col_stop = st.columns(2)
with col_start:
    start_disabled = st.session_state.bot_running or not st.session_state.bot_config['selected_exchange']
    if st.button("🚀 Start Bot", type="primary", disabled=start_disabled, use_container_width=True):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(initialize_bot())
        loop.close()

        if success:
            st.session_state.bot_running = True
            st.success("Bot started!")
            st.rerun()
        else:
            st.error("Failed to start")

with col_stop:
    if st.button("🛑 Stop Bot", type="secondary", disabled=not st.session_state.bot_running, use_container_width=True):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(shutdown_bot())
        loop.close()

        st.session_state.bot_running = False
        st.info("Bot stopped")
        st.rerun()

# SECTION 5: LIVE TRADING
st.markdown('<div class="section-header">📈 Live Trading</div>', unsafe_allow_html=True)

# Fetch DEX price
with st.spinner("Fetching prices..."):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    dex_price = loop.run_until_complete(fetch_dex_price())
    if dex_price:
        st.session_state.dex_price = dex_price
    loop.close()

# Get CEX price for selected exchange
cex_price = None
if st.session_state.bot_config['selected_exchange']:
    cex_price = st.session_state.cex_prices.get(st.session_state.bot_config['selected_exchange'])

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("DEX Price", f"${st.session_state.dex_price:.6f}" if st.session_state.dex_price else "N/A")
with col2:
    st.metric("CEX Price", f"${cex_price:.6f}" if cex_price else "N/A")
with col3:
    if st.session_state.dex_price and cex_price:
        div = abs(st.session_state.dex_price - cex_price) / st.session_state.dex_price
        st.metric("Divergence", f"{div:.2%}")
    else:
        st.metric("Divergence", "N/A")
with col4:
    ref_price = st.session_state.dex_price if ref_mode == 'dex' else cex_price
    if ref_price:
        buy_p = ref_price * (1 - spread / 100)
        sell_p = ref_price * (1 + spread / 100)
        st.metric("Order Range", f"${buy_p:.6f} - ${sell_p:.6f}")
    else:
        st.metric("Order Range", "N/A")

# Active Orders
st.markdown("#### 📊 Active Orders")

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
                'Status': order.get('status', 'N/A').upper()
            })

        df_orders = pd.DataFrame(orders_data)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
    else:
        st.warning("No active orders")
else:
    st.info("Start the bot to place orders")

# Logs
st.markdown("#### 📝 Bot Logs")
if st.session_state.bot_logs:
    for log in reversed(st.session_state.bot_logs[-15:]):
        st.text(log)
else:
    st.info("No logs yet")

# Auto-refresh
import time
if st.session_state.bot_running:
    time.sleep(st.session_state.dynamic_interval)
else:
    time.sleep(5)
st.rerun()
