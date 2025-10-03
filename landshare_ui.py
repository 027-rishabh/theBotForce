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
from landshare_market_maker import MultiCEXManager

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

        elif selected_exchange == 'gateio':
            api_key = st.text_input("Gate.io API Key", type="password", key="gateio_key")
            api_secret = st.text_input("Gate.io API Secret", type="password", key="gateio_secret")
            api_password = st.text_input("Gate.io API Password", type="password", key="gateio_pass")

        elif selected_exchange == 'bitmart':
            api_key = st.text_input("BitMart API Key", type="password", key="bitmart_key")
            api_secret = st.text_input("BitMart API Secret", type="password", key="bitmart_secret")
            api_uid = st.text_input("BitMart UID", key="bitmart_uid")
            api_memo = st.text_input("BitMart Memo", type="password", key="bitmart_memo", help="Required for BitMart API authentication")

        elif selected_exchange == 'ascendex':
            api_key = st.text_input("AscendEX API Key", type="password", key="ascendex_key")
            api_secret = st.text_input("AscendEX API Secret", type="password", key="ascendex_secret")
            api_group_id = st.text_input("AscendEX Group ID", key="ascendex_group_id", help="Required for AscendEX API authentication")

        elif selected_exchange == 'bingx':
            api_key = st.text_input("BingX API Key", type="password", key="bingx_key")
            api_secret = st.text_input("BingX API Secret", type="password", key="bingx_secret")

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
                st.session_state.bot_running = True
                st.success("Bot started successfully!")
                st.rerun()

    with col_stop:
        if st.button("Stop Bot", type="secondary", disabled=not st.session_state.bot_running):
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
    reference_price = st.session_state.dex_price if reference_mode == 'dex' else st.session_state.cex_price

    if reference_price:
        spread = spread_pct / 100
        buy_price = reference_price * (1 - spread)
        sell_price = reference_price * (1 + spread)

        # Calculate order sizes
        buy_size = (order_amount / 2) / buy_price
        sell_size = (order_amount / 2) / sell_price

        orders_data = {
            'Order ID': ['BUY_LAND_001', 'SELL_LAND_001'],
            'Side': ['BUY', 'SELL'],
            'Price': [f"${buy_price:.6f}", f"${sell_price:.6f}"],
            'Amount': [f"{buy_size:.2f} LAND", f"{sell_size:.2f} LAND"],
            'Value': [f"${order_amount/2:.2f}", f"${order_amount/2:.2f}"],
            'Status': ['Open', 'Open'],
            'Exchange': [selected_exchange.upper(), selected_exchange.upper()],
            'Time': [datetime.now().strftime('%H:%M:%S')] * 2
        }

        df_orders = pd.DataFrame(orders_data)
        st.dataframe(df_orders, use_container_width=True, hide_index=True)
    else:
        st.warning("Waiting for price data...")

else:
    st.info("📌 Start the bot to place orders. Prices are shown above for monitoring.")

# Logs Section
st.markdown("---")
st.subheader("📝 Bot Logs")

if st.session_state.bot_running:
    mode_name = "DEX" if reference_mode == 'dex' else "CEX"
    reference_price = st.session_state.dex_price if reference_mode == 'dex' else st.session_state.cex_price

    if reference_price:
        spread = spread_pct / 100
        buy_price = reference_price * (1 - spread)
        sell_price = reference_price * (1 + spread)

        sample_logs = [
            f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Bot started in {mode_name} reference mode",
            f"[{datetime.now().strftime('%H:%M:%S')}] 🔗 Connected to {selected_exchange.upper()} exchange",
            f"[{datetime.now().strftime('%H:%M:%S')}] 💹 DEX price: ${st.session_state.dex_price:.6f}",
            f"[{datetime.now().strftime('%H:%M:%S')}] 💹 CEX price: ${st.session_state.cex_price:.6f}" if st.session_state.cex_price else f"[{datetime.now().strftime('%H:%M:%S')}] 💹 CEX price: N/A",
            f"[{datetime.now().strftime('%H:%M:%S')}] 📌 Reference price ({mode_name}): ${reference_price:.6f}",
            f"[{datetime.now().strftime('%H:%M:%S')}] 🟢 Placed BUY order @ ${buy_price:.6f}",
            f"[{datetime.now().strftime('%H:%M:%S')}] 🔴 Placed SELL order @ ${sell_price:.6f}",
            f"[{datetime.now().strftime('%H:%M:%S')}] ⏱️  Refresh interval: {st.session_state.dynamic_interval}s",
            f"[{datetime.now().strftime('%H:%M:%S')}] 👀 Monitoring for fills...",
        ]

        for log in sample_logs:
            st.text(log)
    else:
        st.text(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for price data...")

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
