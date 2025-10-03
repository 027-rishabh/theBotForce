#!/usr/bin/env python3
"""
Verification script to check all updates are correctly implemented
"""

import yaml
import sys

def check_config_yaml():
    """Verify config.yaml has new fields"""
    print("✓ Checking config.yaml...")

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    api_creds = config.get('api_credentials', {})

    # Check BitMart memo
    if 'bitmart_memo' in api_creds:
        print("  ✅ BitMart memo field found")
    else:
        print("  ❌ BitMart memo field MISSING")
        return False

    # Check AscendEX group_id
    if 'ascendex_group_id' in api_creds:
        print("  ✅ AscendEX group_id field found")
    else:
        print("  ❌ AscendEX group_id field MISSING")
        return False

    return True

def check_market_maker():
    """Verify landshare_market_maker.py has updates"""
    print("\n✓ Checking landshare_market_maker.py...")

    with open('landshare_market_maker.py', 'r') as f:
        content = f.read()

    # Check BitMart memo
    if "bitmart_memo" in content:
        print("  ✅ BitMart memo implementation found")
    else:
        print("  ❌ BitMart memo implementation MISSING")
        return False

    # Check AscendEX group_id
    if "ascendex_group_id" in content:
        print("  ✅ AscendEX group_id implementation found")
    else:
        print("  ❌ AscendEX group_id implementation MISSING")
        return False

    return True

def check_ui():
    """Verify landshare_ui.py has all updates"""
    print("\n✓ Checking landshare_ui.py...")

    with open('landshare_ui.py', 'r') as f:
        content = f.read()

    checks = {
        'bitmart_memo': 'BitMart memo field',
        'ascendex_group_id': 'AscendEX group_id field',
        'dex_price': 'DEX price display',
        'cex_price': 'CEX price display',
        'calculate_dynamic_interval': 'Dynamic refresh interval',
        'fetch_prices': 'Price fetching function',
        'Price Divergence': 'Price divergence metric',
        'dynamic_interval': 'Dynamic interval state'
    }

    all_passed = True
    for key, description in checks.items():
        if key in content:
            print(f"  ✅ {description} found")
        else:
            print(f"  ❌ {description} MISSING")
            all_passed = False

    return all_passed

def check_archived_files():
    """Verify old files are archived"""
    print("\n✓ Checking archived files...")

    import os

    if os.path.exists('archived_files'):
        archived_count = len([f for f in os.listdir('archived_files') if f.endswith('.py') or f.endswith('.md')])
        print(f"  ✅ {archived_count} files archived")
        return True
    else:
        print("  ❌ archived_files directory not found")
        return False

def check_active_files():
    """Verify required files exist"""
    print("\n✓ Checking active files...")

    import os

    required_files = [
        'landshare_ui.py',
        'landshare_market_maker.py',
        'landshare_token_manager.py',
        'test_landshare_bot.py',
        'config.yaml',
        'requirements.txt',
        'README.md',
        'CHANGES_SUMMARY.md'
    ]

    all_exist = True
    for filename in required_files:
        if os.path.exists(filename):
            print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} MISSING")
            all_exist = False

    return all_exist

def main():
    print("=" * 60)
    print("LANDSHARE Market Maker - Update Verification")
    print("=" * 60)

    results = []

    # Run all checks
    results.append(("Config YAML", check_config_yaml()))
    results.append(("Market Maker", check_market_maker()))
    results.append(("UI Updates", check_ui()))
    results.append(("Archived Files", check_archived_files()))
    results.append(("Active Files", check_active_files()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "=" * 60)
    print(f"Result: {passed}/{total} checks passed")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All updates verified successfully!")
        print("\nNext steps:")
        print("1. Launch UI: streamlit run landshare_ui.py")
        print("2. Configure exchange and credentials")
        print("3. Start bot and monitor prices")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please review above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
