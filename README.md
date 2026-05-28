# CAISO OASIS Analysis

A Python project that pulls real-time and historical data from the CAISO OASIS API and analyzes it using economic models from Kirschen & Strbac, *Fundamentals of Power System Economics* (3rd ed.).

## Live Dashboard

Run the Flask web application to see live CAISO market data with auto-refreshing visualizations:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the dashboard
python app.py
```

Then open http://localhost:5000 in your browser.

The dashboard automatically fetches fresh data from CAISO OASIS API and updates every 10 minutes.

For production deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## Project Structure

- `app.py` -- Flask web application for live dashboard
- `templates/` -- Dashboard HTML templates
- `src/oasis/` -- CAISO OASIS API client using gridstatus library
- `src/economics/` -- Economic dispatch, LMP decomposition, merit order (Kirschen & Strbac Ch. 3-5)
- `notebooks/` -- Analysis scripts and visualizations
- `data/` -- Downloaded datasets and generated plots

## Economic Models Implemented

1. **Economic Dispatch** (Ch. 3) -- Equal incremental cost, lambda iteration
2. **LMP Decomposition** (Ch. 5) -- Energy + congestion + loss components
3. **Merit Order & Market Clearing** (Ch. 4) -- Supply stack vs. demand intersection

## Dashboard Features

- Live LMP (Locational Marginal Price) components
- Trading hub price comparisons
- Generation mix and duck curve analysis
- Fuel portfolio breakdown
- System load profiles
- Auto-refresh every 10 minutes
- Manual refresh button
- Responsive design

## API Endpoints

- `GET /` -- Dashboard home page
- `GET /api/plots` -- Get all plots as base64 images
- `GET /api/stats` -- Get summary statistics
- `GET /api/fetch-data` -- Trigger data fetch
- `GET /health` -- Health check
