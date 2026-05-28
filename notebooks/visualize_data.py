"""
Visualization examples for CAISO OASIS data.

Creates informative plots for LMP, fuel mix, and load data.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.oasis import CAISOClient

# Set up matplotlib style
plt.style.use('seaborn-v0_8-darkgrid')
plt.rcParams['figure.figsize'] = (14, 10)
plt.rcParams['font.size'] = 10


def plot_lmp_components(lmp_df: pd.DataFrame, location: str = None):
    """
    Plot LMP with stacked components (energy, congestion, loss).

    Args:
        lmp_df: LMP DataFrame from CAISOClient
        location: Specific location to plot (if None, averages across all)
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Filter by location if specified
    if location:
        df = lmp_df[lmp_df['location'] == location].copy()
        title_suffix = f" at {location}"
    else:
        # Average across all locations
        df = lmp_df.groupby('timestamp').agg({
            'lmp_total': 'mean',
            'lmp_energy': 'mean',
            'lmp_congestion': 'mean',
            'lmp_loss': 'mean',
        }).reset_index()
        title_suffix = " (System Average)"

    df = df.sort_values('timestamp')

    # Plot 1: Total LMP over time
    ax1.plot(df['timestamp'], df['lmp_total'], linewidth=2, color='#2E86AB', label='Total LMP')
    ax1.fill_between(df['timestamp'], 0, df['lmp_total'], alpha=0.3, color='#2E86AB')
    ax1.set_ylabel('Price ($/MWh)', fontsize=12, fontweight='bold')
    ax1.set_title(f'Locational Marginal Price{title_suffix}', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')

    # Format x-axis
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Stacked components
    ax2.fill_between(df['timestamp'], 0, df['lmp_energy'],
                     label='Energy', alpha=0.8, color='#A23B72')
    ax2.fill_between(df['timestamp'], df['lmp_energy'],
                     df['lmp_energy'] + df['lmp_congestion'],
                     label='Congestion', alpha=0.8, color='#F18F01')
    ax2.fill_between(df['timestamp'],
                     df['lmp_energy'] + df['lmp_congestion'],
                     df['lmp_total'],
                     label='Loss', alpha=0.8, color='#C73E1D')

    ax2.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Price Component ($/MWh)', fontsize=12, fontweight='bold')
    ax2.set_title(f'LMP Components Breakdown{title_suffix}', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')

    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return fig


def plot_trading_hubs_comparison(lmp_df: pd.DataFrame):
    """
    Compare LMP across major trading hubs (NP15, SP15, ZP26).

    Args:
        lmp_df: LMP DataFrame with trading hub data
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    # Map hub names to readable labels
    hub_labels = {
        'TH_NP15_GEN-APND': 'NP15 (Northern CA)',
        'TH_SP15_GEN-APND': 'SP15 (Southern CA)',
        'TH_ZP26_GEN-APND': 'ZP26 (San Diego)',
    }

    colors = ['#2E86AB', '#A23B72', '#F18F01']

    for i, (hub, label) in enumerate(hub_labels.items()):
        hub_data = lmp_df[lmp_df['location'] == hub].copy()
        if not hub_data.empty:
            hub_data = hub_data.sort_values('timestamp')
            ax.plot(hub_data['timestamp'], hub_data['lmp_total'],
                   linewidth=2, label=label, color=colors[i], alpha=0.8)

    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('LMP ($/MWh)', fontsize=12, fontweight='bold')
    ax.set_title('CAISO Trading Hub Price Comparison', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=11)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return fig


def plot_fuel_mix(fuel_df: pd.DataFrame):
    """
    Plot fuel mix as stacked area chart.

    Args:
        fuel_df: Fuel mix DataFrame from CAISOClient
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    # Pivot to wide format for stacking
    df_wide = fuel_df.pivot(index='timestamp', columns='fuel_type', values='generation_mw')
    df_wide = df_wide.fillna(0).sort_index()

    # Separate positive (generation) and negative (storage charging)
    df_positive = df_wide.clip(lower=0)
    df_negative = df_wide.clip(upper=0)

    # Define color scheme for fuel types
    fuel_colors = {
        'Solar': '#F4B400',
        'Wind': '#0F9D58',
        'Natural Gas': '#DB4437',
        'Nuclear': '#4285F4',
        'Large Hydro': '#00ACC1',
        'Small Hydro': '#0097A7',
        'Imports': '#9E9E9E',
        'Geothermal': '#FF6F00',
        'Biomass': '#8BC34A',
        'Biogas': '#7CB342',
        'Batteries': '#9C27B0',
        'Coal': '#424242',
        'Other': '#757575',
    }

    # Plot 1: Stacked area chart for generation
    columns_to_plot = [col for col in df_positive.columns if df_positive[col].sum() > 0]
    colors = [fuel_colors.get(col, '#757575') for col in columns_to_plot]

    ax1.stackplot(df_positive.index,
                  *[df_positive[col] for col in columns_to_plot],
                  labels=columns_to_plot,
                  colors=colors,
                  alpha=0.8)

    ax1.set_ylabel('Generation (MW)', fontsize=12, fontweight='bold')
    ax1.set_title('CAISO Fuel Mix - Generation Stack', fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Battery storage (if charging/discharging)
    if 'Batteries' in df_wide.columns:
        battery_data = df_wide['Batteries']
        ax2.fill_between(battery_data.index, 0, battery_data,
                        where=(battery_data >= 0),
                        color='#9C27B0', alpha=0.7, label='Discharging')
        ax2.fill_between(battery_data.index, 0, battery_data,
                        where=(battery_data < 0),
                        color='#E91E63', alpha=0.7, label='Charging')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_ylabel('Battery Power (MW)', fontsize=12, fontweight='bold')
        ax2.set_title('Battery Storage Activity', fontsize=14, fontweight='bold')
        ax2.legend(loc='upper right', fontsize=10)
        ax2.grid(True, alpha=0.3)

    ax2.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    return fig


def plot_fuel_mix_pie(fuel_df: pd.DataFrame):
    """
    Plot average fuel mix as pie chart.

    Args:
        fuel_df: Fuel mix DataFrame from CAISOClient
    """
    fig, ax = plt.subplots(figsize=(12, 8))

    # Calculate average generation by fuel type
    avg_by_fuel = fuel_df.groupby('fuel_type')['generation_mw'].mean()

    # Filter out negative values (storage charging) and very small values
    avg_by_fuel = avg_by_fuel[avg_by_fuel > 50].sort_values(ascending=False)

    # Color scheme
    fuel_colors = {
        'Solar': '#F4B400',
        'Wind': '#0F9D58',
        'Natural Gas': '#DB4437',
        'Nuclear': '#4285F4',
        'Large Hydro': '#00ACC1',
        'Small Hydro': '#0097A7',
        'Imports': '#9E9E9E',
        'Geothermal': '#FF6F00',
        'Biomass': '#8BC34A',
        'Biogas': '#7CB342',
        'Coal': '#424242',
    }

    colors = [fuel_colors.get(fuel, '#757575') for fuel in avg_by_fuel.index]

    # Create pie chart
    wedges, texts, autotexts = ax.pie(avg_by_fuel.values,
                                       labels=avg_by_fuel.index,
                                       autopct='%1.1f%%',
                                       colors=colors,
                                       startangle=90,
                                       textprops={'fontsize': 11, 'weight': 'bold'})

    # Enhance autotext
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)

    ax.set_title('Average Generation by Fuel Type', fontsize=14, fontweight='bold', pad=20)

    # Add legend with MW values
    legend_labels = [f'{fuel}: {mw:.0f} MW' for fuel, mw in avg_by_fuel.items()]
    ax.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)

    plt.tight_layout()
    return fig


def plot_load_profile(load_df: pd.DataFrame):
    """
    Plot system load profile.

    Args:
        load_df: Load DataFrame from CAISOClient
    """
    fig, ax = plt.subplots(figsize=(14, 6))

    df = load_df.sort_values('timestamp')

    ax.plot(df['timestamp'], df['load_mw'], linewidth=2, color='#2E86AB', label='Actual Load')
    ax.fill_between(df['timestamp'], 0, df['load_mw'], alpha=0.3, color='#2E86AB')

    # Add forecast if available
    if 'load_forecast_mw' in df.columns:
        ax.plot(df['timestamp'], df['load_forecast_mw'],
               linewidth=2, linestyle='--', color='#F18F01', label='Forecast')

    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('Load (MW)', fontsize=12, fontweight='bold')
    ax.set_title('CAISO System Load Profile', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=11)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Add statistics box
    stats_text = f"Min: {df['load_mw'].min():.0f} MW\n"
    stats_text += f"Max: {df['load_mw'].max():.0f} MW\n"
    stats_text += f"Avg: {df['load_mw'].mean():.0f} MW\n"
    stats_text += f"Peak/Min Ratio: {df['load_mw'].max() / df['load_mw'].min():.2f}"

    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
           fontsize=10, family='monospace')

    plt.tight_layout()
    return fig


def create_market_dashboard(hours: int = 24):
    """
    Create a comprehensive market dashboard with all visualizations.

    Args:
        hours: Number of hours of historical data to visualize
    """
    print("Fetching CAISO market data...")
    end = datetime.now()
    start = end - timedelta(hours=hours)

    with CAISOClient() as client:
        # Fetch all data
        lmp = client.get_lmp(start, end, market="RTM")
        trading_hub_lmp = client.get_trading_hub_lmp(start, end, market="RTM")
        fuel_mix = client.get_fuel_mix(start, end)
        load = client.get_load(start, end)

    print(f"\nCreating visualizations for {hours} hours of data...")
    print(f"  - LMP records: {len(lmp)}")
    print(f"  - Fuel mix records: {len(fuel_mix)}")
    print(f"  - Load records: {len(load)}")

    # Create all plots
    print("\n1. Plotting LMP components...")
    fig1 = plot_lmp_components(lmp)

    print("2. Plotting trading hub comparison...")
    fig2 = plot_trading_hubs_comparison(trading_hub_lmp)

    print("3. Plotting fuel mix stack...")
    fig3 = plot_fuel_mix(fuel_mix)

    print("4. Plotting fuel mix pie chart...")
    fig4 = plot_fuel_mix_pie(fuel_mix)

    print("5. Plotting load profile...")
    fig5 = plot_load_profile(load)

    # Save figures
    output_dir = Path(__file__).parent.parent / 'data' / 'plots'
    output_dir.mkdir(exist_ok=True, parents=True)

    fig1.savefig(output_dir / 'lmp_components.png', dpi=150, bbox_inches='tight')
    fig2.savefig(output_dir / 'trading_hubs.png', dpi=150, bbox_inches='tight')
    fig3.savefig(output_dir / 'fuel_mix_stack.png', dpi=150, bbox_inches='tight')
    fig4.savefig(output_dir / 'fuel_mix_pie.png', dpi=150, bbox_inches='tight')
    fig5.savefig(output_dir / 'load_profile.png', dpi=150, bbox_inches='tight')

    print(f"\n✓ All plots saved to: {output_dir}")
    print("\nShowing plots...")
    plt.show()


if __name__ == "__main__":
    create_market_dashboard(hours=24)
