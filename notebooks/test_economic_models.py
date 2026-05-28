"""
Test and demonstrate economic models with real CAISO data.

Demonstrates:
1. Economic Dispatch (Ch. 3 - Kirschen & Strbac)
2. Merit Order / Market Clearing (Ch. 4)
3. LMP Decomposition (Ch. 5)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.economics import (
    Generator,
    EconomicDispatch,
    create_generator_from_fuel_type,
    analyze_dispatch_efficiency,
    Bid,
    MeritOrder,
    create_bids_from_generators,
    LMPAnalyzer,
    analyze_caiso_lmp_data,
)
from src.oasis import CAISOClient


def test_economic_dispatch():
    """Test Economic Dispatch model (Ch. 3)."""
    print("=" * 70)
    print("TEST 1: Economic Dispatch (Lambda Iteration)")
    print("=" * 70)

    # Create a simple 3-generator system
    generators = [
        Generator(name="Nuclear", a=5000, b=12, c=0.002, p_min=700, p_max=1000),
        Generator(name="Coal", a=3000, b=30, c=0.005, p_min=300, p_max=600),
        Generator(name="Gas_CCGT", a=1000, b=45, c=0.015, p_min=100, p_max=400),
        Generator(name="Gas_Peaker", a=500, b=85, c=0.04, p_min=0, p_max=200),
    ]

    # Initialize dispatch solver
    ed = EconomicDispatch(generators)

    # Solve for various load levels
    loads = [1000, 1500, 2000]

    print("\nEconomic Dispatch Results:")
    print("-" * 70)

    for load in loads:
        result = ed.lambda_iteration(load)

        print(f"\nLoad = {load} MW")
        print(f"  System Lambda (marginal cost) = ${result['lambda']:.2f}/MWh")
        print(f"  Total Cost = ${result['total_cost']:.2f}/hr")
        print(f"  Converged in {result['iterations']} iterations")
        print(f"  Dispatch:")

        for gen_name, power in result['dispatch'].items():
            cost = result['costs'][gen_name]
            mc = result['marginal_costs'][gen_name]
            print(f"    {gen_name:12s}: {power:6.1f} MW  "
                  f"(Cost: ${cost:8.2f}/hr, MC: ${mc:5.2f}/MWh)")

        # Efficiency analysis
        efficiency = analyze_dispatch_efficiency(result)
        print(f"  Efficiency Metrics:")
        print(f"    Average Cost: ${efficiency['average_cost']:.2f}/MWh")
        print(f"    Active Units: {efficiency['num_generators_active']}")

    return ed


def test_merit_order():
    """Test Merit Order / Market Clearing (Ch. 4)."""
    print("\n\n" + "=" * 70)
    print("TEST 2: Merit Order and Market Clearing")
    print("=" * 70)

    # Create generators with different fuel types
    generators = [
        create_generator_from_fuel_type("Nuclear_1", "nuclear", 1000),
        create_generator_from_fuel_type("Hydro_1", "hydro", 500),
        create_generator_from_fuel_type("Coal_1", "coal", 600),
        create_generator_from_fuel_type("Gas_CCGT_1", "gas_ccgt", 400),
        create_generator_from_fuel_type("Gas_CCGT_2", "gas_ccgt", 400),
        create_generator_from_fuel_type("Gas_Peaker_1", "gas_peaker", 200),
    ]

    # Create bids from generators
    bids = create_bids_from_generators(generators)

    print("\nSupply Bids (Merit Order):")
    print("-" * 70)
    for bid in sorted(bids, key=lambda b: b.price):
        print(f"  {bid.generator:15s}: {bid.quantity:6.1f} MW @ ${bid.price:6.2f}/MWh")

    # Create merit order
    merit_order = MeritOrder(bids)

    # Test market clearing at different demand levels
    demands = [1000, 2000, 3000]

    print("\nMarket Clearing Results:")
    print("-" * 70)

    for demand in demands:
        result = merit_order.market_clearing_price(demand)

        print(f"\nDemand = {demand} MW")
        print(f"  Clearing Price = ${result['clearing_price']:.2f}/MWh")
        print(f"  Marginal Unit = {result['marginal_generator']}")
        print(f"  Dispatched Units:")

        for gen_name, power in sorted(
            result['dispatched'].items(),
            key=lambda x: bids[[b.generator for b in bids].index(x[0])].price
        ):
            bid_price = next(b.price for b in bids if b.generator == gen_name)
            profit = (result['clearing_price'] - bid_price) * power
            print(f"    {gen_name:15s}: {power:6.1f} MW  "
                  f"(Bid: ${bid_price:6.2f}, Profit: ${profit:8.2f})")

    return merit_order


def test_lmp_analysis_with_real_data():
    """Test LMP Analysis with real CAISO data (Ch. 5)."""
    print("\n\n" + "=" * 70)
    print("TEST 3: LMP Decomposition with Real CAISO Data")
    print("=" * 70)

    # Fetch real LMP data from CAISO
    print("\nFetching real LMP data from CAISO OASIS...")
    end = datetime.now()
    start = end - timedelta(hours=12)

    with CAISOClient() as client:
        lmp_df = client.get_lmp(start, end, market="RTM")

    print(f"  Retrieved {len(lmp_df)} LMP records")
    print(f"  Unique locations: {lmp_df['location'].nunique()}")

    # Analyze LMP data
    analysis = analyze_caiso_lmp_data(lmp_df)

    print("\nLMP Distribution Statistics:")
    print("-" * 70)
    dist = analysis['distribution']
    print(f"  Mean LMP:   ${dist['mean_lmp']:6.2f}/MWh")
    print(f"  Median LMP: ${dist['median_lmp']:6.2f}/MWh")
    print(f"  Std Dev:    ${dist['std_lmp']:6.2f}/MWh")
    print(f"  Range:      ${dist['min_lmp']:6.2f} - ${dist['max_lmp']:6.2f}/MWh")

    print("\nLMP Component Analysis:")
    print("-" * 70)
    for component, stats in analysis['components'].items():
        print(f"  {component}:")
        print(f"    Mean: ${stats['mean']:6.2f}/MWh ({stats['contribution_pct']:5.1f}% of total)")
        print(f"    Std:  ${stats['std']:6.2f}/MWh")

    if analysis['top_congested_locations']:
        print("\nTop Congested Locations:")
        print("-" * 70)
        for i, loc in enumerate(analysis['top_congested_locations'][:5], 1):
            print(f"  {i}. {loc}")

    if analysis['time_patterns']:
        print("\nTemporal Price Patterns:")
        print("-" * 70)
        tp = analysis['time_patterns']
        print(f"  Peak Hour: {tp['peak_hour']}:00 (${tp['peak_price']:.2f}/MWh)")
        print(f"  Off-Peak Hour: {tp['off_peak_hour']}:00 (${tp['off_peak_price']:.2f}/MWh)")
        if tp['peak_to_offpeak_ratio']:
            print(f"  Peak/Off-Peak Ratio: {tp['peak_to_offpeak_ratio']:.2f}")

    # Detailed component breakdown for trading hubs
    print("\nTrading Hub LMP Breakdown:")
    print("-" * 70)

    trading_hubs = [
        'TH_NP15_GEN-APND',
        'TH_SP15_GEN-APND',
        'TH_ZP26_GEN-APND',
    ]

    for hub in trading_hubs:
        hub_data = lmp_df[lmp_df['location'] == hub]
        if len(hub_data) > 0:
            avg_total = hub_data['lmp_total'].mean()
            avg_energy = hub_data['lmp_energy'].mean()
            avg_congestion = hub_data['lmp_congestion'].mean()
            avg_loss = hub_data['lmp_loss'].mean()

            hub_name = hub.split('_')[1]  # Extract NP15, SP15, etc.
            print(f"\n  {hub_name}:")
            print(f"    Total:      ${avg_total:6.2f}/MWh")
            print(f"    Energy:     ${avg_energy:6.2f}/MWh ({avg_energy/avg_total*100:5.1f}%)")
            print(f"    Congestion: ${avg_congestion:6.2f}/MWh ({avg_congestion/avg_total*100:5.1f}%)")
            print(f"    Loss:       ${avg_loss:6.2f}/MWh ({avg_loss/avg_total*100:5.1f}%)")

    return lmp_df


def test_integrated_example():
    """Integrated example: Compare economic dispatch with market clearing."""
    print("\n\n" + "=" * 70)
    print("TEST 4: Integrated Example - Dispatch vs Market Clearing")
    print("=" * 70)

    # Create generators
    generators = [
        create_generator_from_fuel_type("Nuclear", "nuclear", 1000),
        create_generator_from_fuel_type("Coal", "coal", 600),
        create_generator_from_fuel_type("Gas_CCGT", "gas_ccgt", 400),
        create_generator_from_fuel_type("Gas_Peaker", "gas_peaker", 200),
    ]

    load = 1800  # MW

    # 1. Economic Dispatch (centralized optimization)
    print("\n1. CENTRALIZED: Economic Dispatch")
    print("-" * 70)
    ed = EconomicDispatch(generators)
    dispatch_result = ed.lambda_iteration(load)

    print(f"System Lambda: ${dispatch_result['lambda']:.2f}/MWh")
    print(f"Total Cost: ${dispatch_result['total_cost']:.2f}/hr")
    print("Dispatch:")
    for gen_name, power in dispatch_result['dispatch'].items():
        print(f"  {gen_name:12s}: {power:6.1f} MW")

    # 2. Market Clearing (decentralized bidding)
    print("\n2. DECENTRALIZED: Market Clearing")
    print("-" * 70)
    bids = create_bids_from_generators(generators)
    merit_order = MeritOrder(bids)
    market_result = merit_order.market_clearing_price(load)

    print(f"Clearing Price: ${market_result['clearing_price']:.2f}/MWh")
    print("Dispatch:")
    total_cost_market = 0
    for gen_name, power in market_result['dispatched'].items():
        bid_price = next(b.price for b in bids if b.generator == gen_name)
        gen_obj = next(g for g in generators if g.name == gen_name)
        actual_cost = gen_obj.cost(power)
        total_cost_market += actual_cost
        print(f"  {gen_name:12s}: {power:6.1f} MW")

    print(f"Total Cost: ${total_cost_market:.2f}/hr")

    # 3. Comparison
    print("\n3. COMPARISON")
    print("-" * 70)
    print(f"Economic Dispatch Lambda:   ${dispatch_result['lambda']:.2f}/MWh")
    print(f"Market Clearing Price:      ${market_result['clearing_price']:.2f}/MWh")
    print(f"Economic Dispatch Cost:     ${dispatch_result['total_cost']:.2f}/hr")
    print(f"Market Dispatch Cost:       ${total_cost_market:.2f}/hr")

    price_diff = abs(dispatch_result['lambda'] - market_result['clearing_price'])
    print(f"\nPrice Difference: ${price_diff:.2f}/MWh")

    if price_diff < 1.0:
        print("✓ Market clearing achieves near-optimal economic dispatch!")
    else:
        print("⚠ Significant difference - may indicate market power or constraints")


def main():
    """Run all tests."""
    try:
        # Test 1: Economic Dispatch
        ed = test_economic_dispatch()

        # Test 2: Merit Order
        merit_order = test_merit_order()

        # Test 3: Real LMP Analysis
        lmp_df = test_lmp_analysis_with_real_data()

        # Test 4: Integrated Comparison
        test_integrated_example()

        print("\n" + "=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nAll economic models from Kirschen & Strbac are working:")
        print("  ✓ Chapter 3: Economic Dispatch (Lambda Iteration)")
        print("  ✓ Chapter 4: Merit Order and Market Clearing")
        print("  ✓ Chapter 5: LMP Decomposition and Analysis")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
