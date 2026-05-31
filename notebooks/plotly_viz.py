"""
Interactive Plotly visualizations for CAISO OASIS data.
Dark command-center theme — matches portfolio aesthetic.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

FUEL_COLORS = {
    'Solar':       '#fbbf24',
    'Wind':        '#38bdf8',
    'Natural Gas': '#ef4444',
    'Nuclear':     '#818cf8',
    'Large Hydro': '#06b6d4',
    'Small Hydro': '#0891b2',
    'Batteries':   '#a855f7',
    'Imports':     '#6b7280',
    'Geothermal':  '#f97316',
    'Biomass':     '#84cc16',
    'Biogas':      '#65a30d',
    'Coal':        '#44403c',
    'Other':       '#374151',
}

_BG       = '#0a0a0a'
_SURFACE  = '#111111'
_BORDER   = 'rgba(255,255,255,0.07)'
_GRID     = 'rgba(255,255,255,0.05)'
_TEXT     = '#e5e7eb'
_MUTED    = '#6b7280'
_GREEN    = '#22c55e'
_BLUE     = '#38bdf8'
_AMBER    = '#f59e0b'

_BASE_LAYOUT = dict(
    font=dict(family="'Space Grotesk', system-ui, sans-serif", color=_TEXT, size=13),
    paper_bgcolor=_BG,
    plot_bgcolor=_SURFACE,
    hoverlabel=dict(
        bgcolor='#1a1a1a', bordercolor='#333333',
        font=dict(color=_TEXT, size=13, family="'Space Grotesk', system-ui, sans-serif"),
    ),
    hovermode='x unified',
)

_AXIS = dict(
    gridcolor=_GRID, gridwidth=1,
    linecolor=_BORDER,
    tickfont=dict(color=_MUTED, size=11, family="'JetBrains Mono', monospace"),
    title_font=dict(color=_MUTED, size=12),
    showgrid=True,
    zeroline=True, zerolinecolor='rgba(255,255,255,0.1)', zerolinewidth=1,
)

_LEGEND = dict(
    bgcolor='rgba(17,17,17,0.95)', bordercolor=_BORDER, borderwidth=1,
    font=dict(color=_TEXT, size=12),
)


def _apply_axes(fig, rows=1):
    for r in range(1, rows + 1):
        fig.update_xaxes(row=r, **_AXIS)
        fig.update_yaxes(row=r, **_AXIS)


def _dark_annotations(fig):
    for ann in fig.layout.annotations:
        ann.update(font=dict(size=13, color='#9ca3af'), x=0, xanchor='left')


def plot_lmp_components(lmp_df: pd.DataFrame) -> go.Figure:
    agg_cols = ['lmp_total', 'lmp_energy', 'lmp_congestion', 'lmp_loss']
    if 'lmp_ghg' in lmp_df.columns:
        agg_cols.append('lmp_ghg')

    df = (
        lmp_df.groupby('timestamp')[agg_cols]
        .mean().reset_index().sort_values('timestamp')
    )
    has_ghg = 'lmp_ghg' in df.columns and df['lmp_ghg'].abs().max() > 0.01

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.45, 0.55],
        subplot_titles=('Real-Time LMP · NP15 Hub Average', 'Component Breakdown'),
        vertical_spacing=0.14,
    )

    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['lmp_total'],
        name='Total LMP', fill='tozeroy', mode='lines',
        line=dict(color=_GREEN, width=2.5),
        fillcolor='rgba(34,197,94,0.1)',
        hovertemplate='<b>$%{y:.2f}/MWh</b><extra>Total LMP</extra>',
    ), row=1, col=1)

    components = [
        ('lmp_energy',     _BLUE,  'Energy'),
        ('lmp_congestion', _AMBER, 'Congestion'),
        ('lmp_loss',       _MUTED, 'Loss'),
    ]
    if has_ghg:
        components.append(('lmp_ghg', '#818cf8', 'GHG (Carbon)'))

    for col, color, label in components:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], y=df[col], name=label, mode='lines',
            line=dict(color=color, width=2),
            hovertemplate=f'<b>$%{{y:.2f}}/MWh</b><extra>{label}</extra>',
        ), row=2, col=1)

    fig.add_hline(y=0, line_dash='dot', line_color=_BORDER, line_width=1, row=2, col=1)

    _apply_axes(fig, rows=2)
    fig.update_yaxes(title_text='$/MWh', row=1, col=1)
    fig.update_yaxes(title_text='$/MWh', row=2, col=1)
    fig.update_xaxes(title_text='Time (US Pacific)', row=2, col=1)
    fig.update_layout(
        **_BASE_LAYOUT, height=580, showlegend=True,
        legend=dict(**_LEGEND, orientation='h', yanchor='bottom', y=1.03, xanchor='right', x=1),
        margin=dict(l=60, r=30, t=90, b=50),
    )
    _dark_annotations(fig)
    return fig


def plot_trading_hubs(lmp_df: pd.DataFrame) -> go.Figure:
    hub_info = {
        'TH_NP15_GEN-APND': {'label': 'NP15 (Northern CA)', 'color': _GREEN},
        'TH_SP15_GEN-APND': {'label': 'SP15 (Southern CA)', 'color': _BLUE},
        'TH_ZP26_GEN-APND': {'label': 'ZP26 (San Diego)',   'color': _AMBER},
    }

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.55, 0.45],
        subplot_titles=('Regional Hub Prices', 'Spread vs. Three-Hub Average'),
        vertical_spacing=0.14,
    )

    avg_lmp = lmp_df.groupby('timestamp')['lmp_total'].mean()

    for hub, info in hub_info.items():
        hub_data = lmp_df[lmp_df['location'] == hub].copy().sort_values('timestamp')
        if hub_data.empty:
            continue
        c = info['color']
        r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)

        fig.add_trace(go.Scatter(
            x=hub_data['timestamp'], y=hub_data['lmp_total'],
            name=info['label'], mode='lines',
            line=dict(color=c, width=2.5),
            hovertemplate=f'<b>$%{{y:.2f}}/MWh</b><extra>{info["label"]}</extra>',
        ), row=1, col=1)

        idx = hub_data.set_index('timestamp')
        spread = idx['lmp_total'] - avg_lmp
        fig.add_trace(go.Scatter(
            x=spread.index, y=spread.values,
            name=info['label'], mode='lines',
            line=dict(color=c, width=2), showlegend=False,
            fill='tozeroy', fillcolor=f'rgba({r},{g},{b},0.08)',
            hovertemplate=f'<b>%{{y:+.2f}} $/MWh</b><extra>{info["label"]}</extra>',
        ), row=2, col=1)

    fig.add_hline(y=0, line_dash='dot', line_color=_BORDER, line_width=1.5, row=2, col=1)
    _apply_axes(fig, rows=2)
    fig.update_yaxes(title_text='$/MWh', row=1, col=1)
    fig.update_yaxes(title_text='Spread ($/MWh)', row=2, col=1)
    fig.update_xaxes(title_text='Time (US Pacific)', row=2, col=1)
    fig.update_layout(
        **_BASE_LAYOUT, height=580, showlegend=True,
        legend=dict(**_LEGEND, orientation='h', yanchor='bottom', y=1.03, xanchor='right', x=1),
        margin=dict(l=60, r=30, t=90, b=50),
    )
    _dark_annotations(fig)
    return fig


def plot_fuel_mix(fuel_df: pd.DataFrame) -> go.Figure:
    df_wide = fuel_df.pivot(index='timestamp', columns='fuel_type', values='generation_mw')
    df_wide = df_wide.fillna(0).sort_index()

    positive = df_wide.clip(lower=0).drop(columns=['Batteries'], errors='ignore')
    batteries = df_wide.get('Batteries', pd.Series(dtype=float))

    col_order = (
        positive[[c for c in positive.columns if positive[c].sum() > 0]]
        .mean().sort_values(ascending=True).index.tolist()
    )

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.70, 0.30],
        subplot_titles=('California Generation Mix', 'Battery Storage Activity'),
        vertical_spacing=0.12,
    )

    for fuel in col_order:
        fig.add_trace(go.Scatter(
            x=positive.index, y=positive[fuel],
            name=fuel, mode='lines', line=dict(width=0),
            fillcolor=FUEL_COLORS.get(fuel, '#374151'),
            stackgroup='gen',
            hovertemplate=f'<b>%{{y:,.0f}} MW</b><extra>{fuel}</extra>',
        ), row=1, col=1)

    if not batteries.empty:
        charge    = batteries.clip(upper=0)
        discharge = batteries.clip(lower=0)
        fig.add_trace(go.Bar(
            x=discharge.index, y=discharge.values,
            name='Discharging', marker_color='rgba(168,85,247,0.75)',
            hovertemplate='<b>%{y:,.0f} MW</b><extra>Discharging</extra>',
        ), row=2, col=1)
        fig.add_trace(go.Bar(
            x=charge.index, y=charge.values,
            name='Charging', marker_color='rgba(56,189,248,0.7)',
            hovertemplate='<b>%{y:,.0f} MW</b><extra>Charging</extra>',
        ), row=2, col=1)

    fig.add_hline(y=0, line_dash='dot', line_color=_BORDER, line_width=1, row=2, col=1)
    _apply_axes(fig, rows=2)
    fig.update_xaxes(title_text='Time (US Pacific)', row=2, col=1)
    fig.update_yaxes(title_text='Generation (MW)', row=1, col=1)
    fig.update_yaxes(title_text='MW', row=2, col=1)
    fig.update_layout(
        **_BASE_LAYOUT, height=640, showlegend=True, barmode='relative',
        legend=dict(**_LEGEND, orientation='v', yanchor='top', y=1, xanchor='left', x=1.01, font=dict(size=11)),
        margin=dict(l=60, r=160, t=90, b=50),
    )
    _dark_annotations(fig)
    return fig


def plot_fuel_mix_pie(fuel_df: pd.DataFrame) -> go.Figure:
    avg   = fuel_df.groupby('fuel_type')['generation_mw'].mean()
    avg   = avg[avg > 50].sort_values(ascending=False)
    total = avg.sum()
    large = avg[avg / total * 100 >= 2.0]
    small = avg[avg / total * 100 < 2.0].sum()
    if small > 0:
        large = pd.concat([large, pd.Series({'Other': small})])

    colors = [FUEL_COLORS.get(f, '#374151') for f in large.index]

    fig = go.Figure(data=[go.Pie(
        labels=large.index, values=large.values, hole=0.52,
        marker=dict(colors=colors, line=dict(color='#111111', width=2)),
        textposition='outside', textinfo='label+percent',
        textfont=dict(size=11, color=_TEXT),
        hovertemplate='<b>%{label}</b><br>%{value:,.0f} MW avg<br>%{percent}<extra></extra>',
        pull=[0.04 if i == 0 else 0 for i in range(len(large))],
    )])

    fig.update_layout(
        **{**_BASE_LAYOUT, 'hovermode': False},
        height=460, showlegend=False,
        margin=dict(l=60, r=60, t=60, b=60),
        annotations=[dict(
            text=f"<b>{total/1000:.1f} GW</b><br>avg total",
            x=0.5, y=0.5, font=dict(size=15, color=_TEXT),
            showarrow=False,
        )],
    )
    return fig


def plot_load_profile(load_df: pd.DataFrame) -> go.Figure:
    df = load_df.sort_values('timestamp').copy()
    df['load_mw'] = df['load_mw'].clip(lower=0)
    mean_load = df['load_mw'].mean()
    peak_load = df['load_mw'].max()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'], y=df['load_mw'],
        name='System Load', fill='tozeroy', mode='lines',
        line=dict(color=_BLUE, width=2.5),
        fillcolor='rgba(56,189,248,0.1)',
        hovertemplate='<b>%{y:,.0f} MW</b><extra>System Load</extra>',
    ))

    fig.add_hline(
        y=mean_load, line_dash='dash', line_color=_GREEN, line_width=1.5,
        annotation_text=f'Avg {mean_load:,.0f} MW',
        annotation_position='top right',
        annotation_font=dict(color=_GREEN, size=12),
    )

    peak_ts = df.loc[df['load_mw'].idxmax(), 'timestamp']
    fig.add_annotation(
        x=peak_ts, y=peak_load,
        text=f'Peak {peak_load:,.0f} MW',
        showarrow=True, arrowhead=2, arrowcolor='#ef4444',
        font=dict(color='#ef4444', size=12),
        bgcolor='rgba(17,17,17,0.9)', bordercolor='#ef4444', borderwidth=1,
        ax=0, ay=-40,
    )

    fig.update_xaxes(title_text='Time (US Pacific)', **_AXIS)
    fig.update_yaxes(title_text='Load (MW)', **_AXIS)
    fig.update_layout(
        **_BASE_LAYOUT, height=420, showlegend=False,
        margin=dict(l=70, r=40, t=60, b=60),
    )
    return fig


def plot_battery(fuel_df: pd.DataFrame) -> go.Figure:
    df_wide   = fuel_df.pivot(index='timestamp', columns='fuel_type', values='generation_mw').fillna(0)
    batteries = df_wide.get('Batteries', pd.Series(dtype=float))

    if batteries.empty or batteries.isna().all() or batteries.abs().max() < 1:
        fig = go.Figure()
        fig.add_annotation(
            text='No battery storage data in this window',
            x=0.5, y=0.5, xref='paper', yref='paper',
            showarrow=False, font=dict(color=_MUTED, size=14),
        )
        fig.update_layout(**_BASE_LAYOUT, height=400, margin=dict(l=40, r=40, t=40, b=40))
        return fig

    charge    = batteries.clip(upper=0)
    discharge = batteries.clip(lower=0)

    # Estimated SOC via integration (5-min intervals = 1/12 hr)
    dt         = 1 / 12
    soc_raw    = (-batteries.fillna(0) * dt).cumsum()
    soc_range  = soc_raw.max() - soc_raw.min()
    soc        = ((soc_raw - soc_raw.min()) / soc_range * 100) if soc_range > 0 else soc_raw * 0 + 50

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.55, 0.45],
        subplot_titles=('Battery Charge / Discharge Power', 'Estimated State of Charge'),
        vertical_spacing=0.14,
    )

    fig.add_trace(go.Bar(
        x=discharge.index, y=discharge.values,
        name='Discharging', marker_color='rgba(168,85,247,0.8)',
        hovertemplate='<b>%{y:,.0f} MW</b><extra>Discharging</extra>',
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=charge.index, y=charge.values,
        name='Charging', marker_color='rgba(56,189,248,0.7)',
        hovertemplate='<b>%{y:,.0f} MW</b><extra>Charging</extra>',
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=soc.index, y=soc.values,
        name='SOC (estimated)', mode='lines',
        line=dict(color=_GREEN, width=2),
        fill='tozeroy', fillcolor='rgba(34,197,94,0.1)',
        hovertemplate='<b>%{y:.1f}%</b><extra>State of Charge (est.)</extra>',
    ), row=2, col=1)

    fig.add_hline(y=0, line_dash='dot', line_color=_BORDER, line_width=1, row=1, col=1)
    _apply_axes(fig, rows=2)
    fig.update_yaxes(title_text='Power (MW)', row=1, col=1)
    fig.update_yaxes(title_text='SOC (%)', row=2, col=1, range=[0, 100])
    fig.update_xaxes(title_text='Time (US Pacific)', row=2, col=1)
    fig.update_layout(
        **_BASE_LAYOUT, height=560, showlegend=True, barmode='relative',
        legend=dict(**_LEGEND, orientation='h', yanchor='bottom', y=1.03, xanchor='right', x=1),
        margin=dict(l=60, r=30, t=90, b=50),
    )
    _dark_annotations(fig)
    return fig
