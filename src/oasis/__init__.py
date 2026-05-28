"""
CAISO OASIS API Client Module

Provides access to CAISO market data including LMP, fuel mix, and load.
"""

from .client import CAISOClient, quick_fetch_latest

__all__ = ['CAISOClient', 'quick_fetch_latest']
