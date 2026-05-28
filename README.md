# CAISO OASIS Analysis

A Python project that pulls real-time and historical data from the CAISO OASIS API and analyzes it using economic models from Kirschen & Strbac, *Fundamentals of Power System Economics* (3rd ed.).

## Structure

- `src/oasis/` -- CAISO OASIS API client
- `src/economics/` -- Economic dispatch, LMP decomposition, merit order (Kirschen & Strbac Ch. 3-5)
- `src/viz/` -- Visualization utilities
- `data/processed/` -- Cleaned datasets
- `notebooks/` -- Exploration and demos

## Models Implemented

1. **Economic Dispatch** (Ch. 3) -- Equal incremental cost, lambda iteration
2. **LMP Decomposition** (Ch. 5) -- Energy + congestion + loss components
3. **Merit Order & Market Clearing** (Ch. 4) -- Supply stack vs. demand intersection
