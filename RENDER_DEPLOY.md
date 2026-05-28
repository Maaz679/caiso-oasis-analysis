# Deploy to Render - Quick Guide

## Step-by-Step Deployment

### 1. Push to GitHub
Make sure all your code is pushed to GitHub (already done).

### 2. Create Render Account
1. Go to https://render.com
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

### 3. Create New Web Service
1. Click "New +" button in Render dashboard
2. Select "Web Service"
3. Connect your GitHub repository: `Maaz679/caiso-oasis-analysis`
4. Click "Connect"

### 4. Configure the Service

**Basic Settings:**
- Name: `caiso-market-dashboard` (or any name you prefer)
- Region: `Oregon (US West)` (closest to California/CAISO)
- Branch: `main`
- Runtime: `Python 3`

**Build & Deploy Settings:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

**Instance Type:**
- Free tier: Select "Free" (512MB RAM, shared CPU)
- Paid tier: Select "Starter" ($7/month, 512MB RAM, better performance)

### 5. Environment Variables (Optional)
No environment variables needed for basic deployment.

### 6. Deploy
1. Click "Create Web Service"
2. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Start the application
3. Wait 2-3 minutes for first deployment

### 7. Access Your Dashboard
Once deployed, your dashboard will be live at:
```
https://caiso-market-dashboard.onrender.com
```
(Replace with your actual service name)

## Free Tier Limitations

**What you get:**
- 512MB RAM (sufficient for this app)
- Shared CPU
- Auto-deploy on git push
- Free SSL certificate
- Custom domain support

**Limitations:**
- Spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds (cold start)
- 750 hours/month of runtime (approximately 31 days, so always on)

**Note:** Since CAISO API calls take a few seconds, the initial page load might take 30-40 seconds on free tier. Subsequent loads are fast.

## Upgrade to Paid Tier ($7/month)

If you want better performance:
1. Go to your service settings
2. Change instance type to "Starter"
3. Benefits:
   - Always on (no spin-down)
   - Faster response times
   - More consistent performance

## Auto-Deploy Setup

Render automatically deploys when you push to GitHub:
```bash
git add .
git commit -m "Update dashboard"
git push origin main
```
Render detects the push and redeploys automatically (takes 1-2 minutes).

## Custom Domain (Optional)

To use your own domain:
1. Go to service Settings > Custom Domain
2. Add your domain (e.g., caiso.yourdomain.com)
3. Update your DNS records as instructed
4. Render provides free SSL certificate

## Monitoring

**View logs:**
1. Go to your service dashboard
2. Click "Logs" tab
3. See real-time application logs

**Check status:**
- Green dot: Running
- Yellow dot: Deploying
- Red dot: Failed (check logs)

## Troubleshooting

**Deployment failed:**
- Check logs for errors
- Verify requirements.txt has all dependencies
- Ensure Python version matches runtime.txt

**App not loading:**
- Check if service is sleeping (free tier)
- Wait 30-60 seconds for spin-up
- Check logs for runtime errors

**CAISO API timeout:**
- Normal on first load after spin-down
- Refresh the page if it times out
- Consider upgrading to paid tier for better performance

## Cost Summary

- **Free tier:** $0/month (with spin-down)
- **Starter tier:** $7/month (always on, better performance)
- No data transfer fees
- No hidden costs

Your dashboard is now live and accessible worldwide!
