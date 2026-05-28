"""
Clean, professional visualizations for CAISO OASIS data.

Creates publication-quality plots for LMP, fuel mix, and load data.
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

# Modern, clean style
plt.style.use('default')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = '#f8f9fa'
plt.rcParams['axes.edgecolor'] = '#dee2e6'
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['grid.color'] = '#dee2e6'
plt.rcParams['grid.linestyle'] = '-'
plt.rcParams['grid.linewidth'] = 0.8
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']
plt.rcParams['font.size'] = 11
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['legend.fontsize'] = 10
plt.rcParams['figure.titlesize'] = 16
plt.rcParams['figure.titleweight'] = 'bold'


# Professional color palette
COLORS = {
    'primary': '#2c3e50',
    'secondary': '#3498db',
    'success': '#27ae60',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'info': '#16a085',
    'purple': '#9b59b6',
    'teal': '#1abc9c',
    'pink': '#e91e63',
    'orange': '#ff6f00',
}


def format_axis(ax, title, xlabel=None, ylabel=None):
    """Apply consistent formatting to an axis."""
    ax.set_title(title, pad=15, fontweight='bold', fontsize=14, color=COLORS['primary'])
    if xlabel:
        ax.set_xlabel(xlabel, fontweight='bold', fontsize=11, color=COLORS['primary'])
    if ylabel:
        ax.set_ylabel(ylabel, fontweight='bold', fontsize=11, color=COLORS['primary'])
    ax.grid(True, alpha=0.3, linewidth=0.8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_linewidth(1.2)
    ax.spines['bottom'].set_linewidth(1.2)


def plot_lmp_components(lmp_df: pd.DataFrame, location: str = None):
    """
    Clean LMP visualization with component breakdown.
    """
    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.2, 1.5, 0.3], hspace=0.35)

    # Filter data
    if location:
        df = lmp_df[lmp_df['location'] == location].copy()
        title_suffix = f" - {location}"
    else:
        df = lmp_df.groupby('timestamp').agg({
            'lmp_total': 'mean',
            'lmp_energy': 'mean',
            'lmp_congestion': 'mean',
            'lmp_loss': 'mean',
        }).reset_index()
        title_suffix = " (System Average)"

    df = df.sort_values('timestamp')

    # Plot 1: Total LMP
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df['timestamp'], df['lmp_total'], linewidth=2.5, color=COLORS['secondary'],
             label='Total LMP', zorder=3)
    ax1.fill_between(df['timestamp'], 0, df['lmp_total'], alpha=0.2, color=COLORS['secondary'])

    # Add stats text box
    mean_lmp = df['lmp_total'].mean()
    max_lmp = df['lmp_total'].max()
    min_lmp = df['lmp_total'].min()
    stats_text = f"Mean: ${mean_lmp:.2f}  |  Range: ${min_lmp:.2f} - ${max_lmp:.2f}"
    ax1.text(0.02, 0.95, stats_text, transform=ax1.transAxes,
             bbox=dict(boxstyle='round', facecolor='white', edgecolor=COLORS['secondary'], linewidth=1.5),
             verticalalignment='top', fontsize=10, family='monospace')

    format_axis(ax1, f'Locational Marginal Price{title_suffix}', ylabel='Price ($/MWh)')
    ax1.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))

    # Plot 2: Component Breakdown
    ax2 = fig.add_subplot(gs[1])

    # Calculate component percentages
    energy_pct = (df['lmp_energy'].mean() / df['lmp_total'].mean() * 100)
    cong_pct = (df['lmp_congestion'].mean() / df['lmp_total'].mean() * 100)
    loss_pct = (df['lmp_loss'].mean() / df['lmp_total'].mean() * 100)

    # Stacked area plot
    ax2.fill_between(df['timestamp'], 0, df['lmp_energy'],
                     label=f'Energy ({energy_pct:.1f}%)', alpha=0.85, color=COLORS['success'])
    ax2.fill_between(df['timestamp'], df['lmp_energy'],
                     df['lmp_energy'] + df['lmp_congestion'],
                     label=f'Congestion ({cong_pct:.1f}%)', alpha=0.85, color=COLORS['warning'])
    ax2.fill_between(df['timestamp'],
                     df['lmp_energy'] + df['lmp_congestion'],
                     df['lmp_total'],
                     label=f'Loss ({loss_pct:.1f}%)', alpha=0.85, color=COLORS['danger'])

    format_axis(ax2, 'LMP Component Breakdown', xlabel='Time', ylabel='Price Component ($/MWh)')
    ax2.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, ncol=3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=0, ha='center')

    # Plot 3: Color legend explanation
    ax3 = fig.add_subplot(gs[2])
    ax3.axis('off')
    legend_text = ("💡 Energy: Base generation cost  |  "
                   "⚡ Congestion: Transmission constraint cost  |  "
                   "📉 Loss: Transmission loss cost")
    ax3.text(0.5, 0.5, legend_text, ha='center', va='center',
             fontsize=10, style='italic', color='#555')

    return fig


def plot_trading_hubs_comparison(lmp_df: pd.DataFrame):
    """
    Clean comparison of trading hub prices.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2, 1])

    hub_info = {
        'TH_NP15_GEN-APND': {'label': 'NP15 (Northern CA)', 'color': COLORS['secondary']},
        'TH_SP15_GEN-APND': {'label': 'SP15 (Southern CA)', 'color': COLORS['danger']},
        'TH_ZP26_GEN-APND': {'label': 'ZP26 (San Diego)', 'color': COLORS['warning']},
    }

    # Plot 1: Price comparison
    for hub, info in hub_info.items():
        hub_data = lmp_df[lmp_df['location'] == hub].copy()
        if not hub_data.empty:
            hub_data = hub_data.sort_values('timestamp')
            ax1.plot(hub_data['timestamp'], hub_data['lmp_total'],
                    linewidth=2.5, label=info['label'], color=info['color'], alpha=0.9)

    format_axis(ax1, 'CAISO Trading Hub Price Comparison', ylabel='LMP ($/MWh)')
    ax1.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))

    # Plot 2: Price spread (difference from average)
    avg_lmp = lmp_df.groupby('timestamp')['lmp_total'].mean()

    for hub, info in hub_info.items():
        hub_data = lmp_df[lmp_df['location'] == hub].copy()
        if not hub_data.empty:
            hub_data = hub_data.sort_values('timestamp')
            hub_data = hub_data.set_index('timestamp')
            spread = hub_data['lmp_total'] - avg_lmp
            ax2.plot(spread.index, spread.values,
                    linewidth=2, label=info['label'], color=info['color'], alpha=0.9)

    ax2.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    format_axis(ax2, 'Price Spread vs System Average',
                xlabel='Time', ylabel='Price Difference ($/MWh)')
    ax2.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=0, ha='center')

    plt.tight_layout()
    return fig


def plot_fuel_mix(fuel_df: pd.DataFrame):
    """
    Clean fuel mix visualization.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), height_ratios=[2.5, 1.5])

    # Pivot data
    df_wide = fuel_df.pivot(index='timestamp', columns='fuel_type', values='generation_mw')
    df_wide = df_wide.fillna(0).sort_index()

    # Color scheme for fuels
    fuel_colors = {
        'Solar': '#FDB813', 'Wind': '#27ae60', 'Natural Gas': '#e74c3c',
        'Nuclear': '#3498db', 'Large Hydro': '#1abc9c', 'Small Hydro': '#16a085',
        'Imports': '#95a5a6', 'Geothermal': '#d35400', 'Biomass': '#8BC34A',
        'Biogas': '#7CB342', 'Batteries': '#9b59b6', 'Coal': '#34495e', 'Other': '#7f8c8d',
    }

    # Separate generation and storage
    df_positive = df_wide.clip(lower=0)

    # Plot 1: Generation stack
    columns_to_plot = [col for col in df_positive.columns if df_positive[col].sum() > 0]
    # Sort by average generation for cleaner stacking
    col_order = df_positive[columns_to_plot].mean().sort_values(ascending=True).index

    colors = [fuel_colors.get(col, '#7f8c8d') for col in col_order]

    ax1.stackplot(df_positive.index,
                  *[df_positive[col] for col in col_order],
                  labels=col_order,
                  colors=colors,
                  alpha=0.9)

    format_axis(ax1, 'California Generation Mix by Fuel Type', ylabel='Generation (MW)')
    ax1.legend(loc='upper left', bbox_to_anchor=(1, 1), frameon=True, fancybox=True, shadow=True)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))

    # Plot 2: Battery activity
    if 'Batteries' in df_wide.columns:
        battery_data = df_wide['Batteries']

        # Charging (negative)
        ax2.fill_between(battery_data.index, 0, battery_data,
                        where=(battery_data < 0),
                        color=COLORS['pink'], alpha=0.8, label='Charging', interpolate=True)
        # Discharging (positive)
        ax2.fill_between(battery_data.index, 0, battery_data,
                        where=(battery_data >= 0),
                        color=COLORS['purple'], alpha=0.8, label='Discharging', interpolate=True)

        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)

        # Add stats
        max_discharge = battery_data.max()
        max_charge = battery_data.min()
        stats_text = f"Max Discharge: {max_discharge:.0f} MW  |  Max Charge: {abs(max_charge):.0f} MW"
        ax2.text(0.02, 0.95, stats_text, transform=ax2.transAxes,
                bbox=dict(boxstyle='round', facecolor='white', edgecolor=COLORS['purple'], linewidth=1.5),
                verticalalignment='top', fontsize=10, family='monospace')

        format_axis(ax2, 'Battery Storage Activity (Duck Curve Response)',
                   xlabel='Time', ylabel='Power (MW)')
        ax2.legend(loc='upper right', frameon=True, fancybox=True, shadow=True)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=0, ha='center')

    plt.tight_layout()
    return fig


def plot_fuel_mix_pie(fuel_df: pd.DataFrame):
    """
    Clean pie chart of average fuel mix.
    """
    fig, ax = plt.subplots(figsize=(14, 9))

    # Calculate averages
    avg_by_fuel = fuel_df.groupby('fuel_type')['generation_mw'].mean()
    avg_by_fuel = avg_by_fuel[avg_by_fuel > 50].sort_values(ascending=False)

    # Colors
    fuel_colors = {
        'Solar': '#FDB813', 'Wind': '#27ae60', 'Natural Gas': '#e74c3c',
        'Nuclear': '#3498db', 'Large Hydro': '#1abc9c', 'Small Hydro': '#16a085',
        'Imports': '#95a5a6', 'Geothermal': '#d35400', 'Biomass': '#8BC34A',
        'Biogas': '#7CB342', 'Coal': '#34495e',
    }
    colors = [fuel_colors.get(fuel, '#7f8c8d') for fuel in avg_by_fuel.index]

    # Create pie chart with better styling
    wedges, texts, autotexts = ax.pie(avg_by_fuel.values,
                                       labels=avg_by_fuel.index,
                                       autopct='%1.1f%%',
                                       colors=colors,
                                       startangle=90,
                                       textprops={'fontsize': 11, 'weight': 'bold'},
                                       pctdistance=0.85,
                                       explode=[0.05 if i == 0 else 0 for i in range(len(avg_by_fuel))])

    # Make percentage text white and bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(11)
        autotext.set_weight('bold')

    # Make labels bold
    for text in texts:
        text.set_fontsize(12)
        text.set_weight('bold')

    ax.set_title('Average California Generation Mix',
                 pad=20, fontweight='bold', fontsize=16, color=COLORS['primary'])

    # Add center text
    total_gen = avg_by_fuel.sum()
    centre_circle = plt.Circle((0, 0), 0.70, fc='white', linewidth=2, edgecolor='#dee2e6')
    ax.add_artist(centre_circle)
    ax.text(0, 0.05, f'{total_gen:.0f} MW', ha='center', va='center',
            fontsize=20, fontweight='bold', color=COLORS['primary'])
    ax.text(0, -0.15, 'Average\nGeneration', ha='center', va='center',
            fontsize=11, style='italic', color='#555')

    plt.tight_layout()
    return fig


def plot_load_profile(load_df: pd.DataFrame):
    """
    Clean load profile visualization.
    """
    fig, ax = plt.subplots(figsize=(16, 7))

    df = load_df.sort_values('timestamp')

    # Main load curve
    ax.plot(df['timestamp'], df['load_mw'], linewidth=2.5,
            color=COLORS['secondary'], label='System Load', zorder=3)
    ax.fill_between(df['timestamp'], 0, df['load_mw'],
                    alpha=0.2, color=COLORS['secondary'])

    # Add forecast if available
    if 'load_forecast_mw' in df.columns:
        ax.plot(df['timestamp'], df['load_forecast_mw'],
               linewidth=2, linestyle='--', color=COLORS['warning'],
               label='Forecast', alpha=0.8)

    # Calculate and display statistics
    min_load = df['load_mw'].min()
    max_load = df['load_mw'].max()
    avg_load = df['load_mw'].mean()
    peak_ratio = max_load / min_load if min_load > 0 else 0

    stats_text = (f"Min: {min_load:,.0f} MW  |  "
                 f"Max: {max_load:,.0f} MW  |  "
                 f"Avg: {avg_load:,.0f} MW  |  "
                 f"Peak/Min: {peak_ratio:.2f}x")

    ax.text(0.5, 0.97, stats_text, transform=ax.transAxes,
           bbox=dict(boxstyle='round', facecolor='white', edgecolor=COLORS['secondary'], linewidth=2),
           verticalalignment='top', horizontalalignment='center',
           fontsize=11, family='monospace', fontweight='bold')

    format_axis(ax, 'CAISO System Load Profile',
               xlabel='Time', ylabel='Load (MW)')
    ax.legend(loc='lower left', frameon=True, fancybox=True, shadow=True)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d\n%H:%M'))
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=0, ha='center')

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

    plt.tight_layout()
    return fig


def create_market_dashboard(hours: int = 24):
    """
    Create comprehensive market dashboard with clean visualizations.
    """
    print(f"📊 Fetching CAISO market data (last {hours} hours)...")
    end = datetime.now()
    start = end - timedelta(hours=hours)

    with CAISOClient() as client:
        lmp = client.get_lmp(start, end, market="RTM")
        trading_hub_lmp = client.get_trading_hub_lmp(start, end, market="RTM")
        fuel_mix = client.get_fuel_mix(start, end)
        load = client.get_load(start, end)

    print(f"✓ Retrieved {len(lmp)} LMP records")
    print(f"✓ Retrieved {len(fuel_mix)} fuel mix records")
    print(f"✓ Retrieved {len(load)} load records\n")

    print("🎨 Creating visualizations...")

    print("  1/5 LMP components...")
    fig1 = plot_lmp_components(lmp)

    print("  2/5 Trading hubs...")
    fig2 = plot_trading_hubs_comparison(trading_hub_lmp)

    print("  3/5 Fuel mix stack...")
    fig3 = plot_fuel_mix(fuel_mix)

    print("  4/5 Fuel mix pie...")
    fig4 = plot_fuel_mix_pie(fuel_mix)

    print("  5/5 Load profile...")
    fig5 = plot_load_profile(load)

    # Save all figures
    output_dir = Path(__file__).parent.parent / 'data' / 'plots'
    output_dir.mkdir(exist_ok=True, parents=True)

    print("\n💾 Saving plots...")
    fig1.savefig(output_dir / 'lmp_components.png', dpi=200, bbox_inches='tight', facecolor='white')
    fig2.savefig(output_dir / 'trading_hubs.png', dpi=200, bbox_inches='tight', facecolor='white')
    fig3.savefig(output_dir / 'fuel_mix_stack.png', dpi=200, bbox_inches='tight', facecolor='white')
    fig4.savefig(output_dir / 'fuel_mix_pie.png', dpi=200, bbox_inches='tight', facecolor='white')
    fig5.savefig(output_dir / 'load_profile.png', dpi=200, bbox_inches='tight', facecolor='white')

    print(f"✅ All plots saved to: {output_dir}")
    print("\n📂 View online:")
    print("   → GitHub: https://github.com/Maaz679/caiso-oasis-analysis/tree/main/data/plots")
    print(f"   → Local:  file://{output_dir.absolute()}/view_plots.html")

    plt.close('all')


if __name__ == "__main__":
    create_market_dashboard(hours=24)
