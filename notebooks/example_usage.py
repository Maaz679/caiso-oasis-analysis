"""
Example usage of the CAISO OASIS client.

This script demonstrates how to fetch LMP, fuel mix, and load data
from CAISO's OASIS API.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.oasis import CAISOClient, quick_fetch_latest


def example_quick_fetch():
    """Quick way to fetch the last 24 hours of data."""
    print("=" * 60)
    print("Example 1: Quick fetch latest 24 hours")
    print("=" * 60)

    data = quick_fetch_latest(hours=24)

    print("\nLMP Data:")
    print(data['lmp'].head())
    print(f"\nTotal LMP records: {len(data['lmp'])}")

    print("\nFuel Mix Data:")
    print(data['fuel_mix'].head())
    print(f"\nTotal fuel mix records: {len(data['fuel_mix'])}")

    print("\nLoad Data:")
    print(data['load'].head())
    print(f"\nTotal load records: {len(data['load'])}")


def example_specific_dates():
    """Fetch data for specific date range."""
    print("\n" + "=" * 60)
    print("Example 2: Fetch specific date range")
    print("=" * 60)

    # Fetch data for yesterday
    end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=1)

    with CAISOClient() as client:
        # Get day-ahead market LMP
        lmp = client.get_lmp(start, end, market="DAM")
        print(f"\nDay-ahead LMP records: {len(lmp)}")
        print(lmp.head())

        # Get real-time market LMP for trading hubs only
        hub_lmp = client.get_trading_hub_lmp(start, end, market="RTM")
        print(f"\nTrading hub LMP records: {len(hub_lmp)}")
        print(hub_lmp.head())


def example_fuel_analysis():
    """Analyze fuel mix composition."""
    print("\n" + "=" * 60)
    print("Example 3: Fuel mix analysis")
    print("=" * 60)

    end = datetime.now()
    start = end - timedelta(hours=6)

    with CAISOClient() as client:
        fuel_mix = client.get_fuel_mix(start, end)

        # Calculate average generation by fuel type
        avg_by_fuel = fuel_mix.groupby('fuel_type')['generation_mw'].mean().sort_values(ascending=False)

        print("\nAverage generation by fuel type (last 6 hours):")
        for fuel, gen in avg_by_fuel.items():
            print(f"  {fuel}: {gen:.2f} MW")


def example_market_summary():
    """Get comprehensive market summary."""
    print("\n" + "=" * 60)
    print("Example 4: Complete market summary")
    print("=" * 60)

    end = datetime.now()
    start = end - timedelta(hours=12)

    with CAISOClient() as client:
        summary = client.get_market_summary(start, end)

        print("\nMarket Summary:")
        print(f"  LMP records: {len(summary['lmp'])}")
        print(f"  Fuel mix records: {len(summary['fuel_mix'])}")
        print(f"  Load records: {len(summary['load'])}")

        # Calculate average system price
        avg_lmp = summary['lmp'].groupby('timestamp')['lmp_total'].mean()
        print(f"\n  Average system LMP: ${avg_lmp.mean():.2f}/MWh")

        # Calculate total load
        avg_load = summary['load']['load_mw'].mean()
        print(f"  Average system load: {avg_load:.2f} MW")


if __name__ == "__main__":
    try:
        example_quick_fetch()
        example_specific_dates()
        example_fuel_analysis()
        example_market_summary()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        print("\nNote: You need an active internet connection to fetch data from CAISO OASIS.")
        import traceback
        traceback.print_exc()
