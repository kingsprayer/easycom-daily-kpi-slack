# Easycom Daily KPI Reporting & Slack Automation: Node.js Edition

> [!TIP]
> **Complete Node.js Migration:**
> The entire Daily KPI Reporting & Slack Automation pipeline and Executive Web Dashboard have been migrated to modern **Node.js (v22 LTS)** using native ES Modules, native `fetch`, Express, and minimal dependencies.

This walkthrough guides you through both operational tasks and deployment options:
1. **Task 1: The Daily Report Making Process** — How raw daily transaction, order, return, and inventory data from EasyEcom is extracted, cleaned, and transformed into an executive KPI report (HTML, Markdown, and Master CSV) using Node.js.
2. **Task 2: Automated Slack Daily Morning Broadcast** — How that KPI report is converted into an interactive Slack Block Kit card and posted automatically every morning at your chosen time (e.g., 08:30 AM IST) with operational health alerts.
3. **Task 3: Running 24/7 in the Cloud (PC Off)** — How to keep the pipeline and dashboard running continuously without keeping your computer on via GitHub Actions (Free Serverless Cron) or Render/Railway/Cloud Run (Docker Container).

---

## High-Level Architecture & End-to-End Pipeline (Node.js)

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           EASYECOM ERP SOURCE                          │
  │   Option A: API (getAllOrdersV2, /inventory)                           │
  │   Option B: Manual CSV Export (Dashboard > Sales Details > Queue)      │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Raw Transactions
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │             TASK 1: DAILY REPORT MAKING PROCESS (Node.js)              │
  │                                                                        │
  │  1. Ingestion & Normalization (Map disparate channel schemas)          │
  │  2. Data Cleansing (Filter test orders, isolate cancellations/RTO)     │
  │  3. KPI Calculation Engine (src/kpiCalculator.js):                     │
  │     • Gross GMV vs Net Realized Revenue                                │
  │     • Order Volume & Average Order Value (AOV)                         │
  │     • Fulfillment Rate & SLA Aging Backlog (>24h)                      │
  │     • Channel Breakdown (Amazon, Flipkart, Shopify, QuickComm)        │
  │     • Returns & RTO %                                                  │
  │     • Stockout Alert (OOS SKUs)                                        │
  │  4. File Generation (src/reportGenerator.js):                          │
  │     • Standalone Styled HTML Report (Print-to-PDF ready)               │
  │     • Executive Markdown Briefing                                      │
  │     • Master History CSV (Appended for BI & trend tracking)           │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │ Structured KPI Summary
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │            TASK 2: AUTOMATED SLACK POSTING (Node.js fetch)             │
  │                                                                        │
  │  1. Block Kit Layout Builder (src/slackFormatter.js)                   │
  │  2. Dynamic Threshold Checker (Flags 🟢 Healthy, 🟡 Attention, 🔴 Alert)│
  │  3. Native HTTP Dispatcher (src/slackNotifier.js via native fetch)     │
  │  4. Automation Trigger:                                                │
  │     • 100% Free Serverless GitHub Actions Cron (08:30 AM IST)          │
  │     • Or Containerized Web Dashboard (Render / Cloud Run)              │
  │     • Or Local Mac/Linux Crontab                                       │
  └────────────────────────────────────────────────────────────────────────┘
```

---

# Part 1: Task 1 — The Daily Report Making Process

The goal of this process is to take hundreds or thousands of unorganized daily transaction records and distill them into five clear executive numbers: **Revenue, Volume, Fulfillment Health, Channel Share, and Quality/Returns**.

### Step 1.1: Data Ingestion (Two Methods)

#### Method A: Automated API Pull (Default)
The Node.js script communicates with EasyEcom's REST API:
- **Orders Endpoint:** `GET https://api.easyecom.io/orders/v2/getAllOrders`
- **Filters Applied:**
  - `start_date`: `YYYY-MM-DD 00:00:00`
  - `end_date`: `YYYY-MM-DD 23:59:59`
- **Headers:**
  - `x-api-key`: Primary account API key
  - `Authorization`: `Bearer <jwt_token>`
- **Inventory Endpoint:** `GET https://api.easyecom.io/inventory/details` (Fetches active SKUs, out of stock SKUs, and damaged units).

#### Method B: Manual Portal Export Fallback (No Code Required)
If you do not have API keys yet, any operations team member can export raw data:
1. Log in to your **EasyEcom Dashboard**.
2. Navigate to **Analytics / Reports ➔ Sales Details** (or Orders).
3. Set the Date Filter to **Yesterday** (or target date) and select all warehouses.
4. Click **Submit** ➔ **Queue Report**.
5. Once finished in **Export Job**, download the `.csv` file.
6. Run: `npm run csv` or `node run_daily_kpi.js --from-csv path/to/downloaded_file.csv`.
   *The custom `EasyEcomCsvLoader` automatically standardizes mismatched column headers!*

---

### Step 1.2: Data Cleaning & Normalization Rules

Before calculating metrics, the ingestion layer enforces these data rules:
1. **Header Alias Matching:** Maps varied column names (`total_amount`, `grand_total`, `invoice_amount`) to standard internal properties.
2. **Numeric Sanitization:** Strips currency symbols (`₹`, `$`) and commas before floating-point conversion.
3. **Status Normalization:** Consolidates multi-marketplace terms into canonical buckets:
   - `Delivered` ➔ Delivered
   - `Dispatched`, `Shipped`, `Handover to Courier` ➔ Shipped
   - `In-Transit`, `Out for Delivery` ➔ In-Transit
   - `Pending`, `Allocated`, `Unfulfilled`, `Breached` ➔ Pending SLA Backlog
   - `Customer Return`, `Return Received` ➔ Customer Return
   - `RTO`, `Undelivered Return` ➔ Courier RTO
   - `Cancelled`, `Void` ➔ Cancelled

---

### Step 1.3: Formula Derivations

The engine calculates:
- **Gross GMV:** $\sum \text{Order Value}$ of all valid consumer orders (excluding test/cancelled before dispatch).
- **Net Realized Revenue:** $\text{Gross GMV} - (\text{Cancelled Orders Value} + \text{Customer Returns Value} + \text{RTO Value})$.
- **Average Order Value (AOV):** $\frac{\text{Gross GMV}}{\text{Total Orders}}$.
- **Fulfillment Rate:** $\frac{\text{Fulfilled / Dispatched Orders}}{\text{Total Actionable Orders}} \times 100$.
- **Return & RTO Rate:** $\frac{\text{Customer Returns} + \text{Courier RTOs}}{\text{Dispatched Orders}} \times 100$.
- **Channel Share:** $\frac{\text{Channel GMV}}{\text{Total Gross GMV}} \times 100$.

---

# Part 2: Task 2 — Automated Slack Morning Broadcast

### Step 2.1: Slack Block Kit Visual Layout

The payload created by `src/slackFormatter.js` renders a modern executive summary in Slack:

```
┌──────────────────────────────────────────────────────────┐
│  📊 Easycom Daily KPI Briefing                           │
│  📅 Period: 2026-09-22 | Status: 🟢 HEALTHY | Source: ERP │
├──────────────────────────────────────────────────────────┤
│  💰 Gross Sales (GMV)        📦 Orders & Volume          │
│  > ₹14,95,907.66             > 515 Orders                │
│  > Net: ₹13,80,380.25        > 625 Units (1.21 / order)  │
│                                                          │
│  📈 Average Order Value      🚚 Fulfillment Rate         │
│  > ₹2,991.82                 > 91.0% (455 dispatched)    │
├──────────────────────────────────────────────────────────┤
│  ↩️ Total Returns & RTO      ⏳ SLA Aging & Backlog       │
│  > 6.6% (30 returns)         > 15 orders pending         │
│  > RTO: 10 | Cust: 20        > Cancellations: 15 (2.9%)  │
│                                                          │
│  💳 Payment Split            🏭 Stockout Health          │
│  > 65.8% Prepaid | 34.2% COD > 12 OOS SKUs (34 low stock)│
├──────────────────────────────────────────────────────────┤
│  🛒 Sales Channel Performance:                           │
│  • Amazon India: 185 orders | ₹4,90,296.33 (32.8%)       │
│  • Flipkart: 129 orders | ₹3,93,006.54 (26.3%)           │
│  • Shopify (Direct Website): 105 orders | ₹3,41,399.14   │
│  • Blinkit (QuickCommerce): 48 orders | ₹1,38,222.44     │
│  • Myntra: 48 orders | ₹1,32,983.21 (8.9%)               │
├──────────────────────────────────────────────────────────┤
│  [ Open EasyEcom Dashboard ↗ ]                           │
└──────────────────────────────────────────────────────────┘
```

> [!NOTE]
> **Dynamic Anomaly Alerting:**
> If any KPI breaches configured safety thresholds (e.g. Return rate > 12% or Fulfillment < 85%), the banner dynamically flips to `🔴 CRITICAL` or `🟡 ATTENTION NEEDED` and inserts an actionable code block at the top:
> ```
> *⚠️ Operational Action Required:*
> ⚠️ Fulfillment Rate (70.0%) is below target (85%)
> 🚨 Total Returns & RTO (14.6%) exceeded safe threshold (12%)
> ```

---

# Part 3: Step-by-Step Hands-On Guide (Node.js)

All code and dependencies have been installed and verified in your workspace at:
`./easycom-daily-kpi-slack/`

### 1. Test Mock Pipeline in Dry-Run Mode
```bash
npm run mock
# Equivalent to: node run_daily_kpi.js --mock --dry-run
```
*Calculates metrics for 515 mock orders, generates the HTML/Markdown files, appends to CSV, and outputs the Slack payload.*

### 2. Ingest Raw CSV Export
```bash
npm run csv
# Equivalent to: node run_daily_kpi.js --from-csv sample_data/sample_easyecom_orders.csv --dry-run
```
*Parses 15 raw transactions, calculates metrics, detects returns anomaly (16.7%), and outputs formatted report.*

### 3. Test Dynamic Operational Anomaly Simulation
```bash
npm run anomaly
# Equivalent to: node run_daily_kpi.js --mock --simulate-anomaly --dry-run
```
*Fulfillment rate drops to 70% (<85%), status flips to 🔴 CRITICAL, and operational warning banner is injected.*

### 4. Interactive Localhost Web Dashboard
Launch the Node.js Express web console:
```bash
npm start
# Or for live development: npm run dev
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.
**Key Features:**
- 6 Real-time Executive KPI cards (Gross GMV, Volume, AOV, Fulfillment %, Returns %, OOS SKUs).
- Authentic Slack messenger mockup simulating `#easycom-daily-kpi`.
- Instant on-demand execution triggers (🚀 Run Mock, 📂 Ingest CSV, ⚠️ Simulate Anomaly).
- Interactive Channel Breakdown progress bars (Amazon, Flipkart, Shopify, Myntra, Blinkit).
- Master Historical Performance Log table with direct CSV download.
- One-click access to standalone print-to-PDF ready HTML reports.

### 5. Broadcast to Real Slack Channel
1. Add your Slack Webhook URL to `.env`:
   ```bash
   cp .env.example .env
   # Edit .env and set SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
   ```
2. Run with mock or CSV data:
   ```bash
   node run_daily_kpi.js --mock
   ```
   Check your Slack channel — the KPI card will appear immediately!

---

# Part 4: Running 24/7 Even If Your PC Is Off

### Option A: GitHub Actions (Recommended — 100% Free & Serverless)
The codebase includes `.github/workflows/daily_kpi_cron.yml` configured for Node.js 22 LTS:
1. Push this project to your GitHub repository (private or public).
2. Go to **Settings ➔ Secrets and variables ➔ Actions**.
3. Add repository secrets:
   - `SLACK_WEBHOOK_URL`
   - `EASYECOM_API_KEY`
   - `EASYECOM_JWT_TOKEN`
4. The workflow will automatically run every morning at **03:00 UTC (08:30 AM IST)**.
5. You can also trigger it manually anytime via **Actions ➔ Easycom Daily KPI Slack Automation ➔ Run workflow**.

### Option B: Cloud Container Deployment (Render / Railway / Cloud Run)
The lightweight Alpine Dockerfile (`node:22-alpine`) packages the web dashboard and scheduler:
```dockerfile
FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev
COPY . .
EXPOSE 5000
CMD ["npm", "start"]
```
- **Image Size:** ~130MB (compared to ~400MB in Python).
- **Deploy:** Connect your repository to Render or Railway as a Web Service. It automatically detects the `Dockerfile`, starts on port 5000, and stays online 24/7!

---

## File Reference & Codebase Map

| File | Purpose |
| :--- | :--- |
| [package.json](file://./easycom-daily-kpi-slack/package.json) | Node.js project manifest, dependencies (`express`, `cors`, `dotenv`), and npm scripts. |
| [web_app.js](file://./easycom-daily-kpi-slack/web_app.js) | Interactive Executive Web Dashboard on http://localhost:5000 (Express). |
| [run_daily_kpi.js](file://./easycom-daily-kpi-slack/run_daily_kpi.js) | Main orchestration entrypoint (CLI & programmatic API). |
| [Dockerfile](file://./easycom-daily-kpi-slack/Dockerfile) | Production Docker container configuration (`node:22-alpine`). |
| [config.json](file://./easycom-daily-kpi-slack/config.json) | Thresholds, alert limits, currency, and channel settings. |
| [src/kpiCalculator.js](file://./easycom-daily-kpi-slack/src/kpiCalculator.js) | Core KPI formulas (GMV, AOV, Fulfillment %, Returns %, SLA aging). |
| [src/csvDataLoader.js](file://./easycom-daily-kpi-slack/src/csvDataLoader.js) | Ingests and normalizes raw CSV exports from EasyEcom portal. |
| [src/easyecomClient.js](file://./easycom-daily-kpi-slack/src/easyecomClient.js) | EasyEcom REST API client + realistic mock generator (with anomaly simulation). |
| [src/reportGenerator.js](file://./easycom-daily-kpi-slack/src/reportGenerator.js) | Compiles HTML, Markdown, and historical master CSV files. |
| [src/slackFormatter.js](file://./easycom-daily-kpi-slack/src/slackFormatter.js) | Builds rich Slack Block Kit payloads. |
| [src/slackNotifier.js](file://./easycom-daily-kpi-slack/src/slackNotifier.js) | Webhook delivery agent using native Node.js `fetch`. |
| [.github/workflows/daily_kpi_cron.yml](file://./easycom-daily-kpi-slack/.github/workflows/daily_kpi_cron.yml) | 24/7 automated scheduled daily runner (08:30 AM IST) using Node.js 22. |
| [reports/master_kpi_history.csv](file://./easycom-daily-kpi-slack/reports/master_kpi_history.csv) | Master CSV log tracking historical metrics day by day. |
