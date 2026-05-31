"""
CAISO OASIS API Client

This module provides an interface to pull data from CAISO's OASIS API using
the gridstatus library with fallback to raw requests for unsupported endpoints.

Data sources:
- LMP (Locational Marginal Prices) by node
- Fuel mix (generation by fuel type)
- System load (demand)
"""

import io
import logging
import zipfile
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
import requests
from gridstatus import CAISO as GridStatusCAISO

logger = logging.getLogger(__name__)


class CAISOClient:
    """
    Client for accessing CAISO OASIS data.

    Uses gridstatus library as primary interface with fallback to raw
    OASIS API requests for additional data or when gridstatus fails.
    """

    OASIS_BASE_URL = "http://oasis.caiso.com/oasisapi/SingleZip"

    @staticmethod
    def _parse_oasis_response(content: bytes) -> pd.DataFrame:
        """Parse CAISO OASIS response — handles ZIP (resultformat=6) and plain CSV."""
        if content[:2] == b'PK':
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                csv_name = next((f for f in zf.namelist() if f.endswith('.csv')), None)
                if not csv_name:
                    raise ValueError("No CSV found in CAISO ZIP response")
                with zf.open(csv_name) as f:
                    return pd.read_csv(f, encoding='utf-8', errors='replace')
        return pd.read_csv(io.BytesIO(content), encoding='utf-8', errors='replace')

    def __init__(self, use_cache: bool = True):
        """
        Initialize the CAISO client.

        Args:
            use_cache: Whether to use gridstatus caching
        """
        self.gridstatus_client = GridStatusCAISO()
        self.use_cache = use_cache
        self.session = requests.Session()

    def get_lmp(
        self,
        start: datetime,
        end: datetime,
        market: str = "RTM",
        locations: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Get Locational Marginal Prices (LMP) data.

        Args:
            start: Start datetime
            end: End datetime
            market: Market type - "RTM" (real-time) or "DAM" (day-ahead)
            locations: List of node names. If None, returns all nodes.

        Returns:
            DataFrame with columns: timestamp, location, lmp_total, lmp_energy,
                                   lmp_congestion, lmp_loss
        """
        try:
            logger.info(f"Fetching {market} LMP data from {start} to {end}")

            # Try gridstatus first
            if market.upper() == "RTM":
                market_type = "REAL_TIME_5_MIN"
            elif market.upper() == "DAM":
                market_type = "DAY_AHEAD_HOURLY"
            else:
                raise ValueError(f"Unknown market type: {market}")

            df = self.gridstatus_client.get_lmp(
                date=start,
                end=end,
                market=market_type,
            )

            # Filter by locations if specified
            if locations is not None:
                df = df[df['Location'].isin(locations)]

            # Standardize column names
            df = df.rename(columns={
                'Time': 'timestamp',
                'Location': 'location',
                'LMP': 'lmp_total',
                'Energy': 'lmp_energy',
                'Congestion': 'lmp_congestion',
                'Loss': 'lmp_loss',
                'GHG': 'lmp_ghg',
            })

            logger.info(f"Retrieved {len(df)} LMP records")
            return df

        except Exception as e:
            logger.warning(f"gridstatus failed for LMP: {e}. Falling back to raw API")
            return self._get_lmp_raw(start, end, market, locations)

    def _get_lmp_raw(
        self,
        start: datetime,
        end: datetime,
        market: str = "RTM",
        locations: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        Fallback method to get LMP data directly from OASIS API.

        Uses the PRC_LMP query type from OASIS.
        """
        # Map market to OASIS market type
        market_map = {
            "RTM": "RTM",  # Real-Time Market
            "DAM": "DAM",  # Day-Ahead Market
        }

        params = {
            "queryname": "PRC_LMP",
            "startdatetime": start.strftime("%Y%m%dT%H:%M-0000"),
            "enddatetime": end.strftime("%Y%m%dT%H:%M-0000"),
            "market_run_id": market_map.get(market.upper(), "RTM"),
            "version": "1",
            "resultformat": "6",  # CSV format
        }

        if locations:
            params["node"] = ",".join(locations)

        response = self.session.get(self.OASIS_BASE_URL, params=params, timeout=60)
        response.raise_for_status()

        df = self._parse_oasis_response(response.content)

        df = df.rename(columns={
            'INTERVALSTARTTIME_GMT': 'timestamp',
            'NODE': 'location',
            'LMP_PRC': 'lmp_total',
            'LMP_ENE_PRC': 'lmp_energy',
            'LMP_CONG_PRC': 'lmp_congestion',
            'LMP_LOSS_PRC': 'lmp_loss',
        })

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df[['timestamp', 'location', 'lmp_total', 'lmp_energy',
                   'lmp_congestion', 'lmp_loss']]

    def get_fuel_mix(
        self,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Get fuel mix (generation by fuel type).

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            DataFrame with columns: timestamp, fuel_type, generation_mw
        """
        try:
            logger.info(f"Fetching fuel mix data from {start} to {end}")

            df = self.gridstatus_client.get_fuel_mix(
                date=start,
                end=end,
            )

            # Standardize column names
            df = df.rename(columns={
                'Time': 'timestamp',
            })

            # Melt fuel columns into long format
            fuel_columns = [col for col in df.columns if col not in ['timestamp', 'Interval Start', 'Interval End']]
            df = df.melt(
                id_vars=['timestamp'],
                value_vars=fuel_columns,
                var_name='fuel_type',
                value_name='generation_mw'
            )

            logger.info(f"Retrieved {len(df)} fuel mix records")
            return df

        except Exception as e:
            logger.warning(f"gridstatus failed for fuel mix: {e}. Falling back to raw API")
            return self._get_fuel_mix_raw(start, end)

    def _get_fuel_mix_raw(
        self,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """
        Fallback method to get fuel mix data directly from OASIS API.

        Uses the SLD_REN_FCST query type from OASIS.
        """
        params = {
            "queryname": "ENE_SLRS",  # Energy - Supply, Load, and Renewables Summary
            "startdatetime": start.strftime("%Y%m%dT%H:%M-0000"),
            "enddatetime": end.strftime("%Y%m%dT%H:%M-0000"),
            "version": "1",
            "resultformat": "6",  # CSV format
        }

        response = self.session.get(self.OASIS_BASE_URL, params=params, timeout=60)
        response.raise_for_status()

        df = self._parse_oasis_response(response.content)

        df = df.rename(columns={
            'INTERVALSTARTTIME_GMT': 'timestamp',
            'FUEL_TYPE': 'fuel_type',
            'VALUE': 'generation_mw',
        })

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df[['timestamp', 'fuel_type', 'generation_mw']]

    def get_load(
        self,
        start: datetime,
        end: datetime,
        forecast: bool = False,
    ) -> pd.DataFrame:
        """
        Get system load (demand) data.

        Args:
            start: Start datetime
            end: End datetime
            forecast: If True, get forecasted load. If False, get actual load.

        Returns:
            DataFrame with columns: timestamp, load_mw, [forecast_type]
        """
        try:
            logger.info(f"Fetching {'forecast' if forecast else 'actual'} load data from {start} to {end}")

            df = self.gridstatus_client.get_load(
                date=start,
                end=end,
            )

            # Standardize column names
            df = df.rename(columns={
                'Time': 'timestamp',
                'Load': 'load_mw',
            })

            # Filter to relevant columns
            result_columns = ['timestamp', 'load_mw']
            if 'Load Forecast' in df.columns:
                df = df.rename(columns={'Load Forecast': 'load_forecast_mw'})
                result_columns.append('load_forecast_mw')

            logger.info(f"Retrieved {len(df)} load records")
            return df[result_columns]

        except Exception as e:
            logger.warning(f"gridstatus failed for load: {e}. Falling back to raw API")
            return self._get_load_raw(start, end, forecast)

    def _get_load_raw(
        self,
        start: datetime,
        end: datetime,
        forecast: bool = False,
    ) -> pd.DataFrame:
        """
        Fallback method to get load data directly from OASIS API.

        Uses the SLD_FCST (forecast) or SLD_REN_FCST (actual) query types.
        """
        queryname = "SLD_FCST" if forecast else "SLD_REN_FCST"

        params = {
            "queryname": queryname,
            "startdatetime": start.strftime("%Y%m%dT%H:%M-0000"),
            "enddatetime": end.strftime("%Y%m%dT%H:%M-0000"),
            "version": "1",
            "resultformat": "6",  # CSV format
        }

        response = self.session.get(self.OASIS_BASE_URL, params=params, timeout=60)
        response.raise_for_status()

        df = self._parse_oasis_response(response.content)

        df = df.rename(columns={
            'INTERVALSTARTTIME_GMT': 'timestamp',
            'LOAD': 'load_mw',
        })

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        return df[['timestamp', 'load_mw']]

    def get_market_summary(
        self,
        start: datetime,
        end: datetime,
    ) -> Dict[str, pd.DataFrame]:
        """
        Get a comprehensive market summary including LMP, fuel mix, and load.

        This is useful for economic analysis where you need all data aligned.

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            Dictionary with keys 'lmp', 'fuel_mix', 'load' containing respective DataFrames
        """
        logger.info(f"Fetching complete market summary from {start} to {end}")

        return {
            'lmp': self.get_lmp(start, end),
            'fuel_mix': self.get_fuel_mix(start, end),
            'load': self.get_load(start, end),
        }

    def get_trading_hub_lmp(
        self,
        start: datetime,
        end: datetime,
        market: str = "RTM",
    ) -> pd.DataFrame:
        """
        Get LMP for major CAISO trading hubs.

        Trading hubs are aggregated pricing nodes representing major load centers.

        Args:
            start: Start datetime
            end: End datetime
            market: Market type - "RTM" or "DAM"

        Returns:
            DataFrame with LMP data for major trading hubs
        """
        # Major CAISO trading hubs
        trading_hubs = [
            "TH_NP15_GEN-APND",  # NP15 (Northern California)
            "TH_SP15_GEN-APND",  # SP15 (Southern California)
            "TH_ZP26_GEN-APND",  # ZP26 (San Diego)
        ]

        return self.get_lmp(start, end, market, locations=trading_hubs)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.session.close()


def quick_fetch_latest(hours: int = 24) -> Dict[str, pd.DataFrame]:
    """
    Convenience function to quickly fetch the latest data.

    Args:
        hours: Number of hours of historical data to fetch

    Returns:
        Dictionary with 'lmp', 'fuel_mix', 'load' DataFrames
    """
    end = datetime.now()
    start = end - timedelta(hours=hours)

    with CAISOClient() as client:
        return client.get_market_summary(start, end)
