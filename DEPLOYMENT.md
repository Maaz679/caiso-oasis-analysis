# Deployment Guide

This guide shows how to deploy the CAISO Market Analysis Dashboard as a live web application.

## Quick Start (Local Development)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser to: http://localhost:5000

The dashboard will automatically fetch live data from CAISO OASIS API when you visit.

## Production Deployment

### Option 1: Deploy to Heroku

1. Create a `Procfile`:
```
web: gunicorn app:app
```

2. Create `runtime.txt`:
```
python-3.12.0
```

3. Deploy:
```bash
heroku create your-app-name
git push heroku main
heroku open
```

### Option 2: Deploy to Railway.app

1. Connect your GitHub repository to Railway
2. Railway will auto-detect Flask and deploy
3. Your app will be live at: https://your-app.railway.app

### Option 3: Deploy to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `gunicorn app:app`
5. Deploy

### Option 4: Deploy to Your Own Server (VPS)

1. SSH into your server

2. Clone repository:
```bash
git clone https://github.com/Maaz679/caiso-oasis-analysis.git
cd caiso-oasis-analysis
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run with Gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

5. Set up Nginx as reverse proxy:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

6. Use systemd for auto-restart:

Create `/etc/systemd/system/caiso-dashboard.service`:
```ini
[Unit]
Description=CAISO Market Analysis Dashboard
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/caiso-oasis-analysis
ExecStart=/usr/bin/gunicorn -w 4 -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable caiso-dashboard
sudo systemctl start caiso-dashboard
```

### Option 5: Deploy to Vercel (Serverless)

1. Install Vercel CLI:
```bash
npm install -g vercel
```

2. Create `vercel.json`:
```json
{
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

3. Deploy:
```bash
vercel
```

## Features

- Live data fetching from CAISO OASIS API
- Auto-refresh every 10 minutes
- Manual refresh button
- Responsive design
- Real-time visualizations
- REST API endpoints

## API Endpoints

- `GET /` - Dashboard home page
- `GET /api/plots` - Get all plots as base64 images
- `GET /api/stats` - Get summary statistics
- `GET /api/fetch-data` - Trigger data fetch
- `GET /health` - Health check

## Configuration

### Environment Variables

You can set these in your deployment platform:

- `FLASK_ENV=production` - Set production mode
- `PORT=5000` - Port number (auto-set by most platforms)

### Caching

For production, consider adding Redis caching:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'redis'})

@cache.cached(timeout=600)  # Cache for 10 minutes
def get_data():
    # ... fetch data
```

## Monitoring

Add health check monitoring to ensure your app stays online:

- Use the `/health` endpoint
- Set up uptime monitoring with services like:
  - UptimeRobot
  - Pingdom
  - StatusCake

## Troubleshooting

### CAISO API Timeouts

If you experience timeouts, reduce the data fetch window in `app.py`:

```python
hours = 6  # Reduce from 12 to 6
```

### Memory Issues

Reduce image DPI in `app.py`:

```python
fig.savefig(buf, format='png', dpi=100, ...)  # Reduce from 150
```

### Slow Loading

Add caching or use a background worker:

```python
from flask_caching import Cache
cache = Cache(app)

@cache.memoize(timeout=600)
def generate_plots():
    # ... generate plots
```

## Security

For production deployments:

1. Set `app.config['SECRET_KEY']`
2. Use HTTPS (Let's Encrypt)
3. Add rate limiting:
```bash
pip install Flask-Limiter
```

4. Enable CORS if needed:
```bash
pip install flask-cors
```

## Performance

- Images are generated on-demand
- Auto-refresh every 10 minutes
- Use CDN for static assets
- Consider Redis for caching

Your dashboard will be live and automatically update with fresh CAISO market data!
