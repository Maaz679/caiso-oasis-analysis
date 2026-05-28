"""
Economic Models for Power Systems

Implementation of economic models from Kirschen & Strbac
"Fundamentals of Power System Economics" (3rd ed.)

Modules:
- dispatch: Economic dispatch with lambda iteration (Ch. 3)
- merit_order: Merit order and market clearing (Ch. 4)
- lmp: LMP decomposition and analysis (Ch. 5)
"""

from .dispatch import (
    Generator,
    EconomicDispatch,
    create_generator_from_fuel_type,
    analyze_dispatch_efficiency,
)

from .merit_order import (
    Bid,
    DemandBid,
    MeritOrder,
    create_bids_from_generators,
    simulate_market_timeline,
    analyze_market_power,
)

from .lmp import (
    Node,
    LMPAnalyzer,
    analyze_caiso_lmp_data,
    calculate_system_cost,
)

__all__ = [
    # Dispatch
    'Generator',
    'EconomicDispatch',
    'create_generator_from_fuel_type',
    'analyze_dispatch_efficiency',
    # Merit Order
    'Bid',
    'DemandBid',
    'MeritOrder',
    'create_bids_from_generators',
    'simulate_market_timeline',
    'analyze_market_power',
    # LMP
    'Node',
    'LMPAnalyzer',
    'analyze_caiso_lmp_data',
    'calculate_system_cost',
]
