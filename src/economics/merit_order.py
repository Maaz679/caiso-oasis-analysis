"""
Merit Order and Market Clearing Models

Implementation of merit order dispatch and market clearing from Kirschen & Strbac
"Fundamentals of Power System Economics" Chapter 4.

Key concepts:
- Supply curve construction (merit order stack)
- Demand curve and market clearing
- Producer surplus and consumer surplus
- Price formation in competitive markets
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
import warnings


@dataclass
class Bid:
    """
    Generator bid for energy market.

    Attributes:
        generator: Generator name
        price: Bid price ($/MWh)
        quantity: Offered quantity (MW)
        is_must_run: Whether generator must run (price-insensitive)
    """
    generator: str
    price: float  # $/MWh
    quantity: float  # MW
    is_must_run: bool = False


@dataclass
class DemandBid:
    """
    Demand bid for energy market.

    Attributes:
        buyer: Buyer/load name
        price: Willingness to pay ($/MWh)
        quantity: Requested quantity (MW)
    """
    buyer: str
    price: float  # $/MWh
    quantity: float  # MW


class MeritOrder:
    """
    Merit order dispatch and market clearing.

    Constructs supply curve from generator bids and finds market clearing
    price/quantity intersection with demand.
    """

    def __init__(self, supply_bids: List[Bid]):
        """
        Initialize merit order with supply bids.

        Args:
            supply_bids: List of generator Bid objects
        """
        self.supply_bids = supply_bids
        self._build_supply_curve()

    def _build_supply_curve(self):
        """
        Build supply curve by sorting bids by price (merit order).

        Must-run generators go first (at any price), then sorted by bid price.
        """
        # Separate must-run and price-responsive
        must_run = [b for b in self.supply_bids if b.is_must_run]
        price_responsive = [b for b in self.supply_bids if not b.is_must_run]

        # Sort price-responsive by price
        price_responsive.sort(key=lambda b: b.price)

        # Combine: must-run first, then by merit order
        self.sorted_bids = must_run + price_responsive

        # Build cumulative supply curve
        cumulative_quantity = 0
        self.supply_curve = []

        for bid in self.sorted_bids:
            self.supply_curve.append({
                'generator': bid.generator,
                'price': bid.price,
                'quantity': bid.quantity,
                'cumulative_start': cumulative_quantity,
                'cumulative_end': cumulative_quantity + bid.quantity,
                'is_must_run': bid.is_must_run,
            })
            cumulative_quantity += bid.quantity

        self.max_supply = cumulative_quantity

    def get_supply_curve_df(self) -> pd.DataFrame:
        """
        Get supply curve as DataFrame.

        Returns:
            DataFrame with supply curve data
        """
        return pd.DataFrame(self.supply_curve)

    def market_clearing_price(
        self,
        demand: float,
        demand_price_cap: float = 1000.0,
    ) -> Dict:
        """
        Find market clearing price for given demand.

        The clearing price is the marginal unit's bid price when supply meets demand.

        Args:
            demand: Total demand (MW)
            demand_price_cap: Maximum price consumers will pay ($/MWh)

        Returns:
            Dictionary with:
                - clearing_price: Market clearing price ($/MWh)
                - clearing_quantity: Quantity cleared (MW)
                - dispatched: Dict of {generator: quantity}
                - marginal_generator: Name of marginal generator
                - scarcity: True if demand exceeds available supply
        """
        if demand > self.max_supply:
            warnings.warn(
                f"Demand ({demand} MW) exceeds available supply ({self.max_supply} MW). "
                "Using price cap."
            )
            return {
                'clearing_price': demand_price_cap,
                'clearing_quantity': self.max_supply,
                'dispatched': {
                    step['generator']: step['quantity']
                    for step in self.supply_curve
                },
                'marginal_generator': self.sorted_bids[-1].generator if self.sorted_bids else None,
                'scarcity': True,
                'shortage': demand - self.max_supply,
            }

        # Find marginal generator
        cumulative = 0
        dispatched = {}
        clearing_price = 0
        marginal_generator = None

        for step in self.supply_curve:
            if cumulative >= demand:
                break

            remaining_demand = demand - cumulative
            quantity_dispatched = min(step['quantity'], remaining_demand)

            dispatched[step['generator']] = quantity_dispatched
            cumulative += quantity_dispatched

            # The clearing price is the marginal unit's price
            if cumulative >= demand:
                clearing_price = step['price']
                marginal_generator = step['generator']

        return {
            'clearing_price': clearing_price,
            'clearing_quantity': demand,
            'dispatched': dispatched,
            'marginal_generator': marginal_generator,
            'scarcity': False,
        }

    def market_clearing_with_demand_curve(
        self,
        demand_bids: List[DemandBid],
    ) -> Dict:
        """
        Find market clearing with explicit demand bids.

        Matches supply and demand curves to find equilibrium price/quantity.

        Args:
            demand_bids: List of DemandBid objects

        Returns:
            Dictionary with clearing results including welfare measures
        """
        # Build demand curve (sorted by price, descending)
        sorted_demand = sorted(demand_bids, key=lambda b: b.price, reverse=True)

        demand_curve = []
        cumulative_quantity = 0

        for bid in sorted_demand:
            demand_curve.append({
                'buyer': bid.buyer,
                'price': bid.price,
                'quantity': bid.quantity,
                'cumulative_start': cumulative_quantity,
                'cumulative_end': cumulative_quantity + bid.quantity,
            })
            cumulative_quantity += bid.quantity

        # Find intersection of supply and demand
        clearing_price = None
        clearing_quantity = 0

        supply_idx = 0
        demand_idx = 0

        while supply_idx < len(self.supply_curve) and demand_idx < len(demand_curve):
            supply_step = self.supply_curve[supply_idx]
            demand_step = demand_curve[demand_idx]

            # Check if demand price >= supply price (willing to trade)
            if demand_step['price'] >= supply_step['price']:
                # Find quantity that can be traded
                supply_available = supply_step['cumulative_end'] - clearing_quantity
                demand_wanted = demand_step['cumulative_end'] - clearing_quantity

                trade_quantity = min(supply_available, demand_wanted)
                clearing_quantity += trade_quantity

                # Clearing price is between supply and demand price
                # Using uniform pricing: clearing price = marginal unit price
                clearing_price = supply_step['price']

                # Move to next step
                if clearing_quantity >= supply_step['cumulative_end']:
                    supply_idx += 1
                if clearing_quantity >= demand_step['cumulative_end']:
                    demand_idx += 1
            else:
                # No more mutually beneficial trades
                break

        if clearing_price is None:
            clearing_price = 0

        # Get dispatch
        result = self.market_clearing_price(clearing_quantity)
        result['clearing_price'] = clearing_price

        # Calculate welfare measures
        result['producer_surplus'] = self._calculate_producer_surplus(
            result['dispatched'], clearing_price
        )
        result['consumer_surplus'] = self._calculate_consumer_surplus(
            demand_curve, clearing_quantity, clearing_price
        )
        result['social_welfare'] = result['producer_surplus'] + result['consumer_surplus']

        return result

    def _calculate_producer_surplus(
        self,
        dispatch: Dict[str, float],
        clearing_price: float,
    ) -> float:
        """
        Calculate producer surplus (profit above bid cost).

        Producer surplus = sum((clearing_price - bid_price) * quantity)

        Args:
            dispatch: Dict of {generator: quantity}
            clearing_price: Market clearing price

        Returns:
            Total producer surplus ($)
        """
        surplus = 0

        for step in self.supply_curve:
            gen = step['generator']
            if gen in dispatch:
                quantity = dispatch[gen]
                bid_price = step['price']
                surplus += (clearing_price - bid_price) * quantity

        return surplus

    def _calculate_consumer_surplus(
        self,
        demand_curve: List[Dict],
        clearing_quantity: float,
        clearing_price: float,
    ) -> float:
        """
        Calculate consumer surplus (value above price paid).

        Consumer surplus = sum((bid_price - clearing_price) * quantity)

        Args:
            demand_curve: List of demand curve steps
            clearing_quantity: Quantity cleared
            clearing_price: Market clearing price

        Returns:
            Total consumer surplus ($)
        """
        surplus = 0
        cumulative = 0

        for step in demand_curve:
            if cumulative >= clearing_quantity:
                break

            remaining = clearing_quantity - cumulative
            quantity = min(step['quantity'], remaining)

            bid_price = step['price']
            surplus += (bid_price - clearing_price) * quantity
            cumulative += quantity

        return surplus

    def supply_stack_data(self, num_points: int = 100) -> pd.DataFrame:
        """
        Get supply stack data for plotting.

        Returns step function data for visualizing the merit order stack.

        Args:
            num_points: Number of interpolation points

        Returns:
            DataFrame with columns: quantity, price, generator
        """
        data = []

        for step in self.supply_curve:
            # Start point
            data.append({
                'quantity': step['cumulative_start'],
                'price': step['price'],
                'generator': step['generator'],
            })
            # End point
            data.append({
                'quantity': step['cumulative_end'],
                'price': step['price'],
                'generator': step['generator'],
            })

        return pd.DataFrame(data)


def create_bids_from_generators(
    generators: List,
    availability: Optional[Dict[str, float]] = None,
) -> List[Bid]:
    """
    Create market bids from Generator objects (from dispatch.py).

    Uses marginal cost at maximum output as bid price.

    Args:
        generators: List of Generator objects
        availability: Dict of {gen_name: availability_factor (0-1)}

    Returns:
        List of Bid objects
    """
    from .dispatch import Generator

    bids = []

    for gen in generators:
        if not isinstance(gen, Generator):
            raise TypeError(f"Expected Generator object, got {type(gen)}")

        # Bid price = marginal cost at some representative output
        # Common practice: bid at marginal cost at 80% of capacity
        representative_output = gen.p_min + 0.8 * (gen.p_max - gen.p_min)
        bid_price = gen.marginal_cost(representative_output)

        # Available quantity considering availability
        if availability and gen.name in availability:
            quantity = gen.p_max * availability[gen.name]
        else:
            quantity = gen.p_max

        # Must-run if generator is at minimum
        is_must_run = gen.p_min > 0

        bids.append(Bid(
            generator=gen.name,
            price=bid_price,
            quantity=quantity,
            is_must_run=is_must_run,
        ))

    return bids


def simulate_market_timeline(
    supply_bids: List[Bid],
    load_profile: np.ndarray,
    timestamps: Optional[pd.DatetimeIndex] = None,
) -> pd.DataFrame:
    """
    Simulate market clearing over a time series of load.

    Args:
        supply_bids: List of supply bids (assumed constant over time)
        load_profile: Array of load values over time (MW)
        timestamps: DatetimeIndex for results

    Returns:
        DataFrame with market outcomes over time
    """
    merit_order = MeritOrder(supply_bids)

    results = []

    for t, load in enumerate(load_profile):
        result = merit_order.market_clearing_price(load)

        row = {
            'time_step': t,
            'load': load,
            'clearing_price': result['clearing_price'],
            'clearing_quantity': result['clearing_quantity'],
            'marginal_generator': result['marginal_generator'],
            'scarcity': result['scarcity'],
        }

        # Add dispatch for each generator
        for gen_name in set(bid.generator for bid in supply_bids):
            row[f'dispatch_{gen_name}'] = result['dispatched'].get(gen_name, 0)

        results.append(row)

    df = pd.DataFrame(results)

    if timestamps is not None:
        df['timestamp'] = timestamps
        df = df.set_index('timestamp')

    return df


def analyze_market_power(
    supply_bids: List[Bid],
    demand: float,
    actual_costs: Optional[Dict[str, float]] = None,
) -> Dict:
    """
    Analyze potential for market power exercise.

    Compares bid prices to actual costs (if known) and calculates markup.

    Args:
        supply_bids: List of supply bids
        demand: System demand (MW)
        actual_costs: Dict of {generator: true_marginal_cost}

    Returns:
        Dictionary with market power metrics
    """
    merit_order = MeritOrder(supply_bids)
    result = merit_order.market_clearing_price(demand)

    metrics = {
        'clearing_price': result['clearing_price'],
        'marginal_generator': result['marginal_generator'],
    }

    if actual_costs:
        # Calculate markups
        markups = {}
        for bid in supply_bids:
            if bid.generator in actual_costs:
                true_cost = actual_costs[bid.generator]
                markup = ((bid.price - true_cost) / true_cost * 100
                         if true_cost > 0 else 0)
                markups[bid.generator] = markup

        metrics['markups'] = markups
        metrics['avg_markup'] = np.mean(list(markups.values())) if markups else 0

    return metrics
