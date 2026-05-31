# CAISO OASIS Dashboard — Development Progress

Last updated: 2026-05-31  
Live URL: https://caiso-oasis-analysis.onrender.com  
Repo: https://github.com/Maaz679/caiso-oasis-analysis  
Deployed via: Render.com (auto-deploys from `main` branch)

---

## Current State

A live Flask dashboard pulling real-time CAISO market data and rendering interactive Plotly charts. The UI is a dark command-center theme matching the portfolio site aesthetic.

### Architecture

```
app.py                    Flask app, 4 API routes, 5-min server-side cache
src/oasis/client.py       CAISOClient — wraps gridstatus, fallback to raw OASIS API
src/economics/
  dispatch.py             Economic dispatch (lambda iteration, quadratic cost curves)
  lmp.py                  LMP decomposition and nodal analysis
  merit_order.py          Merit order stack, market clearing, surplus calculation
notebooks/plotly_viz.py   All Plotly chart functions (dark theme)
templates/dashboard.html  Single-page dashboard — all UI lives here
```

### API Routes

| Route | Purpose |
|---|---|
| `GET /` | Render dashboard HTML |
| `GET /api/stats` | Fast summary stats (avg/max/min LMP, load, top fuels) |
| `GET /api/plots` | All 6 charts as Plotly JSON (slow — fetches live CAISO data) |
| `GET /api/fetch-data` | Force cache refresh |
| `GET /health` | Health check |

### Dashboard Sections

| Section | Status | Notes |
|---|---|---|
| Nav | Done | Sticky, with section tabs and Refresh button |
| Alert strip | Done | Dynamic badges based on live stats (Negative Prices, Duck Curve, BESS Charging, etc.) |
| Market Summary | Done | Auto-generated analyst bullets from `/api/stats` |
| Chart tabs | Done | LMP Components, Regional Hubs, Fuel Mix, System Load, Battery |
| Battery tab | Done | `plot_battery()` — charge/discharge bars + estimated SOC line |
| Project footer | Done | What this demonstrates + tech stack tags |

### Charts (all dark-themed)

| Chart | Function | Notes |
|---|---|---|
| LMP Components | `plot_lmp_components()` | Total LMP + energy/congestion/loss/GHG breakdown, 2-row subplot |
| Regional Hubs | `plot_trading_hubs()` | NP15/SP15/ZP26 prices + spread vs average |
| Fuel Mix | `plot_fuel_mix()` | Stacked generation + battery charge/discharge subplot |
| Generation Portfolio | `plot_fuel_mix_pie()` | 12h average donut chart |
| System Load | `plot_load_profile()` | Load curve with peak annotation and average reference |
| Battery Dispatch | `plot_battery()` | Charge/discharge power + estimated SOC |

---

## Bugs Fixed This Session

- **UTF-8 decode error on ZIP responses** (`src/oasis/client.py`): CAISO OASIS `resultformat=6` returns a ZIP archive. All three raw fallback methods were calling `pd.read_csv()` directly on the binary ZIP content, causing `UnicodeDecodeError` on bytes 10–12 (ZIP local file header). Fixed by adding `_parse_oasis_response()` helper that detects ZIP magic bytes (`PK`) and extracts the CSV before parsing.

---

## What's Next

### High priority
- [ ] **Loading performance** — `/api/plots` is slow (fetches 3 data series sequentially). Parallelize with `asyncio` or `concurrent.futures.ThreadPoolExecutor`
- [ ] **Date range picker** — let users select custom time windows (e.g., last 1h, 6h, 24h, 48h) instead of the hardcoded 6h window
- [ ] **Error state UX** — when CAISO API is down, show a "data unavailable" state with last-known values rather than a blank error box

### Medium priority
- [ ] **Merit order chart** — add a 6th tab showing the supply stack from `src/economics/merit_order.py`; this directly demonstrates the economic dispatch work
- [ ] **Nodal price map** — a California SVG map with NP15/SP15/ZP26 zones color-coded by current LMP spread; very visual and memorable for interviewers
- [ ] **Auto-refresh toggle** — the 10-minute refresh currently always runs; add a pause button and countdown timer
- [ ] **Export button** — let users download the current chart data as CSV

### Low priority / stretch
- [ ] Add WebSocket or SSE for true real-time LMP updates (currently polling)
- [ ] Port economic dispatch models to a standalone API endpoint so they're demonstrable independently of the CAISO data fetch
- [ ] Add a "curtailment detected" alert when LMP goes negative (already computed in analyst summary, just surface it more prominently)

---

## Known Limitations

- **gridstatus primary path**: The primary `gridstatus` client sometimes fails silently on certain CAISO endpoints; the fallback raw API path now handles ZIP correctly but column names may differ from gridstatus output. If you see `KeyError` on a column name, check the rename maps in `client.py`.
- **Render free tier cold starts**: The Render free plan spins down after inactivity. First load after idle can take 30–60s. Consider upgrading to a paid plan or adding a UptimeRobot ping to keep it warm.
- **Battery SOC is estimated**: `plot_battery()` integrates the power signal to approximate SOC — it's not metered data. The absolute value drifts; the relative pattern (charges midday, discharges evening) is accurate.
