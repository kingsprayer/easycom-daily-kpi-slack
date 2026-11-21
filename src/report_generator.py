"""Easycom Daily KPI Report Generator.

Converts calculated KPI summaries into:
1. Standalone executive HTML report (with responsive CSS styling, ready for viewing or PDF export).
2. Clean Markdown report file.
3. Historical master CSV tracking table (appends daily summary row).
"""

import csv
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates file artifacts from KPI summary data."""

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_all_reports(self, kpis: Dict[str, Any]) -> Dict[str, str]:
        """Generate HTML, Markdown, and update master CSV."""
        report_date = kpis.get("report_date", "today")
        paths = {}

        # 1. Generate Markdown
        md_content = self.generate_markdown(kpis)
        md_path = os.path.join(self.output_dir, f"daily_kpi_{report_date}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        paths["markdown"] = md_path

        # 2. Generate HTML
        html_content = self.generate_html(kpis)
        html_path = os.path.join(self.output_dir, f"daily_kpi_{report_date}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        paths["html"] = html_path

        # 3. Append to master CSV
        csv_path = self.append_to_master_csv(kpis)
        paths["master_csv"] = csv_path

        logger.info("Daily reports successfully written to: %s", paths)
        return paths

    def generate_markdown(self, kpis: Dict[str, Any]) -> str:
        fin = kpis["financials"]
        vol = kpis["volume"]
        ful = kpis["fulfillment"]
        ret = kpis["returns_and_cancellations"]
        pay = kpis["payments"]
        curr = fin["currency"]

        channel_rows = "\n".join(
            f"| {c['channel']} | {c['orders']:,} | {curr}{c['revenue']:,.2f} | {c['revenue_share_pct']}% | {curr}{c['aov']:,.2f} |"
            for c in kpis.get("channels", [])
        )

        alerts_section = ""
        if kpis.get("alerts"):
            alerts_section = "### 🚨 Operational Warnings & Alerts\n" + "\n".join(f"- {a}" for a in kpis["alerts"]) + "\n\n"

        return f"""# {kpis['company_name']} - Daily Performance & KPI Report
**Report Date:** {kpis['report_date']} | **System Health:** {kpis['status_health']}

---

## 1. Executive Summary & Financials
- **Gross GMV:** {curr}{fin['gross_gmv']:,.2f}
- **Net Realized Revenue:** {curr}{fin['net_revenue']:,.2f}
- **Average Order Value (AOV):** {curr}{fin['aov']:,.2f}
- **Total Orders Received:** {vol['total_orders']:,}
- **Total Units Sold:** {vol['total_units']:,} (Avg {vol['units_per_order']} units/order)

---

{alerts_section}## 2. Operations & Fulfillment
- **Fulfillment Rate:** {ful['fulfillment_rate_pct']}%
- **Fulfilled Orders:** {ful['fulfilled_count']:,} (Delivered: {ful.get('delivered_count', 0):,}, Shipped: {ful.get('shipped_count', 0):,}, In-Transit: {ful.get('in_transit_count', 0):,})
- **Pending Dispatch (Backlog):** {ful['pending_dispatch_count']:,} orders

---

## 3. Returns, Cancellations & RTO
- **Total Return / RTO Rate:** {ret['return_rate_pct']}%
- **Customer Returns:** {ret['customer_returns_count']:,}
- **Courier RTOs:** {ret['rto_returns_count']:,}
- **Cancellations:** {ret['cancelled_count']:,} ({ret['cancellation_rate_pct']}%)

---

## 4. Sales Channel Breakdown
| Channel | Orders | Revenue | Rev Share | AOV |
| :--- | :--- | :--- | :--- | :--- |
{channel_rows}

---

## 5. Payment Split & Inventory Health
- **Prepaid vs COD:** {pay['prepaid_pct']}% Prepaid ({pay['prepaid_count']:,} orders) vs {pay['cod_pct']}% COD ({pay['cod_count']:,} orders)
- **Out of Stock SKUs:** {kpis['inventory']['out_of_stock_skus']}
- **Low Stock SKUs:** {kpis['inventory']['low_stock_skus']}
"""

    def generate_html(self, kpis: Dict[str, Any]) -> str:
        fin = kpis["financials"]
        vol = kpis["volume"]
        ful = kpis["fulfillment"]
        ret = kpis["returns_and_cancellations"]
        pay = kpis["payments"]
        curr = fin["currency"]

        channel_tr = "".join(
            f"""<tr>
                <td><strong>{c['channel']}</strong></td>
                <td style="text-align: right;">{c['orders']:,}</td>
                <td style="text-align: right;">{curr}{c['revenue']:,.2f}</td>
                <td style="text-align: right;"><span class="badge">{c['revenue_share_pct']}%</span></td>
                <td style="text-align: right;">{curr}{c['aov']:,.2f}</td>
            </tr>"""
            for c in kpis.get("channels", [])
        )

        alerts_html = ""
        if kpis.get("alerts"):
            alerts_html = "<div class='alert-box'><h3>⚠️ Operational Alerts</h3><ul>" + "".join(
                f"<li>{a}</li>" for a in kpis["alerts"]
            ) + "</ul></div>"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{kpis['company_name']} - Daily KPI Report ({kpis['report_date']})</title>
<style>
  :root {{
    --bg: #0f172a;
    --card-bg: #1e293b;
    --border: #334155;
    --text: #f8fafc;
    --text-muted: #94a3b8;
    --primary: #38bdf8;
    --success: #34d399;
    --warning: #fbbf24;
    --danger: #f87171;
  }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    margin: 0;
    padding: 32px 20px;
  }}
  .container {{
    max-width: 1000px;
    margin: 0 auto;
  }}
  .header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px;
    margin-bottom: 24px;
  }}
  .title {{
    margin: 0;
    font-size: 26px;
    font-weight: 700;
  }}
  .subtitle {{
    color: var(--text-muted);
    font-size: 14px;
    margin-top: 4px;
  }}
  .health-pill {{
    padding: 6px 14px;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 13px;
    background: #1e3a5f;
    color: var(--primary);
    border: 1px solid #2563eb;
  }}
  .grid-4 {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
  }}
  .card-label {{
    color: var(--text-muted);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  .card-value {{
    font-size: 26px;
    font-weight: 700;
    margin: 8px 0 4px 0;
    color: #fff;
  }}
  .card-sub {{
    font-size: 13px;
    color: var(--text-muted);
  }}
  .alert-box {{
    background: rgba(248, 113, 113, 0.1);
    border: 1px solid var(--danger);
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 24px;
    color: #fca5a5;
  }}
  .alert-box h3 {{
    margin: 0 0 8px 0;
    font-size: 16px;
  }}
  .alert-box ul {{
    margin: 0;
    padding-left: 20px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
  }}
  th, td {{
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
  }}
  th {{
    text-align: left;
    color: var(--text-muted);
    font-weight: 600;
    background: rgba(255, 255, 255, 0.02);
  }}
  .badge {{
    background: rgba(56, 189, 248, 0.15);
    color: var(--primary);
    padding: 3px 8px;
    border-radius: 4px;
    font-size: 12px;
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div>
      <h1 class="title">{kpis['company_name']} Daily KPI Briefing</h1>
      <div class="subtitle">Generated for: {kpis['report_date']} | Source: EasyEcom Integration</div>
    </div>
    <div class="health-pill">{kpis['status_health']}</div>
  </div>

  {alerts_html}

  <div class="grid-4">
    <div class="card">
      <div class="card-label">Gross GMV</div>
      <div class="card-value">{curr}{fin['gross_gmv']:,.2f}</div>
      <div class="card-sub">Net: {curr}{fin['net_revenue']:,.2f}</div>
    </div>
    <div class="card">
      <div class="card-label">Total Orders</div>
      <div class="card-value">{vol['total_orders']:,}</div>
      <div class="card-sub">Units: {vol['total_units']:,}</div>
    </div>
    <div class="card">
      <div class="card-label">Average Order Value</div>
      <div class="card-value">{curr}{fin['aov']:,.2f}</div>
      <div class="card-sub">{vol['units_per_order']} items/order</div>
    </div>
    <div class="card">
      <div class="card-label">Fulfillment Rate</div>
      <div class="card-value" style="color: {'var(--success)' if ful['fulfillment_rate_pct'] >= 85 else 'var(--warning)'}">{ful['fulfillment_rate_pct']}%</div>
      <div class="card-sub">{ful['fulfilled_count']:,} dispatched</div>
    </div>
  </div>

  <div class="grid-4" style="grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));">
    <div class="card">
      <div class="card-label">Quality & Returns</div>
      <div style="margin-top: 14px; font-size: 14px; line-height: 1.8;">
        <div><strong>Total Return/RTO Rate:</strong> {ret['return_rate_pct']}%</div>
        <div>Customer Returns: {ret['customer_returns_count']:,}</div>
        <div>Courier RTOs: {ret['rto_returns_count']:,}</div>
        <div>Order Cancellations: {ret['cancelled_count']:,} ({ret['cancellation_rate_pct']}%)</div>
      </div>
    </div>

    <div class="card">
      <div class="card-label">Inventory & Payments</div>
      <div style="margin-top: 14px; font-size: 14px; line-height: 1.8;">
        <div><strong>Payment Split:</strong> {pay['prepaid_pct']}% Prepaid / {pay['cod_pct']}% COD</div>
        <div>Out of Stock SKUs: <span style="color: {'var(--danger)' if kpis['inventory']['out_of_stock_skus'] > 0 else 'var(--success)'}; font-weight: bold;">{kpis['inventory']['out_of_stock_skus']}</span></div>
        <div>Low Stock Alert SKUs: {kpis['inventory']['low_stock_skus']}</div>
        <div>Pending SLA Dispatch: {ful['pending_dispatch_count']} orders</div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top: 24px;">
    <div class="card-label">Marketplace & Sales Channel Performance</div>
    <table>
      <thead>
        <tr>
          <th>Sales Channel</th>
          <th style="text-align: right;">Orders</th>
          <th style="text-align: right;">Gross Sales</th>
          <th style="text-align: right;">Revenue Share</th>
          <th style="text-align: right;">Channel AOV</th>
        </tr>
      </thead>
      <tbody>
        {channel_tr}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>
"""

    def append_to_master_csv(self, kpis: Dict[str, Any]) -> str:
        """Append KPI row to historical master CSV."""
        csv_path = os.path.join(self.output_dir, "master_kpi_history.csv")
        file_exists = os.path.exists(csv_path)

        headers = [
            "report_date",
            "company_name",
            "gross_gmv",
            "net_revenue",
            "aov",
            "total_orders",
            "total_units",
            "fulfilled_orders",
            "fulfillment_rate_pct",
            "pending_dispatch",
            "total_returns",
            "return_rate_pct",
            "cancelled_orders",
            "cancellation_rate_pct",
            "prepaid_pct",
            "cod_pct",
            "out_of_stock_skus",
            "status_health",
        ]

        fin = kpis["financials"]
        vol = kpis["volume"]
        ful = kpis["fulfillment"]
        ret = kpis["returns_and_cancellations"]
        pay = kpis["payments"]

        row = [
            kpis["report_date"],
            kpis["company_name"],
            fin["gross_gmv"],
            fin["net_revenue"],
            fin["aov"],
            vol["total_orders"],
            vol["total_units"],
            ful["fulfilled_count"],
            ful["fulfillment_rate_pct"],
            ful["pending_dispatch_count"],
            ret["total_returns_count"],
            ret["return_rate_pct"],
            ret["cancelled_count"],
            ret["cancellation_rate_pct"],
            pay["prepaid_pct"],
            pay["cod_pct"],
            kpis["inventory"]["out_of_stock_skus"],
            kpis["status_health"],
        ]

        with open(csv_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)

        return csv_path
