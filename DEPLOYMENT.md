# Deployment Guide

## Local Development

```bash
pip install -r requirements.txt
python app.py
```

Visit http://localhost:5000. The app runs in Flask's debug mode with auto-reload.

---

## Render (Recommended)

The repo includes a `render.yaml` Blueprint file. If you connect the repository to Render, it reads that file and configures the service automatically.

1. Go to [render.com](https://render.com) and sign in with GitHub.
2. Click **New > Blueprint**.
3. Select the `caiso-oasis-analysis` repository.
4. Click **Apply**. Render will build and deploy the service.

Your dashboard will be live at `https://<service-name>.onrender.com` within a few minutes.

**Free tier note:** Render's free tier spins down a service after 15 minutes of inactivity. The first request after spin-down takes 30-60 seconds while the container restarts. The CAISO API calls add another 5-15 seconds on top of that. If you need the service always on, upgrade to the Starter plan ($7/month).

### Manual Render setup (without render.yaml)

If you prefer to configure the service through the Render dashboard:

| Setting | Value |
|---|---|
| Runtime | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |
| Instance type | Free (or Starter for always-on) |
| Region | Oregon (US West) - closest to CAISO |

No environment variables are required for basic operation.

---

## Heroku

```bash
heroku create your-app-name
git push heroku main
heroku open
```

The `Procfile` is already configured with the correct gunicorn command.

---

## VPS / Self-Hosted

### 1. Clone and install

```bash
git clone https://github.com/Maaz679/caiso-oasis-analysis.git
cd caiso-oasis-analysis
pip install -r requirements.txt
```

### 2. Run with gunicorn

```bash
gunicorn app:app --bind 0.0.0.0:8000 --workers 2 --timeout 120
```

### 3. Nginx reverse proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

The `proxy_read_timeout` should match or exceed gunicorn's `--timeout` value. The CAISO API can take 10-20 seconds on the first cold fetch.

### 4. Systemd service

Create `/etc/systemd/system/caiso-dashboard.service`:

```ini
[Unit]
Description=CAISO Market Dashboard
After=network.target

[Service]
User=youruser
WorkingDirectory=/path/to/caiso-oasis-analysis
ExecStart=/usr/bin/gunicorn app:app --bind 127.0.0.1:8000 --workers 2 --timeout 120
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable caiso-dashboard
sudo systemctl start caiso-dashboard
```

---

## Environment Variables

No variables are required. Optional overrides:

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `5000` | Port for local dev; most platforms set this automatically |
| `FLASK_ENV` | `production` | Set to `development` to enable debug mode locally |

---

## Troubleshooting

### CAISO API timeout on first load

The OASIS API can be slow, especially for large date ranges. The default fetch window is 12 hours. If you see timeouts, reduce it in `app.py`:

```python
hours = 6  # line ~39, ~69, ~108 in app.py
```

### 502 Bad Gateway on Render or Heroku

This almost always means gunicorn timed out waiting for the CAISO API response. The `--timeout 120` flag in the start command gives the worker 120 seconds before gunicorn kills it. If CAISO is slow on that day, increase it:

```
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 180
```

### App sleeping (Render free tier)

Free tier services spin down after 15 minutes of inactivity. You can prevent this by:
- Upgrading to Render Starter ($7/month)
- Setting up an external uptime monitor (UptimeRobot free tier) to ping `/health` every 10 minutes
