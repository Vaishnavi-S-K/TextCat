# Deploy to GitHub Codespaces (100% Free)

## Quick Start (5 minutes)

### Step 1: Launch Codespace
1. Go to: https://github.com/ShivaprasadMurashillin/textcat-app
2. Click **Code** button → **Codespaces** tab
3. Click **Create codespace on main**
4. Wait ~2 minutes for environment to load

### Step 2: Start Docker Stack
Once VS Code loads in browser, open terminal and run:
```bash
cd monitoring
docker-compose up -d
```

### Step 3: Access Services
Codespaces will auto-forward ports. Click the **Ports** tab (bottom panel):
- **Port 3000** (Grafana) → Click globe icon → **Make Public** → Open URL
- **Port 5000** (Flask API) → Click globe icon → **Make Public** → Open URL  
- **Port 9090** (Prometheus) → Click globe icon → **Make Public** → Open URL

### Step 4: Import Dashboard
1. Open Grafana URL (port 3000)
2. Login: **admin / admin** (skip password change)
3. ☰ menu → Dashboards → Import
4. Upload: `monitoring/grafana/dashboards/enhanced-dashboard.json`
5. Click Import

### Step 5: Generate Test Traffic
```bash
cd monitoring
./scripts/test_traffic.ps1
```

## Share With Professor
Copy the three public URLs:
- **Grafana Dashboard**: `https://xxxxx-3000.app.github.dev`
- **Flask API**: `https://xxxxx-5000.app.github.dev`
- **Prometheus Metrics**: `https://xxxxx-9090.app.github.dev`

## Important Notes
- **Free Tier**: 60 hours/month (enough for demos + development)
- **Persistence**: Codespace stays active for 30 days of inactivity
- **Stop When Done**: Codespaces → ⋮ menu → Stop to save hours
- **Database**: Already configured (Render PostgreSQL)

## Troubleshooting
- **Docker not starting?** Run: `sudo systemctl start docker`
- **Ports not forwarding?** Manually add in Ports tab: 3000, 5000, 9090
- **Container build slow?** First build takes 3-5 minutes (downloads images)

## What You Get
✅ Full monitoring stack (Flask + Prometheus + Grafana)  
✅ Public URLs accessible from anywhere  
✅ All 15 Grafana dashboard panels working  
✅ No credit card required  
✅ Professional cloud deployment demo
