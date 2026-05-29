"""
Flask web application for CAISO Market Analysis Dashboard

Serves live dashboard with real-time data from CAISO OASIS API.
"""

from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import json

from src.oasis import CAISOClient
from notebooks.plotly_viz import (
    plot_lmp_components,
    plot_trading_hubs,
    plot_fuel_mix,
    plot_fuel_mix_pie,
    plot_load_profile
)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development




@app.route('/')
def dashboard():
    """Main dashboard page."""
    # Get current timestamp for display
    last_updated = datetime.now().strftime('%B %d, %Y at %I:%M %p')

    return render_template('dashboard.html', last_updated=last_updated)


@app.route('/api/fetch-data')
def fetch_data():
    """Fetch fresh data from CAISO API."""
    try:
        hours = 12  # Fetch last 12 hours
        end = datetime.now()
        start = end - timedelta(hours=hours)

        with CAISOClient() as client:
            lmp = client.get_lmp(start, end, market="RTM")
            trading_hub_lmp = client.get_trading_hub_lmp(start, end, market="RTM")
            fuel_mix = client.get_fuel_mix(start, end)
            load = client.get_load(start, end)

        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'records': {
                'lmp': len(lmp),
                'fuel_mix': len(fuel_mix),
                'load': len(load)
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/plots')
def get_plots():
    """Generate and return all plots as Plotly JSON."""
    try:
        hours = 12
        end = datetime.now()
        start = end - timedelta(hours=hours)

        # Fetch data
        with CAISOClient() as client:
            lmp = client.get_lmp(start, end, market="RTM")
            trading_hub_lmp = client.get_trading_hub_lmp(start, end, market="RTM")
            fuel_mix = client.get_fuel_mix(start, end)
            load = client.get_load(start, end)

        # Generate Plotly figures and convert to JSON
        plots = {
            'lmp_components': json.loads(plot_lmp_components(lmp).to_json()),
            'trading_hubs': json.loads(plot_trading_hubs(trading_hub_lmp).to_json()),
            'fuel_mix_stack': json.loads(plot_fuel_mix(fuel_mix).to_json()),
            'fuel_mix_pie': json.loads(plot_fuel_mix_pie(fuel_mix).to_json()),
            'load_profile': json.loads(plot_load_profile(load).to_json()),
        }

        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'plots': plots
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/api/stats')
def get_stats():
    """Get summary statistics."""
    try:
        hours = 12
        end = datetime.now()
        start = end - timedelta(hours=hours)

        with CAISOClient() as client:
            lmp = client.get_lmp(start, end, market="RTM")
            fuel_mix = client.get_fuel_mix(start, end)
            load = client.get_load(start, end)

        # Calculate statistics
        avg_lmp = lmp['lmp_total'].mean()
        max_lmp = lmp['lmp_total'].max()
        min_lmp = lmp['lmp_total'].min()

        avg_load = load['load_mw'].mean()
        max_load = load['load_mw'].max()

        # Top fuel sources
        fuel_avg = fuel_mix.groupby('fuel_type')['generation_mw'].mean()
        top_fuels = fuel_avg.nlargest(5).to_dict()

        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'lmp': {
                'average': float(avg_lmp),
                'max': float(max_lmp),
                'min': float(min_lmp),
            },
            'load': {
                'average': float(avg_load),
                'max': float(max_load),
            },
            'top_fuels': {k: float(v) for k, v in top_fuels.items()}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Run in development mode
    app.run(debug=True, host='0.0.0.0', port=5000)
