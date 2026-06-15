"""
Flask web application for CAISO Market Analysis Dashboard

Serves live dashboard with real-time data from CAISO OASIS API.
Data is cached for 5 minutes so repeated page loads are fast.
"""

import threading
import time
import json
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify

from src.oasis import CAISOClient
from notebooks.plotly_viz import (
    plot_lmp_components,
    plot_trading_hubs,
    plot_fuel_mix,
    plot_fuel_mix_pie,
    plot_load_profile,
    plot_battery,
)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

FETCH_HOURS = 6
DATA_LAG_HOURS = 2  # CAISO OASIS doesn't publish RTM data until ~1-2h after the fact
CACHE_TTL = 300  # seconds

_cache = {}
_cache_lock = threading.Lock()


def _fetch_fresh():
    """Pull all four data series from CAISO. Called only when cache is cold."""
    end = datetime.now() - timedelta(hours=DATA_LAG_HOURS)
    start = end - timedelta(hours=FETCH_HOURS)
    with CAISOClient() as client:
        trading_hub_lmp = client.get_trading_hub_lmp(start, end, market="RTM")
        fuel_mix = client.get_fuel_mix(start, end)
        load = client.get_load(start, end)
    return {
        'trading_hub_lmp': trading_hub_lmp,
        'fuel_mix':        fuel_mix,
        'load':            load,
        'fetched_at':      datetime.now(),
    }


def get_data():
    """Return cached market data, refreshing if the cache is older than CACHE_TTL."""
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get('data')
        if entry and (now - entry['ts']) < CACHE_TTL:
            return entry['data']

    data = _fetch_fresh()

    with _cache_lock:
        _cache['data'] = {'data': data, 'ts': time.monotonic()}

    return data


@app.route('/')
def dashboard():
    last_updated = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    return render_template('dashboard.html', last_updated=last_updated)


@app.route('/api/plots')
def get_plots():
    """Generate and return all plots as Plotly JSON."""
    try:
        d = get_data()
        trading_hub_lmp = d['trading_hub_lmp']
        fuel_mix        = d['fuel_mix']
        load            = d['load']

        plots = {
            'lmp_components': json.loads(plot_lmp_components(trading_hub_lmp).to_json()),
            'trading_hubs':   json.loads(plot_trading_hubs(trading_hub_lmp).to_json()),
            'fuel_mix_stack': json.loads(plot_fuel_mix(fuel_mix).to_json()),
            'fuel_mix_pie':   json.loads(plot_fuel_mix_pie(fuel_mix).to_json()),
            'load_profile':   json.loads(plot_load_profile(load).to_json()),
            'battery':        json.loads(plot_battery(fuel_mix).to_json()),
        }

        return jsonify({
            'status':    'success',
            'timestamp': d['fetched_at'].isoformat(),
            'plots':     plots,
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/stats')
def get_stats():
    """Return summary statistics (served from the same cache as /api/plots)."""
    try:
        d = get_data()
        lmp      = d['trading_hub_lmp']
        fuel_mix = d['fuel_mix']
        load     = d['load']

        avg_lmp = lmp['lmp_total'].mean()
        max_lmp = lmp['lmp_total'].max()
        min_lmp = lmp['lmp_total'].min()

        avg_load = load['load_mw'].mean()
        max_load = load['load_mw'].max()

        fuel_avg  = fuel_mix.groupby('fuel_type')['generation_mw'].mean()
        top_fuels = fuel_avg.nlargest(5).to_dict()

        return jsonify({
            'status':    'success',
            'timestamp': d['fetched_at'].isoformat(),
            'lmp':  {'average': float(avg_lmp), 'max': float(max_lmp), 'min': float(min_lmp)},
            'load': {'average': float(avg_load), 'max': float(max_load)},
            'top_fuels': {k: float(v) for k, v in top_fuels.items()},
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/fetch-data')
def fetch_data():
    """Force a cache refresh and return record counts."""
    try:
        with _cache_lock:
            _cache.pop('data', None)

        d = get_data()
        return jsonify({
            'status':    'success',
            'timestamp': d['fetched_at'].isoformat(),
            'records': {
                'lmp':      len(d['trading_hub_lmp']),
                'fuel_mix': len(d['fuel_mix']),
                'load':     len(d['load']),
            },
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
