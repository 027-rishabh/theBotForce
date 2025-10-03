
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import asyncio
import threading
import time
from datetime import datetime, timedelta
import json
import os

# Import the bot class (in real implementation, this would be a separate file)
# from dex_cex_bot import DEXCEXArbitrageBot

# Page configuration
st.set_page_config(
    page_title="DEX/CEX Arbitrage Trading Bot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
    }
    .status-running {
        color: #28a745;
        font-weight: bold;
    }
    .status-stopped {
        color: #dc3545;
        font-weight: bold;
    }
    .alert-box {
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
    }
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
    }
    .alert-danger {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'bot_instance' not in st.session_state:
    st.session_state.bot_instance = None
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False
if 'config' not in st.session_state:
    st.session_state.config = {
        'symbols': ['BTC/USDT', 'ETH/USDT'],
        'max_position_size': 0.01,
        'price_threshold': 0.02,
        'rebalance_delay': 120,
        'spread_range': 0.02,
        'portfolio_value': 10000,
        'min_quantity': 0.001,
        'max_quantity': 1.0,
        'sandbox_mode': True
    }

# Main title and description
st.title("🤖 DEX/CEX Arbitrage Trading Bot")
st.markdown("""
**Automated trading bot that monitors price differences between Decentralized Exchanges (DEX) and Centralized Exchanges (CEX)**

This bot places buy and sell orders on CEX within a 2% range based on DEX prices, and automatically rebalances orders when DEX price moves by 2% or more.
""")

# Sidebar for configuration
st.sidebar.title("⚙️ Bot Configuration")

# Exchange Configuration
st.sidebar.subheader("🏦 Exchange Settings")
cex_exchange = st.sidebar.selectbox(
    "CEX Exchange",
    ["Binance", "Coinbase Pro", "Kraken", "FTX", "KuCoin"],
    help="Select the centralized exchange for order placement"
)

dex_source = st.sidebar.selectbox(
    "DEX Data Source",
    ["Uniswap", "SushiSwap", "PancakeSwap", "1inch Aggregator"],
    help="Select the decentralized exchange for price monitoring"
)

# API Configuration
st.sidebar.subheader("🔑 API Configuration")
cex_api_key = st.sidebar.text_input(
    "CEX API Key",
    type="password",
    help="Your centralized exchange API key"
)

cex_secret = st.sidebar.text_input(
    "CEX API Secret",
    type="password",
    help="Your centralized exchange API secret"
)

dex_api_key = st.sidebar.text_input(
    "DEX API Key (if required)",
    type="password",
    help="API key for DEX data source (if required)"
)

# Trading Parameters
st.sidebar.subheader("📊 Trading Parameters")

symbols = st.sidebar.multiselect(
    "Trading Symbols",
    ["BTC/USDT", "ETH/USDT", "ADA/USDT", "DOT/USDT", "LINK/USDT", "UNI/USDT"],
    default=st.session_state.config['symbols'],
    help="Select cryptocurrency pairs to monitor"
)

portfolio_value = st.sidebar.number_input(
    "Portfolio Value ($)",
    min_value=1000,
    max_value=1000000,
    value=st.session_state.config['portfolio_value'],
    help="Total portfolio value for position sizing"
)

max_position_size = st.sidebar.slider(
    "Max Position Size (%)",
    min_value=0.1,
    max_value=5.0,
    value=st.session_state.config['max_position_size'] * 100,
    step=0.1,
    help="Maximum percentage of portfolio per position"
) / 100

# Risk Management
st.sidebar.subheader("⚠️ Risk Management")

price_threshold = st.sidebar.slider(
    "Price Movement Threshold (%)",
    min_value=1.0,
    max_value=10.0,
    value=st.session_state.config['price_threshold'] * 100,
    step=0.1,
    help="Price movement percentage to trigger order rebalancing"
) / 100

spread_range = st.sidebar.slider(
    "Order Spread Range (%)",
    min_value=0.5,
    max_value=5.0,
    value=st.session_state.config['spread_range'] * 100,
    step=0.1,
    help="Price range around DEX price for order placement"
) / 100

rebalance_delay = st.sidebar.slider(
    "Rebalance Delay (seconds)",
    min_value=60,
    max_value=600,
    value=st.session_state.config['rebalance_delay'],
    step=30,
    help="Wait time before rebalancing orders after price movement"
)

sandbox_mode = st.sidebar.checkbox(
    "Sandbox Mode",
    value=st.session_state.config['sandbox_mode'],
    help="Run bot in sandbox/paper trading mode"
)

# Update configuration
st.session_state.config.update({
    'symbols': symbols,
    'max_position_size': max_position_size,
    'price_threshold': price_threshold,
    'rebalance_delay': rebalance_delay,
    'spread_range': spread_range,
    'portfolio_value': portfolio_value,
    'sandbox_mode': sandbox_mode,
    'cex_exchange': cex_exchange,
    'dex_source': dex_source,
    'cex_api_key': cex_api_key,
    'cex_secret': cex_secret,
    'dex_api_key': dex_api_key
})

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎛️ Bot Control")

    # Bot control buttons
    col_start, col_stop, col_status = st.columns(3)

    with col_start:
        if st.button("🚀 Start Bot", type="primary", disabled=st.session_state.bot_running):
            if not symbols:
                st.error("Please select at least one trading symbol")
            elif not cex_api_key or not cex_secret:
                st.error("Please provide CEX API credentials")
            else:
                # In real implementation, initialize and start the bot here
                st.session_state.bot_running = True
                st.success("Bot started successfully!")
                st.rerun()

    with col_stop:
        if st.button("⏹️ Stop Bot", disabled=not st.session_state.bot_running):
            # In real implementation, stop the bot here
            st.session_state.bot_running = False
            st.info("Bot stopped successfully!")
            st.rerun()

    with col_status:
        if st.session_state.bot_running:
            st.markdown('<p class="status-running">🟢 Running</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-stopped">🔴 Stopped</p>', unsafe_allow_html=True)

with col2:
    st.subheader("📊 Quick Stats")

    # Simulate some metrics for demo
    if st.session_state.bot_running:
        active_orders = 4
        total_profit = 156.78
        success_rate = 78.5
    else:
        active_orders = 0
        total_profit = 0
        success_rate = 0

    st.metric("Active Orders", active_orders)
    st.metric("Total Profit", f"${total_profit:.2f}", delta=f"+{total_profit*.1:.2f}")
    st.metric("Success Rate", f"{success_rate:.1f}%")

# Price monitoring section
st.subheader("💹 Price Monitoring")

if symbols:
    # Create sample price data for visualization
    import numpy as np

    tabs = st.tabs(symbols)

    for i, symbol in enumerate(symbols):
        with tabs[i]:
            col_price, col_chart = st.columns([1, 2])

            with col_price:
                # Simulate current prices
                base_price = 50000 if 'BTC' in symbol else 3000
                dex_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
                cex_price = base_price * (1 + np.random.uniform(-0.02, 0.02))
                price_diff = (dex_price - cex_price) / cex_price * 100

                st.metric("DEX Price", f"${dex_price:.2f}")
                st.metric("CEX Price", f"${cex_price:.2f}")
                st.metric("Price Difference", f"{price_diff:.2f}%", 
                         delta=f"{price_diff:.2f}%" if price_diff > 0 else None)

            with col_chart:
                # Create sample chart data
                timestamps = pd.date_range(
                    start=datetime.now() - timedelta(hours=24), 
                    end=datetime.now(), 
                    freq='5T'
                )

                dex_prices = base_price + np.cumsum(np.random.randn(len(timestamps)) * 50)
                cex_prices = dex_prices + np.random.randn(len(timestamps)) * 20

                df = pd.DataFrame({
                    'timestamp': timestamps,
                    'dex_price': dex_prices,
                    'cex_price': cex_prices
                })

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['timestamp'], 
                    y=df['dex_price'],
                    mode='lines',
                    name='DEX Price',
                    line=dict(color='#1f77b4')
                ))
                fig.add_trace(go.Scatter(
                    x=df['timestamp'], 
                    y=df['cex_price'],
                    mode='lines',
                    name='CEX Price',
                    line=dict(color='#ff7f0e')
                ))

                fig.update_layout(
                    title=f"{symbol} Price Comparison (24h)",
                    xaxis_title="Time",
                    yaxis_title="Price ($)",
                    height=300,
                    showlegend=True
                )

                st.plotly_chart(fig, use_container_width=True)

# Orders section
st.subheader("📋 Order Management")

# Create sample order data
if st.session_state.bot_running:
    sample_orders = [
        {
            'Order ID': 'buy_BTC_001',
            'Symbol': 'BTC/USDT',
            'Side': 'BUY',
            'Price': '$49,850.00',
            'Quantity': '0.002',
            'Status': 'Open',
            'Timestamp': '2025-10-03 16:30:15'
        },
        {
            'Order ID': 'sell_BTC_001',
            'Symbol': 'BTC/USDT',
            'Side': 'SELL',
            'Price': '$50,150.00',
            'Quantity': '0.002',
            'Status': 'Open',
            'Timestamp': '2025-10-03 16:30:15'
        },
        {
            'Order ID': 'buy_ETH_001',
            'Symbol': 'ETH/USDT',
            'Side': 'BUY',
            'Price': '$2,985.00',
            'Quantity': '0.05',
            'Status': 'Filled',
            'Timestamp': '2025-10-03 16:25:42'
        }
    ]

    df_orders = pd.DataFrame(sample_orders)

    # Add color coding for status
    def color_status(val):
        if val == 'Open':
            return 'color: orange'
        elif val == 'Filled':
            return 'color: green'
        elif val == 'Cancelled':
            return 'color: red'
        return ''

    styled_df = df_orders.style.applymap(color_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True)

else:
    st.info("Start the bot to see active orders")

# Logs section
st.subheader("📝 Bot Logs")

if st.session_state.bot_running:
    sample_logs = [
        "🟢 [16:30:15] Bot started successfully",
        "📊 [16:30:16] Connected to Binance CEX",
        "🔗 [16:30:17] Connected to Uniswap DEX data source",
        "📈 [16:30:20] Monitoring BTC/USDT - DEX: $50,000, CEX: $49,950",
        "📋 [16:30:21] Placed buy order: BTC/USDT @ $49,850",
        "📋 [16:30:21] Placed sell order: BTC/USDT @ $50,150",
        "⏰ [16:32:45] Price movement detected for BTC/USDT: 2.1%",
        "🔄 [16:32:45] Scheduling order rebalance for BTC/USDT"
    ]

    log_container = st.container()
    with log_container:
        for log in reversed(sample_logs[-10:]):  # Show last 10 logs
            st.text(log)
else:
    st.info("Start the bot to see logs")

# Configuration export/import
st.subheader("⚙️ Configuration Management")

col_export, col_import = st.columns(2)

with col_export:
    if st.button("📥 Export Configuration"):
        config_json = json.dumps(st.session_state.config, indent=2)
        st.download_button(
            label="Download config.json",
            data=config_json,
            file_name="bot_config.json",
            mime="application/json"
        )

with col_import:
    uploaded_file = st.file_uploader("📤 Import Configuration", type=['json'])
    if uploaded_file is not None:
        try:
            config_data = json.load(uploaded_file)
            st.session_state.config.update(config_data)
            st.success("Configuration imported successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error importing configuration: {e}")

# Footer
st.markdown("---")
st.markdown(
    "⚠️ **Disclaimer**: This is a demo trading bot. "
    "Always test with paper trading before using real funds. "
    "Cryptocurrency trading carries high risk."
)

# Auto-refresh for real-time updates (optional)
if st.session_state.bot_running:
    time.sleep(5)
    st.rerun()
