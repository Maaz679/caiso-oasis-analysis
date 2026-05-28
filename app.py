"""
Flask web application for CAISO Market Analysis Dashboard

Serves live dashboard with real-time data from CAISO OASIS API.
"""

from flask import Flask, render_template, jsonify, send_file
from datetime import datetime, timedelta
from pathlib import Path
import io
import base64

from src.oasis import CAISOClient
from notebooks.visualize_data import (
    plot_lmp_components,
    plot_trading_hubs_comparison,
    plot_fuel_mix,
    plot_fuel_mix_pie,
    plot_load_profile
)

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development


def generate_plot_base64(plot_func, *args):
    """Generate plot and return as base64 encoded string."""
    import matplotlib.pyplot as plt

    fig = plot_func(*args)

    # Save to bytes buffer
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    buf.seek(0)
    plt.close(fig)

    # Encode to base64
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return f"data:image/png;base64,{img_base64}"


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
    """Generate and return all plots as base64 encoded images."""
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

        # Generate plots
        plots = {
            'lmp_components': generate_plot_base64(plot_lmp_components, lmp),
            'trading_hubs': generate_plot_base64(plot_trading_hubs_comparison, trading_hub_lmp),
            'fuel_mix_stack': generate_plot_base64(plot_fuel_mix, fuel_mix),
            'fuel_mix_pie': generate_plot_base64(plot_fuel_mix_pie, fuel_mix),
            'load_profile': generate_plot_base64(plot_load_profile, load),
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
