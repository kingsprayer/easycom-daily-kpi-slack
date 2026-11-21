# Easycom Daily KPI Reporting & Slack Automation (Node.js & Python)

An enterprise automation suite for **Easycom / EasyEcom** that:
1. Converts raw daily e-commerce data (from REST API or manual CSV export) into structured KPI reports (HTML, Markdown, Master History CSV).
2. Formats and posts an executive morning briefing to **Slack** with Block Kit layouts, status flags, alerts, channel breakdown, and action buttons.
3. Provides an interactive Executive Web Dashboard on `http://localhost:5000`.
4. Provides serverless 24/7 automated scheduling via **GitHub Actions** (08:30 AM IST daily) or Docker (`node:22-alpine`).

---

## Architecture Overview

```
[EasyEcom API (getAllOrdersV2) OR Portal CSV Export]
                      │
                      ▼
        [1. Ingestion & Normalization]
                      │
                      ▼
         [2. KPI Computation Engine]
     (GMV, Net Rev, AOV, Fulfillment %,
     SLA Aging, Channels, Returns, OOS)
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
 [3. File Reports]         [4. Slack Card]
  • daily_kpi.html          • Block Kit Layout
  • daily_kpi.md            • Operational Alerts
  • master_kpi_history.csv  • Channel Breakdown
```

---

## Quick Start (Node.js)

### 1. Installation
Requires Node.js 18+ (tested on Node.js 22 LTS):
```bash
npm install
```

### 2. Interactive Executive Web Dashboard
Launch the web dashboard on port 5000:
```bash
npm start
# Or for live reload during development: npm run dev
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser to view:
- 6 Real-time KPI Cards
- Realistic Slack `#easycom-daily-kpi` messenger mockup
- On-demand pipeline execution triggers (Mock, CSV, Anomaly)
- Sales Channel share progress bars
- Historical performance log table & CSV export

### 3. CLI Pipeline Execution via npm scripts
- **Run Mock Baseline (Dry-Run):**
  ```bash
  npm run mock
  ```
- **Ingest Sample CSV Export:**
  ```bash
  npm run csv
  ```
- **Simulate Warehouse Anomaly (SLA breach & high returns):**
  ```bash
  npm run anomaly
  ```
- **Live Automated Morning Cron:**
  ```bash
  npm run cron
  ```

### 4. Direct CLI Commands
```bash
# Ingest specific CSV export
node run_daily_kpi.js --from-csv path/to/easyecom_export.csv --dry-run

# Run for a specific past date
node run_daily_kpi.js --date 2026-09-20 --mock
```

---

## Live Slack & EasyEcom Configuration

Copy `.env.example` to `.env` and fill in credentials:
```bash
cp .env.example .env
```
Key variables:
- `EASYECOM_API_KEY`: Generated in EasyEcom Account Settings > Change Credentials.
- `EASYECOM_JWT_TOKEN`: Bearer JWT token from EasyEcom API portal.
- `SLACK_WEBHOOK_URL`: Incoming Webhook URL from your Slack App.

---

## 24/7 Cloud Automation (When PC is Off)

### Option A: GitHub Actions (Free Serverless Cron)
Configured in `.github/workflows/daily_kpi_cron.yml`.
Runs every morning at **03:00 UTC (08:30 AM IST)** without any server infrastructure.
Configure `SLACK_WEBHOOK_URL`, `EASYECOM_API_KEY`, and `EASYECOM_JWT_TOKEN` in your GitHub repository secrets.

### Option B: Cloud Docker Container
Deploy to Render, Railway, or Google Cloud Run using the included `Dockerfile` (`node:22-alpine`).
Image size: ~130MB. Exposes port 5000.
