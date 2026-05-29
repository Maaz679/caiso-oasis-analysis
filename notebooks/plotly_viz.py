"""
Interactive Plotly visualizations for CAISO OASIS data.

Creates interactive web-friendly plots that render directly in the browser.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_lmp_components(lmp_df: pd.DataFrame):
    """Interactive LMP visualization with component breakdown."""
    # Aggregate data
    df = lmp_df.groupby('timestamp').agg({
        'lmp_total': 'mean',
        'lmp_energy': 'mean',
        'lmp_congestion': 'mean',
        'lmp_loss': 'mean',
    }).reset_index().sort_values('timestamp')

    # Create subplots
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.4, 0.6],
        subplot_titles=('Total LMP Over Time', 'LMP Component Breakdown'),
        vertical_spacing=0.12
    )

    # Top: Total LMP
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['lmp_total'],
            fill='tozeroy',
            name='Total LMP',
            line=dict(color='#3498db', width=2),
            fillcolor='rgba(52, 152, 219, 0.2)'
        ),
        row=1, col=1
    )

    # Bottom: Stacked components
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['lmp_energy'],
            fill='tozeroy',
            name='Energy',
            line=dict(color='#27ae60', width=0),
            fillcolor='rgba(39, 174, 96, 0.8)',
            stackgroup='one'
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['lmp_congestion'],
            fill='tonexty',
            name='Congestion',
            line=dict(color='#f39c12', width=0),
            fillcolor='rgba(243, 156, 18, 0.8)',
            stackgroup='one'
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['lmp_loss'],
            fill='tonexty',
            name='Loss',
            line=dict(color='#e74c3c', width=0),
            fillcolor='rgba(231, 76, 60, 0.8)',
            stackgroup='one'
        ),
        row=2, col=1
    )

    # Update layout
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Price ($/MWh)", row=1, col=1)
    fig.update_yaxes(title_text="Price ($/MWh)", row=2, col=1)

    fig.update_layout(
        height=600,
        hovermode='x unified',
        template='plotly_white',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=40, t=80, b=60)
    )

    return fig


def plot_trading_hubs(lmp_df: pd.DataFrame):
    """Interactive trading hub price comparison."""
    hub_info = {
        'TH_NP15_GEN-APND': {'label': 'NP15 (Northern CA)', 'color': '#3498db'},
        'TH_SP15_GEN-APND': {'label': 'SP15 (Southern CA)', 'color': '#e74c3c'},
        'TH_ZP26_GEN-APND': {'label': 'ZP26 (San Diego)', 'color': '#f39c12'},
    }

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.5, 0.5],
        subplot_titles=('Regional Price Comparison', 'Price Spread vs System Average'),
        vertical_spacing=0.12
    )

    # Calculate average for spread
    avg_lmp = lmp_df.groupby('timestamp')['lmp_total'].mean()

    for hub, info in hub_info.items():
        hub_data = lmp_df[lmp_df['location'] == hub].copy().sort_values('timestamp')
        if not hub_data.empty:
            # Top: Actual prices
            fig.add_trace(
                go.Scatter(
                    x=hub_data['timestamp'],
                    y=hub_data['lmp_total'],
                    name=info['label'],
                    line=dict(color=info['color'], width=2.5),
                    mode='lines'
                ),
                row=1, col=1
            )

            # Bottom: Spread
            hub_data = hub_data.set_index('timestamp')
            spread = hub_data['lmp_total'] - avg_lmp
            fig.add_trace(
                go.Scatter(
                    x=spread.index,
                    y=spread.values,
                    name=info['label'],
                    line=dict(color=info['color'], width=2),
                    mode='lines',
                    showlegend=False
                ),
                row=2, col=1
            )

    # Add zero line to spread chart
    fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.5, row=2, col=1)

    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="LMP ($/MWh)", row=1, col=1)
    fig.update_yaxes(title_text="Difference ($/MWh)", row=2, col=1)

    fig.update_layout(
        height=600,
        hovermode='x unified',
        template='plotly_white',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=40, t=80, b=60)
    )

    return fig


def plot_fuel_mix(fuel_df: pd.DataFrame):
    """Interactive fuel mix stacked area chart."""
    # Pivot data
    df_wide = fuel_df.pivot(index='timestamp', columns='fuel_type', values='generation_mw')
    df_wide = df_wide.fillna(0).sort_index()

    # Color scheme
    fuel_colors = {
        'Solar': '#FDB813', 'Wind': '#27ae60', 'Natural Gas': '#e74c3c',
        'Nuclear': '#3498db', 'Large Hydro': '#1abc9c', 'Small Hydro': '#16a085',
        'Imports': '#95a5a6', 'Geothermal': '#d35400', 'Biomass': '#8BC34A',
        'Biogas': '#7CB342', 'Batteries': '#9b59b6', 'Coal': '#34495e', 'Other': '#7f8c8d',
    }

    # Only positive generation
    df_positive = df_wide.clip(lower=0)
    columns_to_plot = [col for col in df_positive.columns if df_positive[col].sum() > 0]
    col_order = df_positive[columns_to_plot].mean().sort_values(ascending=True).index

    fig = go.Figure()

    for fuel in col_order:
        fig.add_trace(
            go.Scatter(
                x=df_positive.index,
                y=df_positive[fuel],
                name=fuel,
                mode='lines',
                line=dict(width=0),
                fillcolor=fuel_colors.get(fuel, '#7f8c8d'),
                stackgroup='one',
                groupnorm='',
                hovertemplate='%{y:.0f} MW<extra></extra>'
            )
        )

    fig.update_layout(
        title='California Generation Mix by Fuel Type',
        xaxis_title='Time',
        yaxis_title='Generation (MW)',
        height=500,
        hovermode='x unified',
        template='plotly_white',
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(l=60, r=150, t=80, b=60)
    )

    return fig


def plot_fuel_mix_pie(fuel_df: pd.DataFrame):
    """Interactive pie chart of average fuel mix."""
    avg_by_fuel = fuel_df.groupby('fuel_type')['generation_mw'].mean()
    avg_by_fuel = avg_by_fuel[avg_by_fuel > 50].sort_values(ascending=False)

    # Combine small slices
    threshold_pct = 2.0
    total = avg_by_fuel.sum()
    large_slices = avg_by_fuel[avg_by_fuel / total * 100 >= threshold_pct]
    small_slices = avg_by_fuel[avg_by_fuel / total * 100 < threshold_pct]

    if len(small_slices) > 0:
        other_total = small_slices.sum()
        large_slices = pd.concat([large_slices, pd.Series({'Other': other_total})])

    fuel_colors = {
        'Solar': '#FDB813', 'Wind': '#27ae60', 'Natural Gas': '#e74c3c',
        'Nuclear': '#3498db', 'Large Hydro': '#1abc9c', 'Small Hydro': '#16a085',
        'Imports': '#95a5a6', 'Geothermal': '#d35400', 'Biomass': '#8BC34A',
        'Biogas': '#7CB342', 'Batteries': '#9b59b6', 'Coal': '#34495e', 'Other': '#7f8c8d',
    }

    colors = [fuel_colors.get(fuel, '#7f8c8d') for fuel in large_slices.index]

    fig = go.Figure(data=[go.Pie(
        labels=large_slices.index,
        values=large_slices.values,
        marker=dict(colors=colors),
        hovertemplate='%{label}<br>%{value:.0f} MW<br>%{percent}<extra></extra>',
        textposition='auto',
        textinfo='label+percent'
    )])

    fig.update_layout(
        title='Average California Generation Mix (Past 12 Hours)',
        height=500,
        template='plotly_white',
        showlegend=False,
        margin=dict(l=40, r=40, t=80, b=40)
    )

    return fig


def plot_load_profile(load_df: pd.DataFrame):
    """Interactive load profile chart."""
    df = load_df.sort_values('timestamp')

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['load_mw'],
            fill='tozeroy',
            name='System Load',
            line=dict(color='#3498db', width=2.5),
            fillcolor='rgba(52, 152, 219, 0.3)',
            hovertemplate='%{y:,.0f} MW<extra></extra>'
        )
    )

    # Add mean line
    mean_load = df['load_mw'].mean()
    fig.add_hline(
        y=mean_load,
        line_dash="dash",
        line_color="red",
        opacity=0.5,
        annotation_text=f"Average: {mean_load:,.0f} MW",
        annotation_position="top right"
    )

    fig.update_layout(
        title='California System Load Profile',
        xaxis_title='Time',
        yaxis_title='Load (MW)',
        height=450,
        hovermode='x unified',
        template='plotly_white',
        showlegend=False,
        margin=dict(l=60, r=40, t=80, b=60)
    )

    return fig
