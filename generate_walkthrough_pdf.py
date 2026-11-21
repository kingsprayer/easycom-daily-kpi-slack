#!/usr/bin/env python3
"""Script to convert Easycom Daily KPI Walkthrough into a publication-quality PDF.

Utilizes headless Google Chrome with custom print-oriented styling for A4 pages.
"""

import os
import subprocess
import sys

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Easycom Daily KPI Reporting & Slack Automation - Complete Walkthrough</title>
<style>
  @page {
    size: A4;
    margin: 16mm 14mm 16mm 14mm;
    @bottom-right {
      content: counter(page);
      font-size: 9pt;
      color: #64748b;
    }
  }

  :root {
    --primary: #0284c7;
    --primary-dark: #0369a1;
    --text: #0f172a;
    --text-muted: #475569;
    --border: #e2e8f0;
    --bg-code: #f8fafc;
    --bg-card: #ffffff;
    --success: #15803d;
    --warning: #b45309;
    --danger: #b91c1c;
  }

  * {
    box-sizing: border-box;
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--text);
    background: #ffffff;
    line-height: 1.55;
    font-size: 10pt;
    margin: 0;
    padding: 0;
  }

  /* Cover Header */
  .cover {
    border-bottom: 3px solid var(--primary);
    padding-bottom: 20px;
    margin-bottom: 25px;
  }
  .company-tag {
    font-size: 11pt;
    font-weight: 700;
    color: var(--primary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
  h1 {
    font-size: 22pt;
    font-weight: 800;
    color: #0f172a;
    margin: 8px 0 10px 0;
    line-height: 1.2;
  }
  .doc-subtitle {
    font-size: 11pt;
    color: var(--text-muted);
    margin: 0;
  }
  .meta-bar {
    margin-top: 14px;
    display: flex;
    gap: 20px;
    font-size: 9pt;
    color: var(--text-muted);
  }
  .meta-item strong {
    color: var(--text);
  }

  h2 {
    font-size: 14pt;
    font-weight: 700;
    color: #0f172a;
    border-bottom: 1.5px solid var(--border);
    padding-bottom: 6px;
    margin-top: 28px;
    margin-bottom: 12px;
    page-break-after: avoid;
  }

  h3 {
    font-size: 11.5pt;
    font-weight: 700;
    color: var(--primary-dark);
    margin-top: 20px;
    margin-bottom: 8px;
    page-break-after: avoid;
  }

  h4 {
    font-size: 10.5pt;
    font-weight: 600;
    color: #1e293b;
    margin-top: 14px;
    margin-bottom: 6px;
    page-break-after: avoid;
  }

  p {
    margin: 0 0 10px 0;
    color: #1e293b;
  }

  ul, ol {
    margin: 0 0 12px 0;
    padding-left: 20px;
  }

  li {
    margin-bottom: 4px;
  }

  /* Callout Alerts */
  .alert {
    border-left: 4px solid var(--primary);
    background: #f0f9ff;
    padding: 12px 16px;
    border-radius: 4px;
    margin: 14px 0;
    page-break-inside: avoid;
    font-size: 9.5pt;
  }
  .alert.alert-warning {
    border-color: #f59e0b;
    background: #fffbeb;
    color: #78350f;
  }
  .alert.alert-success {
    border-color: #10b981;
    background: #ecfdf5;
    color: #064e3b;
  }
  .alert strong {
    display: block;
    margin-bottom: 3px;
    font-size: 10pt;
  }

  /* Diagrams and ASCII boxes */
  .diagram-box {
    background: #0f172a;
    color: #f8fafc;
    border-radius: 6px;
    padding: 14px 18px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
    font-size: 8pt;
    line-height: 1.4;
    white-space: pre;
    overflow-x: hidden;
    margin: 14px 0;
    page-break-inside: avoid;
    border: 1px solid #1e293b;
  }

  /* Code blocks */
  pre, code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }
  p code, li code, td code {
    background: var(--bg-code);
    border: 1px solid var(--border);
    padding: 1.5px 5px;
    border-radius: 3px;
    font-size: 9pt;
    color: #0369a1;
  }
  pre {
    background: var(--bg-code);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    font-size: 8.5pt;
    line-height: 1.45;
    margin: 10px 0;
    page-break-inside: avoid;
    overflow-x: hidden;
    white-space: pre-wrap;
    word-break: break-word;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0;
    page-break-inside: avoid;
    font-size: 9pt;
  }
  th, td {
    border: 1px solid var(--border);
    padding: 7px 10px;
    text-align: left;
    vertical-align: top;
  }
  th {
    background: #f1f5f9;
    font-weight: 700;
    color: #0f172a;
  }
  tr:nth-child(even) td {
    background: #fafafa;
  }

  /* Slack Preview Card */
  .slack-preview {
    border: 1px solid #cbd5e1;
    border-left: 4px solid var(--primary);
    border-radius: 6px;
    background: #ffffff;
    padding: 16px;
    margin: 14px 0;
    page-break-inside: avoid;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  }
  .slack-header {
    font-size: 12pt;
    font-weight: 700;
    color: #0f172a;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .slack-meta {
    font-size: 8.5pt;
    color: var(--text-muted);
    margin-bottom: 10px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
  }
  .slack-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin: 10px 0;
  }
  .slack-item {
    background: #f8fafc;
    border: 1px solid var(--border);
    padding: 8px 12px;
    border-radius: 5px;
  }
  .slack-item-label {
    font-size: 8pt;
    font-weight: 600;
    color: var(--text-muted);
    text-transform: uppercase;
  }
  .slack-item-val {
    font-size: 11pt;
    font-weight: 700;
    color: #0f172a;
    margin-top: 2px;
  }
  .slack-item-sub {
    font-size: 7.5pt;
    color: #64748b;
  }

  .badge-healthy {
    display: inline-block;
    background: #dcfce7;
    color: #15803d;
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 8pt;
    font-weight: 700;
  }

  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<div class="cover">
  <div class="company-tag">Easycom Operations & Analytics Automation</div>
  <h1>Daily KPI Reporting & Slack Automation</h1>
  <div class="doc-subtitle">Unified Operations Manual, Data-to-Report Architecture & Automated Dispatch SOP</div>
  <div class="meta-bar">
    <div class="meta-item"><strong>Target Platform:</strong> EasyEcom ERP & Slack</div>
    <div class="meta-item"><strong>Author:</strong> Lead Systems Architect</div>
    <div class="meta-item"><strong>Frequency:</strong> Daily at 08:30 AM IST</div>
    <div class="meta-item"><strong>Delivery Engine:</strong> GitHub Actions / Cron</div>
  </div>
</div>

<h2>Executive Summary & System Architecture</h2>
<p>
This walkthrough consolidates two core operational workflows into a single production pipeline:
</p>
<ol>
  <li><strong>Task 1 (Daily Report Making Process):</strong> Automatically extracting, cleaning, and transforming raw e-commerce transaction data (orders, shipments, cancellations, customer returns, courier RTOs, and inventory health) into structured executive KPI reports (HTML, Markdown, and Master Historical CSV).</li>
  <li><strong>Task 2 (Slack Automated Daily Broadcast):</strong> Formatting calculated metrics into an executive Slack Block Kit card, evaluating threshold anomalies, and automatically posting to a designated Slack channel (e.g. <code>#easycom-daily-kpi</code>) every morning at 08:30 AM IST.</li>
</ol>

<div class="diagram-box">
 ┌────────────────────────────────────────────────────────────────────────┐
 │                           EASYECOM ERP SOURCE                          │
 │   Option A: REST API (getAllOrdersV2, /inventory)                      │
 │   Option B: Manual CSV Export (Dashboard > Sales Details > Queue)      │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Raw Transactions
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                 TASK 1: DAILY REPORT MAKING PROCESS                    │
 │                                                                        │
 │  1. Ingestion & Normalization (Standardize disparate channel formats)   │
 │  2. Data Cleansing (Filter test orders, isolate cancellations/RTO)    │
 │  3. KPI Calculation Engine:                                            │
 │     • Gross GMV vs Net Realized Revenue                                │
 │     • Order Volume & Average Order Value (AOV)                         │
 │     • Fulfillment Rate & SLA Aging Backlog (>24h)                      │
 │     • Channel Breakdown (Amazon, Flipkart, Shopify, QuickComm)        │
 │     • Returns & RTO %                                                  │
 │     • Stockout Alert (OOS SKUs)                                        │
 │  4. File Generation:                                                   │
 │     • Standalone Styled HTML Report (Print-to-PDF ready)               │
 │     • Executive Markdown Briefing                                      │
 │     • Master History CSV (Appended for BI & trend tracking)           │
 └───────────────────────────────────┬────────────────────────────────────┘
                                     │ Structured KPI Summary
                                     ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                   TASK 2: AUTOMATED SLACK POSTING                      │
 │                                                                        │
 │  1. Block Kit Layout Builder (KPI cards, emojis, status badges)        │
 │  2. Dynamic Threshold Checker (Flags 🟢 Healthy, 🟡 Attention, 🔴 Alert)│
 │  3. Dispatcher (Incoming Webhook / chat.postMessage)                   │
 │  4. Automation Trigger:                                                │
 │     • 100% Free Serverless GitHub Actions Cron (08:30 AM IST)          │
 │     • Or Local Mac/Linux Crontab                                       │
 └────────────────────────────────────────────────────────────────────────┘
</div>

<div class="page-break"></div>

<h2>Task 1: The Daily Report Making Process (Raw Data ➔ KPI Report)</h2>

<p>
The objective of the report making process is to ingest raw, unaggregated order records and output consistent, audited metrics.
</p>

<h3>1. Data Extraction Options</h3>
<ul>
  <li>
    <strong>Automated API Extraction (Primary):</strong>
    The system queries EasyEcom's <code>getAllOrdersV2</code> endpoint with query parameters:
    <code>start_date=YYYY-MM-DD 00:00:00</code> and <code>end_date=YYYY-MM-DD 23:59:59</code>.
    Stock health is pulled simultaneously via <code>GET /inventory/details</code>.
  </li>
  <li>
    <strong>Manual CSV Export (Fallback Mode):</strong>
    If API keys are pending or an offline audit is required:
    <ol>
      <li>Log in to <strong>EasyEcom Dashboard</strong>.</li>
      <li>Navigate to <strong>Analytics / Reports ➔ Sales Details</strong> (or Orders).</li>
      <li>Select the target date filter (e.g. Yesterday), check all warehouses, and click <strong>Submit</strong>.</li>
      <li>Click <strong>Queue Report</strong>, wait for the job to complete in the Export queue, and download the CSV.</li>
      <li>Run: <code>python run_daily_kpi.py --from-csv path/to/export.csv</code>.</li>
    </ol>
  </li>
</ul>

<h3>2. Data Cleaning & Standardization Logic</h3>
<p>
Different marketplaces (Amazon, Flipkart, Shopify, QuickCommerce) send varied status labels and column names. The <code>EasyEcomCsvLoader</code> and <code>EasyEcomClient</code> normalize these into consistent internal buckets:
</p>
<table>
  <thead>
    <tr>
      <th>Marketplace / Source Raw Status</th>
      <th>Canonical Bucket</th>
      <th>Impact on Metrics</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>Delivered</code>, <code>Completed</code></td>
      <td><strong>Delivered</strong></td>
      <td>Counts toward Fulfilled Orders and Realized Revenue.</td>
    </tr>
    <tr>
      <td><code>Shipped</code>, <code>Dispatched</code>, <code>Handover to Courier</code></td>
      <td><strong>Shipped</strong></td>
      <td>Counts toward Fulfilled Orders; tracked for courier TAT.</td>
    </tr>
    <tr>
      <td><code>In-Transit</code>, <code>Out for Delivery</code></td>
      <td><strong>In-Transit</strong></td>
      <td>Counts toward Fulfilled Orders.</td>
    </tr>
    <tr>
      <td><code>Pending</code>, <code>Allocated</code>, <code>Breached</code>, <code>Unfulfilled</code></td>
      <td><strong>Pending Dispatch</strong></td>
      <td>Flags operational delay if age exceeds SLA (e.g. &gt; 24h).</td>
    </tr>
    <tr>
      <td><code>Customer Return</code>, <code>Return Received</code></td>
      <td><strong>Customer Return</strong></td>
      <td>Deducted from Net Revenue; increments Return Rate.</td>
    </tr>
    <tr>
      <td><code>RTO</code>, <code>Courier Return</code>, <code>Undelivered Return</code></td>
      <td><strong>Courier RTO</strong></td>
      <td>Failed delivery attempt; deducted from Net Revenue.</td>
    </tr>
    <tr>
      <td><code>Cancelled</code>, <code>Void</code></td>
      <td><strong>Cancelled</strong></td>
      <td>Deducted from Valid Orders and Gross GMV.</td>
    </tr>
  </tbody>
</table>

<h3>3. Core KPI Mathematical Formulas</h3>
<table>
  <thead>
    <tr>
      <th>Metric Name</th>
      <th>Standard Mathematical Definition</th>
      <th>Business Interpretation</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Gross Sales (GMV)</strong></td>
      <td>$$\sum (\text{Item Amount} - \text{Discount} + \text{Taxes} + \text{Shipping})$$</td>
      <td>Total top-line transaction demand generated.</td>
    </tr>
    <tr>
      <td><strong>Net Realized Revenue</strong></td>
      <td>$$\text{Gross GMV} - \text{Cancelled Amount} - \text{Returned Amount}$$</td>
      <td>Realized top-line after cancellations and returns.</td>
    </tr>
    <tr>
      <td><strong>Average Order Value (AOV)</strong></td>
      <td>$$\frac{\text{Gross GMV}}{\text{Total Orders} - \text{Cancelled Orders}}$$</td>
      <td>Average customer expenditure per successful order.</td>
    </tr>
    <tr>
      <td><strong>Fulfillment Rate (%)</strong></td>
      <td>$$\frac{\text{Delivered} + \text{Shipped} + \text{In-Transit}}{\text{Valid Orders}} \times 100$$</td>
      <td>Warehouse processing efficiency. Benchmark: &ge; 85%.</td>
    </tr>
    <tr>
      <td><strong>Total Return / RTO Rate (%)</strong></td>
      <td>$$\frac{\text{Customer Returns} + \text{Courier RTO}}{\text{Total Fulfilled Orders}} \times 100$$</td>
      <td>Customer satisfaction & courier reliability indicator. Safe: &lt; 12%.</td>
    </tr>
    <tr>
      <td><strong>Channel Share (%)</strong></td>
      <td>$$\frac{\text{Channel Revenue}}{\text{Gross GMV}} \times 100$$</td>
      <td>Revenue dependency per marketplace (Amazon vs Shopify, etc.).</td>
    </tr>
  </tbody>
</table>

<div class="page-break"></div>

<h2>Task 2: Automated Slack Daily Morning Broadcast</h2>

<p>
Every morning at 08:30 AM IST, the automation transforms the computed metrics into an interactive Slack Block Kit card.
</p>

<h3>1. Interactive Slack Block Kit Layout Preview</h3>
<div class="slack-preview">
  <div class="slack-header">📊 Easycom Daily KPI Briefing <span class="badge-healthy">🟢 HEALTHY</span></div>
  <div class="slack-meta">📅 Period: 2026-09-20 | Source: EasyEcom ERP | Warehouse: All Hubs</div>
  
  <div class="slack-grid">
    <div class="slack-item">
      <div class="slack-item-label">💰 Gross Sales (GMV)</div>
      <div class="slack-item-val">₹1,864,433.47</div>
      <div class="slack-item-sub">Net Realized: ₹1,722,310.47</div>
    </div>
    <div class="slack-item">
      <div class="slack-item-label">📦 Orders & Volume</div>
      <div class="slack-item-val">630 Orders</div>
      <div class="slack-item-sub">785 Units (1.25 items/order)</div>
    </div>
    <div class="slack-item">
      <div class="slack-item-label">📈 Average Order Value</div>
      <div class="slack-item-val">₹3,061.47</div>
      <div class="slack-item-sub">Prepaid: 63.0% | COD: 37.0%</div>
    </div>
    <div class="slack-item">
      <div class="slack-item-label">🚚 Fulfillment Rate</div>
      <div class="slack-item-val" style="color: #15803d;">93.1%</div>
      <div class="slack-item-sub">567 Dispatched | 14 SLA Backlog</div>
    </div>
    <div class="slack-item">
      <div class="slack-item-label">↩️ Total Returns & RTO</div>
      <div class="slack-item-val">4.9% (28 Orders)</div>
      <div class="slack-item-sub">RTO: 13 | Cust Returns: 15</div>
    </div>
    <div class="slack-item">
      <div class="slack-item-label">🏭 Stockout Health</div>
      <div class="slack-item-val">12 OOS SKUs</div>
      <div class="slack-item-sub">34 Low Stock Alerts</div>
    </div>
  </div>

  <div style="font-size: 9pt; font-weight: 600; margin-top: 10px;">🛒 Sales Channel Breakdown:</div>
  <ul style="font-size: 8.5pt; margin-top: 4px;">
    <li><strong>Amazon India:</strong> 226 orders | ₹621,791.26 (33.4% Share)</li>
    <li><strong>Flipkart:</strong> 164 orders | ₹549,569.45 (29.5% Share)</li>
    <li><strong>Shopify (Direct Website):</strong> 114 orders | ₹327,211.22 (17.6% Share)</li>
    <li><strong>Myntra:</strong> 71 orders | ₹200,594.42 (10.8% Share)</li>
    <li><strong>Blinkit (QuickCommerce):</strong> 55 orders | ₹165,267.12 (8.9% Share)</li>
  </ul>
</div>

<div class="alert alert-warning">
  <strong>Dynamic Anomaly Alerting Rules</strong>
  If Fulfillment Rate drops below 85% or Returns/RTO exceed 12%, the Slack header changes to <code>🔴 CRITICAL</code> and inserts an explicit warning banner:
  <pre>⚠️ Fulfillment Rate (78.6%) is below target (85.0%)
🚨 Total Returns & RTO (18.2%) exceeded safe threshold (12.0%)</pre>
</div>

<h3>2. Setting Up Slack Incoming Webhooks (Step-by-Step)</h3>
<ol>
  <li>Navigate to <strong><a href="https://api.slack.com/apps">api.slack.com/apps</a></strong> in your browser.</li>
  <li>Click <strong>Create New App</strong> ➔ Choose <strong>From scratch</strong>.</li>
  <li>Name the app <code>Easycom KPI Bot</code> and pick your workspace.</li>
  <li>Go to <strong>Incoming Webhooks</strong> in the left sidebar and toggle it to <strong>On</strong>.</li>
  <li>Click <strong>Add New Webhook to Workspace</strong>, choose your target channel (e.g. <code>#easycom-daily-kpi</code>), and click <strong>Allow</strong>.</li>
  <li>Copy the resulting Webhook URL:
    <pre>https://hooks.slack.com/services/YOUR_WORKSPACE_ID/YOUR_CHANNEL_ID/YOUR_WEBHOOK_TOKEN</pre>
  </li>
</ol>

<h3>3. EasyEcom API Credentials Setup</h3>
<ol>
  <li>Log in to your <strong>EasyEcom Primary Account</strong>.</li>
  <li>Navigate to <strong>Account Settings ➔ Change Credentials</strong>.</li>
  <li>Locate the <strong>X-API-KEY</strong> section and click <strong>Generate X-API-KEY</strong>.</li>
  <li>Visit <a href="https://api-docs.easyecom.io">api-docs.easyecom.io</a> to obtain your <code>Bearer JWT Token</code>.</li>
  <li>Save these credentials into your <code>.env</code> file:
    <pre>EASYECOM_API_KEY=your_x_api_key_here
EASYECOM_JWT_TOKEN=your_jwt_bearer_token_here
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...</pre>
  </li>
</ol>

<div class="page-break"></div>

<h2>Automated Scheduling & Deployment Architecture</h2>

<h3>Option A: GitHub Actions Cron (Recommended — 100% Free & Serverless)</h3>
<p>
The project includes a ready-to-use GitHub Actions workflow located at <code>.github/workflows/daily_kpi_cron.yml</code>.
</p>
<pre>name: Easycom Daily KPI Slack Automation

on:
  schedule:
    - cron: '0 3 * * *'  # 03:00 UTC = 08:30 AM IST Every Day
  workflow_dispatch:      # Allows 1-click manual trigger from GitHub UI

jobs:
  report_and_notify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run Daily Report & Post to Slack
        env:
          EASYECOM_API_KEY: ${{ secrets.EASYECOM_API_KEY }}
          EASYECOM_JWT_TOKEN: ${{ secrets.EASYECOM_JWT_TOKEN }}
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: python run_daily_kpi.py
      - name: Archive Reports
        uses: actions/upload-artifact@v4
        with:
          name: daily-reports
          path: reports/</pre>

<div class="alert alert-success">
  <strong>Benefits of GitHub Actions:</strong>
  Zero infrastructure maintenance, zero server hosting costs, automatic report archiving, and encrypted secrets storage.
</div>

<h3>Option B: Linux / macOS Crontab Schedule</h3>
<p>To run directly on an internal server or office machine:</p>
<pre>crontab -e
# Add this entry to run at 8:30 AM every morning:
30 8 * * * cd ./easycom-daily-kpi-slack && ~/.gemini/antigravity-ide/scratch/.shared-venv/bin/python run_daily_kpi.py >> cron.log 2>&1</pre>

---

<h2>Verification & Quick Reference Commands</h2>

<table>
  <thead>
    <tr>
      <th>Action</th>
      <th>Terminal Command</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>1. Test in Mock Mode (Dry-Run)</strong></td>
      <td><code>python run_daily_kpi.py --mock --dry-run</code></td>
    </tr>
    <tr>
      <td><strong>2. Convert Raw CSV Export to Report</strong></td>
      <td><code>python run_daily_kpi.py --from-csv sample_data/sample_easyecom_orders.csv --dry-run</code></td>
    </tr>
    <tr>
      <td><strong>3. Run Specific Historical Date</strong></td>
      <td><code>python run_daily_kpi.py --date 2026-09-15 --mock --dry-run</code></td>
    </tr>
    <tr>
      <td><strong>4. Execute Live Pipeline to Slack</strong></td>
      <td><code>python run_daily_kpi.py</code> (requires <code>.env</code> configured)</td>
    </tr>
  </tbody>
</table>

<br>
<hr>
<div style="text-align: center; font-size: 8.5pt; color: #64748b; margin-top: 20px;">
  Easycom Daily KPI & Slack Automation Suite • Internal Documentation • Confidential
</div>

</body>
</html>
"""

def generate_pdf():
    project_dir = "./easycom-daily-kpi-slack"
    artifact_dir = "~/.gemini/antigravity-ide/brain/11d50e2e-38a3-495d-a972-433ea5e06320"
    
    html_path = os.path.join(project_dir, "walkthrough_print.html")
    pdf_project_path = os.path.join(project_dir, "Easycom_Daily_KPI_Walkthrough.pdf")
    pdf_artifact_path = os.path.join(artifact_dir, "Easycom_Daily_KPI_Walkthrough.pdf")

    # 1. Write HTML
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    print(f"Written printable HTML template to {html_path}")

    # 2. Chrome binary
    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if not os.path.exists(chrome_bin):
        print(f"Error: Chrome binary not found at {chrome_bin}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        chrome_bin,
        "--headless",
        "--disable-gpu",
        "--run-all-compositor-stages-before-draw",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_project_path}",
        html_path,
    ]

    print(f"Rendering PDF with headless Chrome: {' '.join(cmd)}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error rendering PDF: {res.stderr}", file=sys.stderr)
        sys.exit(1)

    # Copy to artifact directory as well
    if os.path.exists(pdf_project_path):
        import shutil
        shutil.copy2(pdf_project_path, pdf_artifact_path)
        size_kb = os.path.getsize(pdf_project_path) / 1024
        print(f"Successfully generated PDF ({size_kb:.1f} KB)!")
        print(f"  - Project path:  {pdf_project_path}")
        print(f"  - Artifact path: {pdf_artifact_path}")
    else:
        print("Error: Output PDF file was not created.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    generate_pdf()
