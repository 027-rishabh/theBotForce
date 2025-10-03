# Create deployment and quick-start scripts
deployment_script = """#!/usr/bin/env python3
\"\"\"
DEX/CEX Arbitrage Bot Deployment Script
Automated setup and deployment script for the trading bot
\"\"\"

import os
import sys
import subprocess
import json
import yaml
from pathlib import Path
import shutil

class BotDeployer:
    def __init__(self):
        self.project_dir = Path.cwd()
        self.venv_dir = self.project_dir / 'venv'
        self.config_file = self.project_dir / 'config.yaml'
        
    def print_banner(self):
        print(\"\"\"
╔═══════════════════════════════════════════════════════════╗
║           DEX/CEX Arbitrage Trading Bot Deployer         ║
║                     Setup Assistant                      ║
╚═══════════════════════════════════════════════════════════╝
        \"\"\")
    
    def check_python_version(self):
        \"\"\"Check if Python version is compatible\"\"\"
        if sys.version_info < (3, 8):
            print("❌ Python 3.8 or higher is required")
            print(f"Current version: {sys.version}")
            return False
        
        print(f"✅ Python version: {sys.version.split()[0]}")
        return True
    
    def create_virtual_environment(self):
        \"\"\"Create and activate virtual environment\"\"\"
        print("\\n🔧 Setting up virtual environment...")
        
        if self.venv_dir.exists():
            print("📁 Virtual environment already exists")
            response = input("Do you want to recreate it? (y/n): ")
            if response.lower() == 'y':
                shutil.rmtree(self.venv_dir)
            else:
                return True
        
        try:
            subprocess.run([sys.executable, '-m', 'venv', str(self.venv_dir)], check=True)
            print("✅ Virtual environment created successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create virtual environment: {e}")
            return False
    
    def install_dependencies(self):
        \"\"\"Install required Python packages\"\"\"
        print("\\n📦 Installing dependencies...")
        
        # Determine pip path based on OS
        if os.name == 'nt':  # Windows
            pip_path = self.venv_dir / 'Scripts' / 'pip'
        else:  # Linux/Mac
            pip_path = self.venv_dir / 'bin' / 'pip'
        
        try:
            # Upgrade pip first
            subprocess.run([str(pip_path), 'install', '--upgrade', 'pip'], check=True)
            
            # Install from requirements.txt
            subprocess.run([str(pip_path), 'install', '-r', 'requirements.txt'], check=True)
            
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ Requirements file not found")
            return False
    
    def setup_configuration(self):
        \"\"\"Interactive configuration setup\"\"\"
        print("\\n⚙️ Setting up bot configuration...")
        
        if self.config_file.exists():
            print("📁 Configuration file already exists")
            response = input("Do you want to reconfigure? (y/n): ")
            if response.lower() != 'y':
                return True
        
        config = {
            'cex_exchange': 'binance',
            'dex_source': 'coingecko',
            'symbols': ['BTC/USDT', 'ETH/USDT'],
            'max_position_size': 0.01,
            'price_threshold': 0.02,
            'rebalance_delay': 120,
            'spread_range': 0.02,
            'portfolio_value': 10000.0,
            'sandbox_mode': True,
            'log_level': 'INFO'
        }
        
        print("\\n📊 Exchange Configuration:")
        exchanges = ['binance', 'coinbase', 'kraken', 'kucoin']
        for i, exchange in enumerate(exchanges, 1):
            print(f"{i}. {exchange.title()}")
        
        choice = input(f"Select CEX exchange (1-{len(exchanges)}) [1]: ").strip() or "1"
        try:
            config['cex_exchange'] = exchanges[int(choice) - 1]
        except (ValueError, IndexError):
            config['cex_exchange'] = 'binance'
        
        print("\\n🔑 API Configuration (leave empty to skip):")
        api_key = input("CEX API Key: ").strip()
        if api_key:
            config['cex_api_key'] = api_key
            secret = input("CEX API Secret: ").strip()
            if secret:
                config['cex_secret'] = secret
        else:
            config['cex_api_key'] = ''
            config['cex_secret'] = ''
        
        print("\\n💰 Trading Configuration:")
        try:
            portfolio = input(f"Portfolio value in USD [{config['portfolio_value']}]: ").strip()
            if portfolio:
                config['portfolio_value'] = float(portfolio)
            
            position_size = input(f"Max position size % [{config['max_position_size']*100}]: ").strip()
            if position_size:
                config['max_position_size'] = float(position_size) / 100
        except ValueError:
            print("⚠️ Invalid input, using defaults")
        
        # Save configuration
        try:
            with open(self.config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            print("✅ Configuration saved successfully")
            return True
        except Exception as e:
            print(f"❌ Failed to save configuration: {e}")
            return False
    
    def create_startup_scripts(self):
        \"\"\"Create platform-specific startup scripts\"\"\"
        print("\\n📜 Creating startup scripts...")
        
        # Windows batch script
        windows_script = f'''@echo off
echo Starting DEX/CEX Arbitrage Bot...
cd /d "{self.project_dir}"
call venv\\Scripts\\activate
python main_bot.py
pause
'''
        
        # Linux/Mac shell script
        unix_script = f'''#!/bin/bash
echo "Starting DEX/CEX Arbitrage Bot..."
cd "{self.project_dir}"
source venv/bin/activate
python main_bot.py
'''
        
        try:
            # Windows script
            with open('start_bot.bat', 'w') as f:
                f.write(windows_script)
            
            # Unix script
            with open('start_bot.sh', 'w') as f:
                f.write(unix_script)
            
            # Make Unix script executable
            if os.name != 'nt':
                os.chmod('start_bot.sh', 0o755)
            
            print("✅ Startup scripts created")
            return True
        except Exception as e:
            print(f"❌ Failed to create startup scripts: {e}")
            return False
    
    def run_test(self):
        \"\"\"Run a quick test of the bot\"\"\"
        print("\\n🧪 Running bot test...")
        
        # Determine python path
        if os.name == 'nt':  # Windows
            python_path = self.venv_dir / 'Scripts' / 'python'
        else:  # Linux/Mac
            python_path = self.venv_dir / 'bin' / 'python'
        
        try:
            # Run a quick import test
            result = subprocess.run([
                str(python_path), '-c', 
                'import ccxt, yaml, pandas, numpy; print("All imports successful")'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print("✅ Bot dependencies test passed")
                return True
            else:
                print(f"❌ Test failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Test timed out")
            return False
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
    
    def print_instructions(self):
        \"\"\"Print final instructions\"\"\"
        print(\"\"\"
╔═══════════════════════════════════════════════════════════╗
║                    Setup Complete! 🎉                   ║
╚═══════════════════════════════════════════════════════════╝

🚀 To start the bot:

   Windows: double-click start_bot.bat
   Linux/Mac: ./start_bot.sh
   
   Or manually:
   1. Activate virtual environment:
      - Windows: venv\\Scripts\\activate
      - Linux/Mac: source venv/bin/activate
   2. Run bot: python main_bot.py

📊 To start the dashboard:
   streamlit run dex_cex_arbitrage_streamlit.py

⚙️ Configuration:
   - Edit config.yaml to modify settings
   - Add your API keys before live trading
   - Keep sandbox_mode: true for testing

⚠️  Important Notes:
   - Test thoroughly before live trading
   - Start with small position sizes
   - Monitor logs for errors
   - Understand the risks involved

📚 Documentation:
   - See DEX-CEX-Bot-Guide.md for detailed guide
   - Check logs/ directory for runtime logs
   - Visit exchange websites for API setup

Happy trading! 🤖📈
        \"\"\")
    
    def deploy(self):
        \"\"\"Main deployment process\"\"\"
        self.print_banner()
        
        # Check system requirements
        if not self.check_python_version():
            return False
        
        # Setup steps
        steps = [
            ("Create virtual environment", self.create_virtual_environment),
            ("Install dependencies", self.install_dependencies),
            ("Setup configuration", self.setup_configuration),
            ("Create startup scripts", self.create_startup_scripts),
            ("Run tests", self.run_test)
        ]
        
        for step_name, step_func in steps:
            print(f"\\n{'='*60}")
            print(f"Step: {step_name}")
            print('='*60)
            
            if not step_func():
                print(f"\\n❌ Deployment failed at: {step_name}")
                return False
        
        self.print_instructions()
        return True

def main():
    deployer = BotDeployer()
    
    try:
        success = deployer.deploy()
        if success:
            print("\\n🎉 Deployment completed successfully!")
            sys.exit(0)
        else:
            print("\\n❌ Deployment failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\\n\\n⏹️ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""

# Save deployment script
with open('deploy.py', 'w') as f:
    f.write(deployment_script)

# Create a demo/test script
demo_script = """#!/usr/bin/env python3
\"\"\"
DEX/CEX Arbitrage Bot Demo Script
Quick demonstration of bot functionality without real trading
\"\"\"

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
        print(\"\"\"
╔════════════════════════════════════════════════╗
║      DEX/CEX Arbitrage Bot Demo 🤖              ║
║      Simulated Trading Environment             ║
╚════════════════════════════════════════════════╝
        \"\"\")
    
    def simulate_price_update(self, symbol):
        \"\"\"Simulate price changes\"\"\"
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
        \"\"\"Check if arbitrage opportunity exists\"\"\"
        price_diff_pct = (dex_price - cex_price) / cex_price
        
        # Check if within 2% range
        if abs(price_diff_pct) <= 0.02:  # Within 2% range
            return True, price_diff_pct
        
        return False, price_diff_pct
    
    def calculate_order_prices(self, dex_price):
        \"\"\"Calculate buy/sell order prices\"\"\"
        spread = 0.02  # 2% spread
        buy_price = dex_price * (1 - spread/2)   # 1% below DEX
        sell_price = dex_price * (1 + spread/2)  # 1% above DEX
        
        return buy_price, sell_price
    
    def place_simulated_order(self, symbol, side, quantity, price):
        \"\"\"Place a simulated order\"\"\"
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
        \"\"\"Check for significant price movement\"\"\"
        # Simulate random significant movements
        if random.random() < 0.1:  # 10% chance of significant movement
            self.price_movements += 1
            return True
        return False
    
    async def run_demo_cycle(self):
        \"\"\"Run one demo cycle\"\"\"
        for symbol in self.demo_data.keys():
            # Simulate new prices
            dex_price, cex_price = self.simulate_price_update(symbol)
            
            # Display current prices
            price_diff = (dex_price - cex_price) / cex_price * 100
            print(f"\\n📊 {symbol}:")
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
            print(f"\\n📋 Active Orders: {len(open_orders)}")
            for order in open_orders[-3:]:  # Show last 3 orders
                print(f"   {order['side']:4} {order['symbol']:8} @ ${order['price']:8.2f} [{order['timestamp']}]")
    
    async def run_demo(self, cycles=10):
        \"\"\"Run the demo for specified cycles\"\"\"
        self.print_banner()
        
        print(f"🚀 Starting demo simulation...")
        print(f"📊 Will run for {cycles} cycles (about {cycles*3} seconds)")
        print(f"💡 This simulates the bot's trading logic without real trades\\n")
        
        self.running = True
        
        try:
            for cycle in range(1, cycles + 1):
                print(f"\\n{'='*50}")
                print(f"Demo Cycle {cycle}/{cycles}")
                print(f"{'='*50}")
                
                await self.run_demo_cycle()
                
                # Summary stats
                open_orders = len([o for o in self.orders if o['status'] == 'open'])
                print(f"\\n📈 Cycle Summary:")
                print(f"   Active orders: {open_orders}")
                print(f"   Total orders placed: {len(self.orders)}")
                print(f"   Price movements detected: {self.price_movements}")
                
                if cycle < cycles:
                    print("\\n⏳ Waiting 3 seconds for next cycle...")
                    await asyncio.sleep(3)
                    
        except KeyboardInterrupt:
            print("\\n\\n⏹️ Demo stopped by user")
        
        self.print_final_summary()
    
    def print_final_summary(self):
        \"\"\"Print final demo summary\"\"\"
        print(\"\"\"
╔════════════════════════════════════════════════╗
║              Demo Complete! 🎉                 ║
╚════════════════════════════════════════════════╝

📊 Demo Statistics:
\"\"\")
        
        open_orders = len([o for o in self.orders if o['status'] == 'open'])
        buy_orders = len([o for o in self.orders if o['side'] == 'BUY'])
        sell_orders = len([o for o in self.orders if o['side'] == 'SELL'])
        
        print(f"   Total orders placed: {len(self.orders)}")
        print(f"   Active orders: {open_orders}")
        print(f"   Buy orders: {buy_orders}")
        print(f"   Sell orders: {sell_orders}")
        print(f"   Price movements: {self.price_movements}")
        
        print(\"\"\"
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
        \"\"\")

async def main():
    demo = BotDemo()
    
    print("Welcome to the DEX/CEX Arbitrage Bot Demo!")
    print("\\nOptions:")
    print("1. Quick demo (5 cycles)")
    print("2. Standard demo (10 cycles)")
    print("3. Extended demo (20 cycles)")
    print("4. Custom cycles")
    
    try:
        choice = input("\\nSelect option (1-4) [2]: ").strip() or "2"
        
        cycles_map = {'1': 5, '2': 10, '3': 20}
        
        if choice in cycles_map:
            cycles = cycles_map[choice]
        elif choice == '4':
            cycles = int(input("Enter number of cycles: "))
        else:
            cycles = 10
            
        await demo.run_demo(cycles)
        
    except (ValueError, KeyboardInterrupt):
        print("\\n⏹️ Demo cancelled")
    except Exception as e:
        print(f"\\n❌ Demo error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
"""

# Save demo script
with open('demo.py', 'w') as f:
    f.write(demo_script)

# Create a README file
readme_content = """# DEX/CEX Arbitrage Trading Bot

A sophisticated automated trading bot that monitors price differences between Decentralized Exchanges (DEX) and Centralized Exchanges (CEX), implementing a specific arbitrage strategy with intelligent order management.

## 🎯 Strategy Overview

- **Monitor** DEX and CEX prices in real-time
- **Place** buy and sell orders on CEX within 2% range of DEX price  
- **Detect** 2% price movements on DEX
- **Wait** 2 minutes after price movement
- **Rebalance** orders to new price levels

## 🚀 Quick Start

### 1. Automated Setup
```bash
python deploy.py
```

### 2. Manual Setup  
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\\Scripts\\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure settings
cp config.yaml.template config.yaml
# Edit config.yaml with your settings
```

### 3. Run Demo
```bash
python demo.py
```

### 4. Start Bot
```bash
python main_bot.py
```

### 5. Launch Dashboard
```bash
streamlit run dex_cex_arbitrage_streamlit.py
```

## 📁 Project Structure

```
├── main_bot.py                      # Main bot implementation
├── exchange_integrations.py         # CCXT & WebSocket handlers  
├── dex_cex_arbitrage_streamlit.py  # Streamlit dashboard
├── config.yaml                     # Configuration file
├── deploy.py                       # Automated setup script
├── demo.py                         # Demo/test script
├── requirements.txt                # Dependencies
└── DEX-CEX-Bot-Guide.md           # Comprehensive guide
```

## ⚙️ Configuration

Key settings in `config.yaml`:

```yaml
# Trading Strategy
price_threshold: 0.02      # 2% movement detection
rebalance_delay: 120       # 2 minutes wait
spread_range: 0.02         # 2% order range

# Risk Management  
max_position_size: 0.01    # 1% of portfolio per trade
portfolio_value: 10000.0   # Total portfolio value

# Exchange Settings
cex_exchange: "binance"    # Target exchange
sandbox_mode: true         # Paper trading mode
```

## 🔑 API Setup

1. **Binance**: [API Management](https://www.binance.com/en/my/settings/api-management)
2. **Coinbase Pro**: [API Settings](https://pro.coinbase.com/profile/api)  
3. **Kraken**: [API Settings](https://www.kraken.com/u/security/api)

Enable spot trading permissions and add IP restrictions for security.

## 📊 Features

### Core Trading Logic
- [x] Real-time price monitoring (DEX/CEX)
- [x] 2% spread order placement
- [x] 2% price movement detection  
- [x] 2-minute rebalancing delay
- [x] Automatic order management

### Risk Management
- [x] Position sizing limits
- [x] Daily trade limits
- [x] Stop-loss protection
- [x] Portfolio percentage limits

### Technical Features  
- [x] CCXT multi-exchange support
- [x] WebSocket real-time data
- [x] Async/await architecture
- [x] Comprehensive logging
- [x] Performance tracking

### User Interface
- [x] Streamlit web dashboard
- [x] Real-time monitoring
- [x] Configuration management
- [x] Order tracking
- [x] Performance analytics

## ⚠️ Risk Disclaimer

This bot is for educational and research purposes. Cryptocurrency trading involves substantial financial risk. Always:

- Start with paper trading (`sandbox_mode: true`)
- Use only funds you can afford to lose
- Test thoroughly before live trading
- Understand the strategy and risks
- Monitor the bot continuously

## 📚 Documentation

- **[Complete Guide](DEX-CEX-Bot-Guide.md)**: Comprehensive documentation
- **Configuration**: See `config.yaml` for all settings
- **API Integration**: Check `exchange_integrations.py` for details
- **Strategy Logic**: Review `main_bot.py` for implementation

## 🛠️ Development

### Requirements
- Python 3.8+
- Virtual environment recommended
- Exchange API credentials

### Dependencies
- ccxt (exchange connectivity)
- websockets (real-time data)
- streamlit (web interface)
- pandas/numpy (data processing)
- pyyaml (configuration)

### Testing
```bash
python demo.py        # Run simulation
python -m pytest     # Run unit tests (if available)
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Test thoroughly
4. Submit pull request

## 📄 License

This project is provided as-is for educational purposes. Use at your own risk.

## 🆘 Support

- Check the [Complete Guide](DEX-CEX-Bot-Guide.md) for detailed instructions
- Review logs in `logs/` directory for debugging
- Ensure API keys have correct permissions
- Test with sandbox mode before live trading

---

**Happy Trading! 🤖📈**

*Remember: Past performance doesn't guarantee future results. Trade responsibly.*
"""

with open('README.md', 'w') as f:
    f.write(readme_content)

print("✅ Deployment and demo scripts created successfully!")
print("\n📁 Additional files created:")
print("  - deploy.py (Automated setup script)")
print("  - demo.py (Interactive demo/test script)")  
print("  - README.md (Project overview)")

print("\n🎯 Complete Project Structure:")
print("  - main_bot.py (Core bot implementation)")
print("  - exchange_integrations.py (CCXT & WebSocket)")
print("  - dex_cex_arbitrage_streamlit.py (Web dashboard)")
print("  - config.yaml (Configuration)")
print("  - requirements.txt (Dependencies)")
print("  - DEX-CEX-Bot-Guide.md (Comprehensive guide)")
print("  - deploy.py (Setup automation)")
print("  - demo.py (Interactive demo)")
print("  - README.md (Project overview)")

print("\n🚀 Quick Start Options:")
print("1. Automated setup: python deploy.py")
print("2. Run demo first: python demo.py")
print("3. Manual setup: pip install -r requirements.txt")
print("4. Start bot: python main_bot.py")
print("5. Launch UI: streamlit run dex_cex_arbitrage_streamlit.py")

print("\n✨ Your DEX/CEX Arbitrage Trading Bot is ready for deployment!")