"""
Locational Marginal Price (LMP) Decomposition

Implementation of LMP analysis from Kirschen & Strbac
"Fundamentals of Power System Economics" Chapter 5.

Key concepts:
- LMP = Energy component + Congestion component + Loss component
- Shadow prices from optimal power flow
- Congestion rent and loss allocation
- Nodal vs zonal pricing
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Node:
    """
    Power system node/bus.

    Attributes:
        name: Node identifier
        load: Load at node (MW)
        generation: Generation at node (MW)
        lmp: Locational marginal price ($/MWh)
        lmp_energy: Energy component of LMP ($/MWh)
        lmp_congestion: Congestion component of LMP ($/MWh)
        lmp_loss: Loss component of LMP ($/MWh)
    """
    name: str
    load: float = 0.0
    generation: float = 0.0
    lmp: float = 0.0
    lmp_energy: float = 0.0
    lmp_congestion: float = 0.0
    lmp_loss: float = 0.0


class LMPAnalyzer:
    """
    Analyze and decompose Locational Marginal Prices.

    LMP represents the marginal cost of serving an additional MW at a location,
    considering energy costs, transmission congestion, and losses.
    """

    def __init__(self, nodes: Optional[List[Node]] = None):
        """
        Initialize LMP analyzer.

        Args:
            nodes: List of Node objects (optional)
        """
        self.nodes = nodes if nodes else []

    def decompose_lmp(
        self,
        lmp_total: float,
        energy_price: float,
        congestion_price: float,
    ) -> Dict[str, float]:
        """
        Decompose LMP into components.

        LMP = Energy + Congestion + Loss

        Args:
            lmp_total: Total LMP ($/MWh)
            energy_price: System energy price / lambda ($/MWh)
            congestion_price: Congestion component ($/MWh)

        Returns:
            Dictionary with components
        """
        loss_price = lmp_total - energy_price - congestion_price

        return {
            'lmp_total': lmp_total,
            'lmp_energy': energy_price,
            'lmp_congestion': congestion_price,
            'lmp_loss': loss_price,
            'energy_pct': (energy_price / lmp_total * 100) if lmp_total != 0 else 0,
            'congestion_pct': (congestion_price / lmp_total * 100) if lmp_total != 0 else 0,
            'loss_pct': (loss_price / lmp_total * 100) if lmp_total != 0 else 0,
        }

    def calculate_congestion_rent(
        self,
        lmp_data: pd.DataFrame,
        flow_data: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """
        Calculate total congestion rent in the system.

        Congestion rent = sum over all buses of:
            (LMP_congestion_i * net_injection_i)

        This represents the total payment for transmission constraints.

        Args:
            lmp_data: DataFrame with columns: node, lmp_congestion, net_injection
            flow_data: Optional DataFrame with transmission line flows

        Returns:
            Dictionary with congestion rent metrics
        """
        if 'net_injection' not in lmp_data.columns:
            # Calculate net injection as generation - load
            if 'generation' in lmp_data.columns and 'load' in lmp_data.columns:
                lmp_data = lmp_data.copy()
                lmp_data['net_injection'] = lmp_data['generation'] - lmp_data['load']
            else:
                raise ValueError("Need net_injection or (generation, load) columns")

        # Total congestion rent
        total_rent = (lmp_data['lmp_congestion'] * lmp_data['net_injection']).sum()

        # Separate generators (paying) and loads (receiving)
        generators = lmp_data[lmp_data['net_injection'] > 0].copy()
        loads = lmp_data[lmp_data['net_injection'] < 0].copy()

        generator_payments = (generators['lmp_congestion'] * generators['net_injection']).sum()
        load_payments = (loads['lmp_congestion'] * loads['net_injection']).sum()

        return {
            'total_congestion_rent': total_rent,
            'generator_congestion_payments': generator_payments,
            'load_congestion_credits': -load_payments,  # Negative because loads are negative injection
            'net_balance': total_rent,  # Should be ~0 in lossless case
        }

    def analyze_lmp_distribution(
        self,
        lmp_data: pd.DataFrame,
    ) -> Dict:
        """
        Analyze statistical distribution of LMPs across nodes.

        Args:
            lmp_data: DataFrame with LMP data by node

        Returns:
            Dictionary with distribution statistics
        """
        lmp_values = lmp_data['lmp_total'] if 'lmp_total' in lmp_data.columns else lmp_data['lmp']

        return {
            'mean_lmp': lmp_values.mean(),
            'median_lmp': lmp_values.median(),
            'std_lmp': lmp_values.std(),
            'min_lmp': lmp_values.min(),
            'max_lmp': lmp_values.max(),
            'range_lmp': lmp_values.max() - lmp_values.min(),
            'cv_lmp': lmp_values.std() / lmp_values.mean() if lmp_values.mean() != 0 else 0,
        }

    def identify_congested_nodes(
        self,
        lmp_data: pd.DataFrame,
        threshold: float = 5.0,
    ) -> pd.DataFrame:
        """
        Identify nodes with significant congestion.

        Nodes with |congestion component| > threshold are congested.

        Args:
            lmp_data: DataFrame with lmp_congestion column
            threshold: Threshold for significant congestion ($/MWh)

        Returns:
            DataFrame of congested nodes sorted by congestion magnitude
        """
        if 'lmp_congestion' not in lmp_data.columns:
            raise ValueError("lmp_data must have lmp_congestion column")

        congested = lmp_data[
            np.abs(lmp_data['lmp_congestion']) > threshold
        ].copy()

        congested['congestion_magnitude'] = np.abs(congested['lmp_congestion'])
        congested = congested.sort_values('congestion_magnitude', ascending=False)

        return congested

    def calculate_nodal_surplus(
        self,
        node_data: pd.DataFrame,
        system_lambda: float,
    ) -> pd.DataFrame:
        """
        Calculate nodal surplus (benefit/cost vs system average).

        Nodal surplus for generators = (LMP - system_lambda) * generation
        Nodal surplus for loads = (system_lambda - LMP) * load

        Args:
            node_data: DataFrame with columns: node, lmp, generation, load
            system_lambda: System marginal cost (reference price)

        Returns:
            DataFrame with nodal surplus calculations
        """
        result = node_data.copy()

        # Generator surplus (benefit from higher LMP)
        result['generator_surplus'] = (
            (result['lmp'] - system_lambda) * result['generation']
        )

        # Load surplus (benefit from lower LMP)
        result['load_surplus'] = (
            (system_lambda - result['lmp']) * result['load']
        )

        # Net surplus
        result['net_surplus'] = result['generator_surplus'] + result['load_surplus']

        return result

    def temporal_lmp_analysis(
        self,
        lmp_timeseries: pd.DataFrame,
        node_name: str,
    ) -> Dict:
        """
        Analyze LMP components over time for a specific node.

        Args:
            lmp_timeseries: DataFrame with columns: timestamp, node, lmp_*, ...
            node_name: Node to analyze

        Returns:
            Dictionary with temporal statistics
        """
        node_data = lmp_timeseries[
            lmp_timeseries['node'] == node_name
        ].copy()

        if len(node_data) == 0:
            raise ValueError(f"No data found for node: {node_name}")

        # Component statistics
        stats = {}

        for component in ['lmp_total', 'lmp_energy', 'lmp_congestion', 'lmp_loss']:
            if component in node_data.columns:
                values = node_data[component]
                stats[f'{component}_mean'] = values.mean()
                stats[f'{component}_std'] = values.std()
                stats[f'{component}_min'] = values.min()
                stats[f'{component}_max'] = values.max()

        # Congestion frequency
        if 'lmp_congestion' in node_data.columns:
            congested_hours = (np.abs(node_data['lmp_congestion']) > 1.0).sum()
            stats['congestion_frequency'] = congested_hours / len(node_data)

        # Price volatility
        if 'lmp_total' in node_data.columns:
            returns = node_data['lmp_total'].pct_change()
            stats['price_volatility'] = returns.std()

        return stats

    def compare_market_designs(
        self,
        nodal_lmps: pd.DataFrame,
        zonal_mapping: Dict[str, str],
    ) -> Dict:
        """
        Compare nodal vs zonal pricing.

        Calculate zonal average prices and compare to nodal prices.

        Args:
            nodal_lmps: DataFrame with nodal LMP data
            zonal_mapping: Dict mapping {node_name: zone_name}

        Returns:
            Dictionary with comparison metrics
        """
        # Add zone column
        df = nodal_lmps.copy()
        df['zone'] = df['node'].map(zonal_mapping)

        # Calculate zonal average LMPs (load-weighted if load data available)
        if 'load' in df.columns:
            zonal_prices = df.groupby('zone').apply(
                lambda x: (x['lmp'] * x['load']).sum() / x['load'].sum()
                if x['load'].sum() > 0 else x['lmp'].mean()
            ).to_dict()
        else:
            zonal_prices = df.groupby('zone')['lmp'].mean().to_dict()

        # Calculate nodal vs zonal difference
        df['zonal_lmp'] = df['zone'].map(zonal_prices)
        df['nodal_zonal_diff'] = df['lmp'] - df['zonal_lmp']

        # Calculate inefficiency (welfare loss) from zonal pricing
        # This is simplified - full calculation needs dispatch model
        if 'generation' in df.columns and 'load' in df.columns:
            # Generators get zonal price, pay nodal cost
            gen_inefficiency = (
                df['generation'] * (df['zonal_lmp'] - df['lmp'])
            ).sum()

            # Loads pay zonal price vs nodal value
            load_inefficiency = (
                df['load'] * (df['lmp'] - df['zonal_lmp'])
            ).sum()

            total_inefficiency = gen_inefficiency + load_inefficiency
        else:
            total_inefficiency = None

        return {
            'zonal_prices': zonal_prices,
            'nodal_zonal_diff_mean': df['nodal_zonal_diff'].mean(),
            'nodal_zonal_diff_std': df['nodal_zonal_diff'].std(),
            'nodal_zonal_diff_max': df['nodal_zonal_diff'].abs().max(),
            'total_inefficiency': total_inefficiency,
        }


def analyze_caiso_lmp_data(lmp_df: pd.DataFrame) -> Dict:
    """
    Analyze LMP data from CAISO OASIS API.

    Convenience function for analyzing CAISO LMP data from the client.

    Args:
        lmp_df: DataFrame from CAISOClient.get_lmp()

    Returns:
        Dictionary with comprehensive LMP analysis
    """
    analyzer = LMPAnalyzer()

    # Overall statistics
    overall_stats = {
        'total_records': len(lmp_df),
        'unique_locations': lmp_df['location'].nunique(),
        'time_range': (lmp_df['timestamp'].min(), lmp_df['timestamp'].max()),
    }

    # LMP distribution
    lmp_data = lmp_df.rename(columns={'lmp_total': 'lmp', 'location': 'node'})
    distribution = analyzer.analyze_lmp_distribution(lmp_data)

    # Component analysis
    component_stats = {}
    for component in ['lmp_energy', 'lmp_congestion', 'lmp_loss']:
        if component in lmp_df.columns:
            values = lmp_df[component]
            component_stats[component] = {
                'mean': values.mean(),
                'std': values.std(),
                'contribution_pct': (values.mean() / lmp_df['lmp_total'].mean() * 100)
                                   if lmp_df['lmp_total'].mean() != 0 else 0,
            }

    # Congested locations
    try:
        congested = analyzer.identify_congested_nodes(lmp_data, threshold=5.0)
        top_congested = congested.head(10)['node'].tolist()
    except (ValueError, KeyError):
        top_congested = []

    # Time-based patterns
    if 'timestamp' in lmp_df.columns:
        lmp_df['hour'] = pd.to_datetime(lmp_df['timestamp']).dt.hour
        hourly_avg = lmp_df.groupby('hour')['lmp_total'].mean()

        peak_hour = hourly_avg.idxmax()
        off_peak_hour = hourly_avg.idxmin()

        time_patterns = {
            'peak_hour': int(peak_hour),
            'peak_price': float(hourly_avg.max()),
            'off_peak_hour': int(off_peak_hour),
            'off_peak_price': float(hourly_avg.min()),
            'peak_to_offpeak_ratio': float(hourly_avg.max() / hourly_avg.min())
                                     if hourly_avg.min() > 0 else None,
        }
    else:
        time_patterns = {}

    return {
        'overall': overall_stats,
        'distribution': distribution,
        'components': component_stats,
        'top_congested_locations': top_congested,
        'time_patterns': time_patterns,
    }


def calculate_system_cost(
    lmp_df: pd.DataFrame,
    load_df: pd.DataFrame,
) -> Dict:
    """
    Calculate total system cost from LMP and load data.

    Total cost = sum(LMP_i * Load_i) for all nodes i

    Args:
        lmp_df: DataFrame with LMP by node
        load_df: DataFrame with load by node

    Returns:
        Dictionary with cost metrics
    """
    # Merge LMP and load data
    merged = pd.merge(
        lmp_df,
        load_df,
        left_on=['timestamp', 'location'],
        right_on=['timestamp', 'location'],
        how='inner',
    )

    # Calculate cost at each node-time
    merged['cost'] = merged['lmp_total'] * merged['load_mw']

    # Aggregate
    total_cost = merged['cost'].sum()
    total_energy = merged['load_mw'].sum()
    avg_price = total_cost / total_energy if total_energy > 0 else 0

    # By time period
    time_costs = merged.groupby('timestamp').agg({
        'cost': 'sum',
        'load_mw': 'sum',
    })
    time_costs['avg_price'] = time_costs['cost'] / time_costs['load_mw']

    return {
        'total_cost': total_cost,
        'total_energy': total_energy,
        'load_weighted_avg_price': avg_price,
        'time_series': time_costs,
    }
