#!/usr/bin/env python3
"""
DEX/CEX Arbitrage Bot Deployment Script
Automated setup and deployment script for the trading bot
"""

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
        print("""
╔═══════════════════════════════════════════════════════════╗
║           DEX/CEX Arbitrage Trading Bot Deployer         ║
║                     Setup Assistant                      ║
╚═══════════════════════════════════════════════════════════╝
        """)

    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 8):
            print("❌ Python 3.8 or higher is required")
            print(f"Current version: {sys.version}")
            return False

        print(f"✅ Python version: {sys.version.split()[0]}")
        return True

    def create_virtual_environment(self):
        """Create and activate virtual environment"""
        print("\n🔧 Setting up virtual environment...")

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
        """Install required Python packages"""
        print("\n📦 Installing dependencies...")

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
        """Interactive configuration setup"""
        print("\n⚙️ Setting up bot configuration...")

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

        print("\n📊 Exchange Configuration:")
        exchanges = ['binance', 'coinbase', 'kraken', 'kucoin']
        for i, exchange in enumerate(exchanges, 1):
            print(f"{i}. {exchange.title()}")

        choice = input(f"Select CEX exchange (1-{len(exchanges)}) [1]: ").strip() or "1"
        try:
            config['cex_exchange'] = exchanges[int(choice) - 1]
        except (ValueError, IndexError):
            config['cex_exchange'] = 'binance'

        print("\n🔑 API Configuration (leave empty to skip):")
        api_key = input("CEX API Key: ").strip()
        if api_key:
            config['cex_api_key'] = api_key
            secret = input("CEX API Secret: ").strip()
            if secret:
                config['cex_secret'] = secret
        else:
            config['cex_api_key'] = ''
            config['cex_secret'] = ''

        print("\n💰 Trading Configuration:")
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
        """Create platform-specific startup scripts"""
        print("\n📜 Creating startup scripts...")

        # Windows batch script
        windows_script = f'''@echo off
echo Starting DEX/CEX Arbitrage Bot...
cd /d "{self.project_dir}"
call venv\Scripts\activate
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
        """Run a quick test of the bot"""
        print("\n🧪 Running bot test...")

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
        """Print final instructions"""
        print("""
╔═══════════════════════════════════════════════════════════╗
║                    Setup Complete! 🎉                   ║
╚═══════════════════════════════════════════════════════════╝

🚀 To start the bot:

   Windows: double-click start_bot.bat
   Linux/Mac: ./start_bot.sh

   Or manually:
   1. Activate virtual environment:
      - Windows: venv\Scripts\activate
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
        """)

    def deploy(self):
        """Main deployment process"""
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
            print(f"\n{'='*60}")
            print(f"Step: {step_name}")
            print('='*60)

            if not step_func():
                print(f"\n❌ Deployment failed at: {step_name}")
                return False

        self.print_instructions()
        return True

def main():
    deployer = BotDeployer()

    try:
        success = deployer.deploy()
        if success:
            print("\n🎉 Deployment completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Deployment failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
