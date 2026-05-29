"""
Interactive Plotly visualizations for CAISO OASIS data.

Creates interactive web-friendly plots that render directly in the browser.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# CAISO-aligned color palette
FUEL_COLORS = {
    'Solar':       '#F5A623',
    'Wind':        '#4FC3F7',
    'Natural Gas': '#EF5350',
    'Nuclear':     '#7E57C2',
    'Large Hydro': '#26C6DA',
    'Small Hydro': '#00ACC1',
    'Batteries':   '#AB47BC',
    'Imports':     '#78909C',
    'Geothermal':  '#FF7043',
    'Biomass':     '#66BB6A',
    'Biogas':      '#9CCC65',
    'Coal':        '#546E7A',
    'Other':       '#BDBDBD',
}

CHART_THEME = {
    'bg':           '#FFFFFF',
    'paper_bg':     '#F8FAFC',
    'grid':         '#E2E8F0',
    'text':         '#1E293B',
    'subtext':      '#64748B',
    'accent':       '#6366F1',
    'accent2':      '#8B5CF6',
    'positive':     '#10B981',
    'negative':     '#EF4444',
    'neutral':      '#F59E0B',
}

_BASE_LAYOUT = dict(
    font=dict(family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
              color=CHART_THEME['text'], size=13),
    paper_bgcolor=CHART_THEME['paper_bg'],
    plot_bgcolor=CHART_THEME['bg'],
    hoverlabel=dict(
        bgcolor='#1E293B',
        bordercolor='#334155',
        font=dict(color='white', size=13),
    ),
    hovermode='x unified',
)

_AXIS_STYLE = dict(
    gridcolor=CHART_THEME['grid'],
    gridwidth=1,
    linecolor='#CBD5E1',
    tickfont=dict(color=CHART_THEME['subtext'], size=12),
    title_font=dict(color=CHART_THEME['subtext'], size=12),
    showgrid=True,
    zeroline=False,
)


def _apply_axis_style(fig, rows=1):
    """Apply consistent axis styling to all subplots."""
    for r in range(1, rows + 1):
        fig.update_xaxes(row=r, **_AXIS_STYLE)
        fig.update_yaxes(row=r, **_AXIS_STYLE)


def plot_lmp_components(lmp_df: pd.DataFrame) -> go.Figure:
    """LMP over time with energy / congestion / loss breakdown."""
    df = (
        lmp_df.groupby('timestamp')[['lmp_total', 'lmp_energy', 'lmp_congestion', 'lmp_loss']]
        .mean()
        .reset_index()
        .sort_values('timestamp')
    )

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.45, 0.55],
        subplot_titles=('Real-Time LMP — System Average', 'Price Component Breakdown'),
        vertical_spacing=0.14,
    )

    # ── Row 1: total LMP gradient fill ──────────────────────────────────────
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'], y=df['lmp_total'],
            name='Total LMP',
            fill='tozeroy',
            mode='lines',
            line=dict(color=CHART_THEME['accent'], width=2.5),
            fillcolor='rgba(99,102,241,0.15)',
            hovertemplate='<b>%{y:.2f} $/MWh</b><extra>Total LMP</extra>',
        ),
        row=1, col=1,
    )

    # ── Row 2: stacked components ────────────────────────────────────────────
    component_colors = {
        'lmp_energy':     ('#10B981', 'rgba(16,185,129,0.80)', 'Energy'),
        'lmp_congestion': ('#F59E0B', 'rgba(245,158,11,0.80)', 'Congestion'),
        'lmp_loss':       ('#EF4444', 'rgba(239,68,68,0.80)',  'Loss'),
    }

    first = True
    for col, (line_color, fill_color, label) in component_colors.items():
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'], y=df[col],
                name=label,
                mode='lines',
                line=dict(color=line_color, width=0),
                fillcolor=fill_color,
                fill='tozeroy' if first else 'tonexty',
                stackgroup='components',
                hovertemplate=f'<b>%{{y:.2f}} $/MWh</b><extra>{label}</extra>',
            ),
            row=2, col=1,
        )
        first = False

    _apply_axis_style(fig, rows=2)
    fig.update_yaxes(title_text='$/MWh', row=1, col=1)
    fig.update_yaxes(title_text='$/MWh', row=2, col=1)
    fig.update_xaxes(title_text='', row=1, col=1)
    fig.update_xaxes(title_text='Time (US Pacific PT)', row=2, col=1)

    fig.update_layout(
        **_BASE_LAYOUT,
        height=580,
        showlegend=True,
        legend=dict(
            orientation='h', yanchor='bottom', y=1.03, xanchor='right', x=1,
            bgcolor='rgba(255,255,255,0.9)', bordercolor='#E2E8F0', borderwidth=1,
        ),
        margin=dict(l=60, r=30, t=90, b=50),
    )

    for ann in fig.layout.annotations:
        ann.update(font=dict(size=14, color=CHART_THEME['text']), x=0, xanchor='left')

    return fig


def plot_trading_hubs(lmp_df: pd.DataFrame) -> go.Figure:
    """Regional LMP comparison — NP15 / SP15 / ZP26."""
    hub_info = {
        'TH_NP15_GEN-APND': {'label': 'NP15 — Northern CA', 'color': '#6366F1'},
        'TH_SP15_GEN-APND': {'label': 'SP15 — Southern CA', 'color': '#EF4444'},
        'TH_ZP26_GEN-APND': {'label': 'ZP26 — San Diego',   'color': '#F59E0B'},
    }

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.55, 0.45],
        subplot_titles=('Regional Price Comparison', 'Spread vs. System Average'),
        vertical_spacing=0.14,
    )

    avg_lmp = lmp_df.groupby('timestamp')['lmp_total'].mean()

    for hub, info in hub_info.items():
        hub_data = lmp_df[lmp_df['location'] == hub].copy().sort_values('timestamp')
        if hub_data.empty:
            continue

        # Row 1 — actual prices
        fig.add_trace(
            go.Scatter(
                x=hub_data['timestamp'], y=hub_data['lmp_total'],
                name=info['label'],
                mode='lines',
                line=dict(color=info['color'], width=2.5),
                hovertemplate='<b>%{y:.2f} $/MWh</b><extra>' + info['label'] + '</extra>',
            ),
            row=1, col=1,
        )

        # Row 2 — spread
        idx = hub_data.set_index('timestamp')
        spread = idx['lmp_total'] - avg_lmp
        fig.add_trace(
            go.Scatter(
                x=spread.index, y=spread.values,
                name=info['label'],
                mode='lines',
                line=dict(color=info['color'], width=2),
                showlegend=False,
                fill='tozeroy',
                fillcolor=info['color'].replace('#', 'rgba(').replace(')', ',0.10)') if False else
                    f"rgba({int(info['color'][1:3],16)},{int(info['color'][3:5],16)},{int(info['color'][5:7],16)},0.10)",
                hovertemplate='<b>%{y:+.2f} $/MWh</b><extra>' + info['label'] + '</extra>',
            ),
            row=2, col=1,
        )

    fig.add_hline(y=0, line_dash='dot', line_color='#94A3B8', line_width=1.5, row=2, col=1)

    _apply_axis_style(fig, rows=2)
    fig.update_yaxes(title_text='$/MWh', row=1, col=1)
    fig.update_yaxes(title_text='Spread ($/MWh)', row=2, col=1)
    fig.update_xaxes(title_text='Time (US Pacific PT)', row=2, col=1)

    fig.update_layout(
        **_BASE_LAYOUT,
        height=580,
        showlegend=True,
        legend=dict(
            orientation='h', yanchor='bottom', y=1.03, xanchor='right', x=1,
            bgcolor='rgba(255,255,255,0.9)', bordercolor='#E2E8F0', borderwidth=1,
        ),
        margin=dict(l=60, r=30, t=90, b=50),
    )

    for ann in fig.layout.annotations:
        ann.update(font=dict(size=14, color=CHART_THEME['text']), x=0, xanchor='left')

    return fig


def plot_fuel_mix(fuel_df: pd.DataFrame) -> go.Figure:
    """Stacked area chart of California generation by fuel type."""
    df_wide = fuel_df.pivot(index='timestamp', columns='fuel_type', values='generation_mw')
    df_wide = df_wide.fillna(0).sort_index()

    # Separate batteries (can go negative) from the rest
    positive = df_wide.clip(lower=0).drop(columns=['Batteries'], errors='ignore')
    batteries = df_wide.get('Batteries', pd.Series(dtype=float))

    # Order by average contribution (smallest on bottom, largest on top)
    col_order = (
        positive[[c for c in positive.columns if positive[c].sum() > 0]]
        .mean().sort_values(ascending=True).index.tolist()
    )

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.70, 0.30],
        subplot_titles=('California Generation Mix', 'Battery Storage Activity'),
        vertical_spacing=0.12,
    )

    for fuel in col_order:
        fig.add_trace(
            go.Scatter(
                x=positive.index, y=positive[fuel],
                name=fuel,
                mode='lines',
                line=dict(width=0),
                fillcolor=FUEL_COLORS.get(fuel, '#BDBDBD'),
                stackgroup='gen',
                hovertemplate='<b>%{y:,.0f} MW</b><extra>' + fuel + '</extra>',
            ),
            row=1, col=1,
        )

    # Battery charge / discharge
    if not batteries.empty:
        charge = batteries.clip(upper=0)
        discharge = batteries.clip(lower=0)

        fig.add_trace(
            go.Bar(
                x=discharge.index, y=discharge.values,
                name='Discharging', marker_color='rgba(171,71,188,0.75)',
                showlegend=True,
                hovertemplate='<b>%{y:,.0f} MW</b><extra>Discharging</extra>',
            ),
            row=2, col=1,
        )
        fig.add_trace(
            go.Bar(
                x=charge.index, y=charge.values,
                name='Charging', marker_color='rgba(99,102,241,0.75)',
                showlegend=True,
                hovertemplate='<b>%{y:,.0f} MW</b><extra>Charging</extra>',
            ),
            row=2, col=1,
        )

    fig.add_hline(y=0, line_dash='dot', line_color='#94A3B8', line_width=1, row=2, col=1)

    _apply_axis_style(fig, rows=2)
    fig.update_xaxes(title_text='Time (US Pacific PT)', row=2, col=1)
    fig.update_yaxes(title_text='Generation (MW)', row=1, col=1)
    fig.update_yaxes(title_text='MW', row=2, col=1)

    fig.update_layout(
        **_BASE_LAYOUT,
        height=640,
        showlegend=True,
        barmode='relative',
        legend=dict(
            orientation='v', yanchor='top', y=1, xanchor='left', x=1.01,
            bgcolor='rgba(255,255,255,0.9)', bordercolor='#E2E8F0', borderwidth=1,
            font=dict(size=11),
        ),
        margin=dict(l=60, r=160, t=90, b=50),
    )

    for ann in fig.layout.annotations:
        ann.update(font=dict(size=14, color=CHART_THEME['text']), x=0, xanchor='left')

    return fig


def plot_fuel_mix_pie(fuel_df: pd.DataFrame) -> go.Figure:
    """Donut chart of average generation mix over the window."""
    avg = fuel_df.groupby('fuel_type')['generation_mw'].mean()
    avg = avg[avg > 50].sort_values(ascending=False)

    total = avg.sum()
    large = avg[avg / total * 100 >= 2.0]
    small_sum = avg[avg / total * 100 < 2.0].sum()
    if small_sum > 0:
        large = pd.concat([large, pd.Series({'Other': small_sum})])

    colors = [FUEL_COLORS.get(f, '#BDBDBD') for f in large.index]

    fig = go.Figure(data=[go.Pie(
        labels=large.index,
        values=large.values,
        hole=0.52,
        marker=dict(colors=colors, line=dict(color='#FFFFFF', width=2)),
        textposition='outside',
        textinfo='label+percent',
        textfont=dict(size=12),
        hovertemplate='<b>%{label}</b><br>%{value:,.0f} MW avg<br>%{percent}<extra></extra>',
        pull=[0.04 if i == 0 else 0 for i in range(len(large))],
    )])

    pie_layout = {**_BASE_LAYOUT, 'hovermode': False}
    fig.update_layout(
        **pie_layout,
        height=480,
        showlegend=False,
        margin=dict(l=60, r=60, t=70, b=60),
        annotations=[dict(
            text=f"<b>{total/1000:.1f} GW</b><br><span style='font-size:11px'>avg total</span>",
            x=0.5, y=0.5, font=dict(size=16, color=CHART_THEME['text']),
            showarrow=False,
        )],
    )

    return fig


def plot_load_profile(load_df: pd.DataFrame) -> go.Figure:
    """System load profile with peak/average annotations."""
    df = load_df.sort_values('timestamp').copy()
    df['load_mw'] = df['load_mw'].clip(lower=0)

    mean_load = df['load_mw'].mean()
    peak_load = df['load_mw'].max()

    fig = go.Figure()

    # Gradient fill area
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'], y=df['load_mw'],
            name='System Load',
            fill='tozeroy',
            mode='lines',
            line=dict(color='#6366F1', width=2.5),
            fillcolor='rgba(99,102,241,0.12)',
            hovertemplate='<b>%{y:,.0f} MW</b><extra>System Load</extra>',
        )
    )

    # Average reference line
    fig.add_hline(
        y=mean_load,
        line_dash='dash', line_color='#10B981', line_width=1.5,
        annotation_text=f'Avg: {mean_load:,.0f} MW',
        annotation_position='top right',
        annotation_font=dict(color='#10B981', size=12),
    )

    # Peak annotation
    peak_ts = df.loc[df['load_mw'].idxmax(), 'timestamp']
    fig.add_annotation(
        x=peak_ts, y=peak_load,
        text=f'Peak: {peak_load:,.0f} MW',
        showarrow=True,
        arrowhead=2,
        arrowcolor='#EF4444',
        font=dict(color='#EF4444', size=12),
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='#EF4444',
        borderwidth=1,
        ax=0, ay=-40,
    )

    fig.update_xaxes(title_text='Time (US Pacific PT)', **_AXIS_STYLE)
    fig.update_yaxes(title_text='Load (MW)', **_AXIS_STYLE)

    fig.update_layout(
        **_BASE_LAYOUT,
        height=420,
        showlegend=False,
        margin=dict(l=70, r=40, t=60, b=60),
    )

    return fig
