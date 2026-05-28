"""
Economic Dispatch Models

Implementation of economic dispatch algorithms from Kirschen & Strbac
"Fundamentals of Power System Economics" Chapter 3.

Key concepts:
- Equal incremental cost principle
- Lambda iteration method
- Generator cost curves (quadratic)
- Minimum/maximum generation limits
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Generator:
    """
    Generator with quadratic cost function: C(P) = a + b*P + c*P^2

    Attributes:
        name: Generator identifier
        a: Fixed cost coefficient ($/hr)
        b: Linear cost coefficient ($/MWh)
        c: Quadratic cost coefficient ($/MW^2h)
        p_min: Minimum generation (MW)
        p_max: Maximum generation (MW)
    """
    name: str
    a: float  # $/hr
    b: float  # $/MWh
    c: float  # $/MW^2h
    p_min: float  # MW
    p_max: float  # MW

    def cost(self, power: float) -> float:
        """Total generation cost at given power output."""
        return self.a + self.b * power + self.c * power**2

    def marginal_cost(self, power: float) -> float:
        """Incremental cost (dC/dP) at given power output."""
        return self.b + 2 * self.c * power

    def inverse_marginal_cost(self, lambda_: float) -> float:
        """
        Power output for a given marginal cost (lambda).
        Solves: lambda = b + 2*c*P for P
        """
        if self.c == 0:
            # Linear cost function - infinite supply at marginal cost b
            return self.p_max if lambda_ >= self.b else self.p_min
        return (lambda_ - self.b) / (2 * self.c)

    def clip_to_limits(self, power: float) -> float:
        """Clip power output to generator limits."""
        return np.clip(power, self.p_min, self.p_max)


class EconomicDispatch:
    """
    Economic dispatch solver using lambda iteration.

    Finds optimal generator dispatch that minimizes total generation cost
    while meeting load demand, based on the equal incremental cost principle.
    """

    def __init__(self, generators: List[Generator]):
        """
        Initialize economic dispatch solver.

        Args:
            generators: List of Generator objects
        """
        self.generators = generators

    def lambda_iteration(
        self,
        load: float,
        tolerance: float = 0.01,
        max_iterations: int = 100,
    ) -> Dict:
        """
        Solve economic dispatch using lambda iteration method.

        Algorithm (Kirschen & Strbac Section 3.3):
        1. Initialize lambda (system marginal cost)
        2. For each generator, compute output: P_i = (lambda - b_i) / (2*c_i)
        3. Apply generator limits
        4. Check if sum(P_i) = Load
        5. Adjust lambda and iterate until convergence

        Args:
            load: Total system load (MW)
            tolerance: Convergence tolerance (MW)
            max_iterations: Maximum iterations

        Returns:
            Dictionary with:
                - dispatch: Power output for each generator (MW)
                - lambda: System marginal cost ($/MWh)
                - total_cost: Total generation cost ($/hr)
                - iterations: Number of iterations
                - converged: Whether algorithm converged
        """
        # Initialize lambda using average marginal cost at mid-range
        lambda_min = min(g.marginal_cost(g.p_min) for g in self.generators)
        lambda_max = max(g.marginal_cost(g.p_max) for g in self.generators)
        lambda_ = (lambda_min + lambda_max) / 2

        converged = False
        iteration = 0

        for iteration in range(max_iterations):
            # Compute dispatch for current lambda
            dispatch = {}
            total_generation = 0

            for gen in self.generators:
                # Compute optimal output for this lambda
                p = gen.inverse_marginal_cost(lambda_)
                # Apply generator limits
                p = gen.clip_to_limits(p)
                dispatch[gen.name] = p
                total_generation += p

            # Check convergence
            error = total_generation - load

            if abs(error) < tolerance:
                converged = True
                break

            # Adjust lambda using bisection-like approach
            if error > 0:  # Over-generation
                lambda_max = lambda_
            else:  # Under-generation
                lambda_min = lambda_

            lambda_ = (lambda_min + lambda_max) / 2

        # Calculate total cost
        total_cost = sum(
            gen.cost(dispatch[gen.name])
            for gen in self.generators
        )

        # Calculate individual costs
        costs = {
            gen.name: gen.cost(dispatch[gen.name])
            for gen in self.generators
        }

        # Calculate marginal costs at dispatch point
        marginal_costs = {
            gen.name: gen.marginal_cost(dispatch[gen.name])
            for gen in self.generators
        }

        return {
            'dispatch': dispatch,
            'lambda': lambda_,
            'total_cost': total_cost,
            'costs': costs,
            'marginal_costs': marginal_costs,
            'total_generation': sum(dispatch.values()),
            'load': load,
            'iterations': iteration + 1,
            'converged': converged,
        }

    def dispatch_profile(
        self,
        load_profile: np.ndarray,
        **kwargs
    ) -> pd.DataFrame:
        """
        Solve economic dispatch for a load profile (time series).

        Args:
            load_profile: Array of load values (MW) over time
            **kwargs: Additional arguments for lambda_iteration

        Returns:
            DataFrame with dispatch results for each time step
        """
        results = []

        for t, load in enumerate(load_profile):
            result = self.lambda_iteration(load, **kwargs)

            row = {
                'time_step': t,
                'load': load,
                'lambda': result['lambda'],
                'total_cost': result['total_cost'],
                'converged': result['converged'],
            }

            # Add dispatch for each generator
            for gen_name, power in result['dispatch'].items():
                row[f'dispatch_{gen_name}'] = power

            results.append(row)

        return pd.DataFrame(results)

    def merit_order_curve(
        self,
        load_range: Optional[Tuple[float, float]] = None,
        num_points: int = 100,
    ) -> pd.DataFrame:
        """
        Compute the system-level merit order (supply) curve.

        Shows relationship between load and system lambda (marginal cost).

        Args:
            load_range: (min_load, max_load) in MW. If None, uses generator limits.
            num_points: Number of points in the curve

        Returns:
            DataFrame with columns: load, lambda, total_cost
        """
        if load_range is None:
            min_load = sum(g.p_min for g in self.generators)
            max_load = sum(g.p_max for g in self.generators)
            load_range = (min_load, max_load)

        loads = np.linspace(load_range[0], load_range[1], num_points)
        results = []

        for load in loads:
            result = self.lambda_iteration(load)
            results.append({
                'load': load,
                'lambda': result['lambda'],
                'total_cost': result['total_cost'],
            })

        return pd.DataFrame(results)


def create_generator_from_fuel_type(
    name: str,
    fuel_type: str,
    capacity: float,
    **kwargs
) -> Generator:
    """
    Create a generator with typical cost parameters for a fuel type.

    Typical marginal costs (2026):
    - Nuclear: $10-15/MWh (baseload)
    - Coal: $25-35/MWh (baseload)
    - Hydro: $0-10/MWh (very low marginal cost)
    - Natural Gas (CCGT): $30-60/MWh
    - Natural Gas (Peaker): $60-150/MWh
    - Solar/Wind: $0/MWh (zero marginal cost)

    Args:
        name: Generator name
        fuel_type: One of: nuclear, coal, hydro, gas_ccgt, gas_peaker, solar, wind
        capacity: Generator capacity (MW)
        **kwargs: Override default cost parameters (a, b, c, p_min)

    Returns:
        Generator object
    """
    # Default parameters by fuel type
    defaults = {
        'nuclear': {'a': 5000, 'b': 12, 'c': 0.002, 'p_min': 0.7},
        'coal': {'a': 3000, 'b': 30, 'c': 0.005, 'p_min': 0.5},
        'hydro': {'a': 100, 'b': 5, 'c': 0.001, 'p_min': 0.0},
        'gas_ccgt': {'a': 1000, 'b': 40, 'c': 0.015, 'p_min': 0.3},
        'gas_peaker': {'a': 500, 'b': 80, 'c': 0.04, 'p_min': 0.0},
        'solar': {'a': 0, 'b': 0, 'c': 0.0, 'p_min': 0.0},
        'wind': {'a': 0, 'b': 0, 'c': 0.0, 'p_min': 0.0},
    }

    if fuel_type not in defaults:
        raise ValueError(f"Unknown fuel type: {fuel_type}")

    params = defaults[fuel_type].copy()
    params.update(kwargs)

    p_min_mw = params.pop('p_min') * capacity

    return Generator(
        name=name,
        a=params.get('a', 0),
        b=params.get('b', 0),
        c=params.get('c', 0),
        p_min=p_min_mw,
        p_max=capacity,
    )


def analyze_dispatch_efficiency(dispatch_result: Dict) -> Dict:
    """
    Analyze efficiency metrics of dispatch solution.

    Args:
        dispatch_result: Output from EconomicDispatch.lambda_iteration

    Returns:
        Dictionary with efficiency metrics
    """
    dispatch = dispatch_result['dispatch']
    marginal_costs = dispatch_result['marginal_costs']

    # Calculate average cost vs marginal cost
    avg_cost = dispatch_result['total_cost'] / dispatch_result['total_generation']

    # Calculate cost spread (max - min marginal cost of dispatched units)
    active_marginal_costs = [
        mc for gen_name, mc in marginal_costs.items()
        if dispatch[gen_name] > 0
    ]

    if active_marginal_costs:
        cost_spread = max(active_marginal_costs) - min(active_marginal_costs)
    else:
        cost_spread = 0

    return {
        'average_cost': avg_cost,
        'marginal_cost': dispatch_result['lambda'],
        'cost_spread': cost_spread,
        'num_generators_active': sum(1 for p in dispatch.values() if p > 0),
        'utilization': dispatch_result['total_generation'] / sum(
            g for g in dispatch.values()
        ) if sum(dispatch.values()) > 0 else 0,
    }
