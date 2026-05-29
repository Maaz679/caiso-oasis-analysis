# CAISO OASIS Market Dashboard

A live electricity market dashboard that pulls real-time data from the California ISO (CAISO) OASIS API and presents it through interactive visualizations. Built to explore how wholesale power markets work and to apply economic models from power systems theory to real grid data.

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Flask](https://img.shields.io/badge/Flask-3.x-lightgrey)
![Plotly](https://img.shields.io/badge/Plotly-5.x-3F4F75)
![Data](https://img.shields.io/badge/Data-CAISO%20OASIS%20API-orange)

---

## What It Does

The dashboard pulls five-minute interval data directly from the CAISO OASIS API and renders it as interactive Plotly charts. All timestamps are in US Pacific Time (PT), matching CAISO's own reporting convention.

**Charts rendered on each load:**

| Chart | What it shows |
|---|---|
| LMP Components | Real-time system-average price broken into energy, congestion, and loss |
| Regional Price Comparison | NP15 / SP15 / ZP26 hub prices and their spread vs. the system average |
| California Generation Mix | Stacked fuel output over time, plus battery charge/discharge activity |
| Generation Portfolio | 12-hour average generation share by fuel as a donut chart |
| System Load Profile | Statewide electricity demand with peak annotation and average reference line |

Five summary stat cards at the top of the page (average LMP, system load, peak LMP, top fuel source, renewable share) load from a separate fast endpoint so they appear before the heavier chart data arrives.

---

## Data Sources

All data comes from the [CAISO OASIS API](http://oasis.caiso.com), accessed through the [gridstatus](https://github.com/kmax12/gridstatus) library.

| Data type | OASIS query | Update frequency |
|---|---|---|
| Real-time LMP | `PRC_INTVL_LMP` (RTM) | 5-minute intervals |
| Fuel mix | CAISO current outlook CSV | 5-minute intervals |
| System load | CAISO current outlook CSV | 5-minute intervals |
| Trading hub LMP | `PRC_INTVL_LMP` filtered to NP15/SP15/ZP26 | 5-minute intervals |

The dashboard fetches the trailing 12 hours on each load and caches nothing, so every page refresh reflects the current market state.

---

## Project Structure

```
caiso-oasis-analysis/
├── app.py                  Flask app and API routes
├── templates/
│   └── dashboard.html      Single-page dashboard with embedded JS
├── src/
│   ├── oasis/
│   │   └── client.py       CAISOClient - wraps gridstatus with fallback to raw OASIS API
│   ├── economics/
│   │   ├── dispatch.py     Economic dispatch (lambda iteration, quadratic cost curves)
│   │   ├── lmp.py          LMP decomposition and nodal analysis
│   │   └── merit_order.py  Merit order stack construction and market clearing
│   └── viz/
│       └── plots.py        Static matplotlib plots (used in notebooks)
├── notebooks/
│   ├── plotly_viz.py       Interactive Plotly chart functions used by the Flask app
│   ├── visualize_data.py   Exploratory matplotlib charts
│   └── example_usage.py    Example scripts showing how to use the API client
├── data/
│   ├── raw/                Downloaded OASIS data (git-ignored)
│   └── processed/          Cleaned datasets (git-ignored)
├── Procfile                Gunicorn start command for Render/Heroku
├── render.yaml             Render Blueprint for one-click deployment
├── runtime.txt             Python version pin
└── requirements.txt        Python dependencies
```

---

## Economics Models

The `src/economics/` modules implement theory from Kirschen and Strbac, *Fundamentals of Power System Economics* (3rd ed.). They are standalone Python classes that can be used independently of the dashboard.

### Economic Dispatch (`dispatch.py`)

Solves the classical economic dispatch problem: given a set of generators with quadratic cost curves and a total load to serve, find the output level for each generator that minimizes total generation cost.

- Generator cost model: `C(P) = a + b*P + c*P^2`
- Solves for the system lambda (marginal cost) using the equal incremental cost principle
- Enforces per-generator minimum and maximum output limits
- Returns optimal dispatch levels and the system clearing price

### LMP Decomposition (`lmp.py`)

Analyzes locational marginal prices at the node level, following the standard decomposition:

```
LMP = Energy component + Congestion component + Loss component
```

- `LMPAnalyzer.decompose_lmp()` - breaks a total LMP into its three additive parts
- `calculate_congestion_rent()` - computes total payment flowing through transmission constraints
- `identify_congested_nodes()` - flags nodes where the congestion component exceeds a threshold
- `compare_market_designs()` - computes the welfare difference between nodal and zonal pricing
- `analyze_caiso_lmp_data()` - convenience wrapper that runs a full analysis on a DataFrame returned by `CAISOClient.get_lmp()`

### Merit Order and Market Clearing (`merit_order.py`)

Constructs the supply stack from generator bids and finds the market clearing price where supply meets demand.

- Builds an ordered supply curve from generator bids (cheapest dispatched first)
- Accepts both price-sensitive and must-run (price-insensitive) generators
- Computes producer surplus, consumer surplus, and total welfare
- Supports both perfectly inelastic demand (fixed load) and downward-sloping demand curves

---

## Quick Start

```bash
git clone https://github.com/Maaz679/caiso-oasis-analysis.git
cd caiso-oasis-analysis
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The dashboard fetches live data on load and auto-refreshes every 10 minutes.

If you also want to run the notebooks or exploratory scripts in `notebooks/`, install the dev dependencies instead:

```bash
pip install -r requirements-dev.txt
```

---

## API Reference

The Flask app exposes four JSON endpoints.

### `GET /api/plots`

Fetches the trailing 12 hours of CAISO data and returns all five charts as Plotly figure JSON. The response can be passed directly to `Plotly.newPlot()`.

```json
{
  "status": "success",
  "timestamp": "2026-05-28T18:00:00",
  "plots": {
    "lmp_components":  { "data": [...], "layout": {...} },
    "trading_hubs":    { "data": [...], "layout": {...} },
    "fuel_mix_stack":  { "data": [...], "layout": {...} },
    "fuel_mix_pie":    { "data": [...], "layout": {...} },
    "load_profile":    { "data": [...], "layout": {...} }
  }
}
```

### `GET /api/stats`

Returns summary statistics for the trailing 12 hours. Faster than `/api/plots` because it skips chart generation.

```json
{
  "status": "success",
  "timestamp": "2026-05-28T18:00:00",
  "lmp":  { "average": 13.4, "max": 45.4, "min": -29.0 },
  "load": { "average": 21539, "max": 23757 },
  "top_fuels": {
    "Solar": 9002, "Imports": 3421, "Wind": 2726,
    "Large Hydro": 2546, "Nuclear": 2322
  }
}
```

### `GET /api/fetch-data`

Triggers a data fetch and returns record counts. Useful for confirming API connectivity.

```json
{
  "status": "success",
  "timestamp": "2026-05-28T18:00:00",
  "records": { "lmp": 14400, "fuel_mix": 1872, "load": 144 }
}
```

### `GET /health`

Health check. Returns 200 with `{"status": "healthy"}` when the app is running.

---

## Using the API Client Directly

The `CAISOClient` class can be used outside the dashboard to pull CAISO data into any Python workflow.

```python
from datetime import datetime, timedelta
from src.oasis import CAISOClient

end = datetime.now()
start = end - timedelta(hours=24)

with CAISOClient() as client:
    lmp      = client.get_lmp(start, end, market="RTM")
    fuel_mix = client.get_fuel_mix(start, end)
    load     = client.get_load(start, end)
    hubs     = client.get_trading_hub_lmp(start, end, market="RTM")
```

Each method returns a pandas DataFrame with standardized column names. `get_lmp()` accepts `market="DAM"` for day-ahead prices. `get_trading_hub_lmp()` filters to the three major CAISO hubs (NP15, SP15, ZP26) automatically.

---

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for full instructions. The short version for Render:

1. Fork or clone the repo to your GitHub account.
2. On [render.com](https://render.com), click **New > Blueprint** and connect the repository. Render reads `render.yaml` and configures everything automatically.
3. Click **Apply**. The service will build and be live within a few minutes.

The `render.yaml` in this repo pins the Python version, sets the build and start commands, and configures a free-tier web service.

---

## Requirements

Python 3.12 is recommended (pinned in `runtime.txt` for Render).

`requirements.txt` contains only what the Flask dashboard needs:

```
gridstatus==0.36.0
pandas>=2.0
numpy>=1.24
plotly>=5.0
flask>=3.0
gunicorn>=21.0
requests>=2.28
```

`requirements-dev.txt` extends that with notebook dependencies (`matplotlib`, `scipy`, `jupyter`, `python-dotenv`).
