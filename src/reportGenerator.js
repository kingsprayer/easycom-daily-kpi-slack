/**
 * Easycom Daily KPI Report Generator for Node.js.
 *
 * Converts calculated KPI summaries into:
 * 1. Standalone executive HTML report (print-to-PDF ready).
 * 2. Clean Markdown report file.
 * 3. Historical master CSV tracking table (appends daily summary row).
 */

import fs from 'node:fs';
import path from 'node:path';

export class ReportGenerator {
  constructor(outputDir = 'reports') {
    this.outputDir = outputDir;
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  generateAllReports(kpis) {
    const reportDate = kpis.report_date || 'today';
    const paths = {};

    // 1. Generate Markdown
    const mdContent = this.generateMarkdown(kpis);
    const mdPath = path.join(this.outputDir, `daily_kpi_${reportDate}.md`);
    fs.writeFileSync(mdPath, mdContent, 'utf-8');
    paths.markdown = mdPath;

    // 2. Generate HTML
    const htmlContent = this.generateHtml(kpis);
    const htmlPath = path.join(this.outputDir, `daily_kpi_${reportDate}.html`);
    fs.writeFileSync(htmlPath, htmlContent, 'utf-8');
    paths.html = htmlPath;

    // 3. Append to master CSV
    const csvPath = this.appendToMasterCsv(kpis);
    paths.master_csv = csvPath;

    console.log('[ReportGenerator] Daily reports successfully written to:', paths);
    return paths;
  }

  generateMarkdown(kpis) {
    const fin = kpis.financials || {};
    const vol = kpis.volume || {};
    const ful = kpis.fulfillment || {};
    const ret = kpis.returns_and_cancellations || {};
    const pay = kpis.payments || {};
    const curr = fin.currency || '₹';

    const fmtNum = (n) => Number(n || 0).toLocaleString('en-IN');
    const fmtCur = (n) => `${curr}${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const channelRows = (kpis.channels || []).map(c =>
      `| ${c.channel} | ${fmtNum(c.orders)} | ${fmtCur(c.revenue)} | ${c.revenue_share_pct}% | ${fmtCur(c.aov)} |`
    ).join('\n');

    let alertSection = '';
    if (kpis.alerts && kpis.alerts.length > 0) {
      alertSection = `\n### ⚠️ Operational Health Alerts\n${kpis.alerts.map(a => `- **${a}**`).join('\n')}\n`;
    }

    return `# ${kpis.company_name || 'Easycom'} Daily Executive KPI Report
**Date:** \`${kpis.report_date}\` | **Health Status:** ${kpis.status_health || '🟢 HEALTHY'}
${alertSection}
---

## 1. Executive Summary
- **Gross Sales (GMV):** ${fmtCur(fin.gross_gmv)}
- **Net Realized Revenue:** ${fmtCur(fin.net_revenue)}
- **Total Orders:** ${fmtNum(vol.total_orders)} (${fmtNum(vol.total_units)} total units, ${vol.units_per_order} units/order)
- **Average Order Value (AOV):** ${fmtCur(fin.aov)}
- **Payment Split:** ${pay.prepaid_pct}% Prepaid | ${pay.cod_pct}% COD

---

## 2. Fulfillment & SLA Performance
- **Fulfillment Rate:** ${ful.fulfillment_rate_pct}% (${fmtNum(ful.fulfilled_count)} dispatched)
- **Pending Dispatch SLA Backlog:** ${ful.pending_dispatch_count} orders
- **Return & RTO Rate:** ${ret.return_rate_pct}% (${fmtNum(ret.total_returns_count)} orders: ${ret.rto_returns_count} RTO, ${ret.customer_returns_count} Customer Returns)
- **Cancellations:** ${ret.cancelled_count} orders (${ret.cancellation_rate_pct}%)

---

## 3. Marketplace & Sales Channel Breakdown
| Channel | Orders | Revenue | Revenue Share | Channel AOV |
| :--- | :--- | :--- | :--- | :--- |
${channelRows}

---

## 4. Inventory Health
- **Out of Stock SKUs:** ${kpis.inventory?.out_of_stock_skus || 0}
- **Low Stock SKUs:** ${kpis.inventory?.low_stock_skus || 0}
`;
  }

  generateHtml(kpis) {
    const fin = kpis.financials || {};
    const vol = kpis.volume || {};
    const ful = kpis.fulfillment || {};
    const ret = kpis.returns_and_cancellations || {};
    const pay = kpis.payments || {};
    const inv = kpis.inventory || {};
    const curr = fin.currency || '₹';

    const fmtNum = (n) => Number(n || 0).toLocaleString('en-IN');
    const fmtCur = (n) => `${curr}${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const channelRows = (kpis.channels || []).map(c => `
      <tr>
        <td><b>${c.channel}</b></td>
        <td>${fmtNum(c.orders)}</td>
        <td>${fmtCur(c.revenue)}</td>
        <td><span class="badge badge-info">${c.revenue_share_pct}%</span></td>
        <td>${fmtCur(c.aov)}</td>
      </tr>
    `).join('');

    const alertsHtml = (kpis.alerts && kpis.alerts.length > 0)
      ? `<div class="alert-box">
          <div class="alert-title">⚠️ Operational Action Required</div>
          <ul>${kpis.alerts.map(a => `<li>${a}</li>`).join('')}</ul>
        </div>`
      : '';

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${kpis.company_name || 'Easycom'} Executive KPI Report - ${kpis.report_date}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; color: #1e293b; padding: 32px; max-width: 960px; margin: 0 auto; line-height: 1.5; }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #e2e8f0; padding-bottom: 16px; margin-bottom: 24px; }
    .title h1 { font-size: 24px; margin: 0; color: #0f172a; }
    .title p { margin: 4px 0 0 0; color: #64748b; font-size: 14px; }
    .status-badge { padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 13px; background: #e0f2fe; color: #0369a1; }
    .status-badge.critical { background: #fee2e2; color: #b91c1c; }
    .status-badge.attention { background: #fef3c7; color: #b45309; }
    .alert-box { background: #fff1f2; border-left: 4px solid #f43f5e; padding: 14px 18px; border-radius: 6px; margin-bottom: 24px; }
    .alert-title { font-weight: 700; color: #e11d48; margin-bottom: 6px; font-size: 14px; }
    .alert-box ul { margin: 0; padding-left: 20px; font-size: 13px; color: #9f1239; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 28px; }
    .card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .card-label { font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
    .card-val { font-size: 22px; font-weight: 800; color: #0f172a; }
    .card-sub { font-size: 12px; color: #64748b; margin-top: 4px; }
    table { width: 100%; border-collapse: collapse; background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; margin-top: 12px; font-size: 13px; }
    th { background: #f1f5f9; padding: 10px 14px; text-align: left; font-weight: 600; color: #475569; }
    td { padding: 12px 14px; border-top: 1px solid #e2e8f0; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px; }
    .badge-info { background: #e0e7ff; color: #3730a3; }
    @media print { body { background: #fff; padding: 0; } .card, table { box-shadow: none; } }
  </style>
</head>
<body>
  <div class="header">
    <div class="title">
      <h1>${kpis.company_name || 'Easycom'} Executive KPI Report</h1>
      <p>Reporting Period: <b>${kpis.report_date}</b> | Data Source: EasyEcom ERP</p>
    </div>
    <div class="status-badge ${kpis.status_health?.includes('CRITICAL') ? 'critical' : (kpis.status_health?.includes('ATTENTION') ? 'attention' : '')}">
      ${kpis.status_health || '🟢 HEALTHY'}
    </div>
  </div>

  ${alertsHtml}

  <div class="grid">
    <div class="card">
      <div class="card-label">Gross GMV</div>
      <div class="card-val">${fmtCur(fin.gross_gmv)}</div>
      <div class="card-sub">Net: <b>${fmtCur(fin.net_revenue)}</b></div>
    </div>
    <div class="card">
      <div class="card-label">Total Orders</div>
      <div class="card-val">${fmtNum(vol.total_orders)}</div>
      <div class="card-sub">${fmtNum(vol.total_units)} units (${vol.units_per_order}/ord)</div>
    </div>
    <div class="card">
      <div class="card-label">Average Order Value</div>
      <div class="card-val">${fmtCur(fin.aov)}</div>
      <div class="card-sub">Prepaid ${pay.prepaid_pct}% | COD ${pay.cod_pct}%</div>
    </div>
    <div class="card">
      <div class="card-label">Fulfillment Rate</div>
      <div class="card-val">${ful.fulfillment_rate_pct}%</div>
      <div class="card-sub">${fmtNum(ful.fulfilled_count)} dispatched | SLA: ${ful.pending_dispatch_count}</div>
    </div>
    <div class="card">
      <div class="card-label">Returns & RTO %</div>
      <div class="card-val">${ret.return_rate_pct}%</div>
      <div class="card-sub">RTO: ${ret.rto_returns_count} | Cust: ${ret.customer_returns_count}</div>
    </div>
    <div class="card">
      <div class="card-label">Stockout Health</div>
      <div class="card-val">${inv.out_of_stock_skus || 0} OOS</div>
      <div class="card-sub">Low stock: ${inv.low_stock_skus || 0} SKUs</div>
    </div>
  </div>

  <h3 style="margin-bottom: 6px;">Marketplace Sales Breakdown</h3>
  <table>
    <thead>
      <tr>
        <th>Channel</th>
        <th>Orders</th>
        <th>Revenue</th>
        <th>Share</th>
        <th>AOV</th>
      </tr>
    </thead>
    <tbody>
      ${channelRows}
    </tbody>
  </table>
</body>
</html>`;
  }

  appendToMasterCsv(kpis) {
    const csvPath = path.join(this.outputDir, 'master_kpi_history.csv');
    const headers = [
      'report_date', 'company_name', 'gross_gmv', 'net_revenue', 'aov',
      'total_orders', 'total_units', 'fulfilled_orders', 'fulfillment_rate_pct',
      'pending_dispatch', 'total_returns', 'return_rate_pct', 'cancelled_orders',
      'cancellation_rate_pct', 'prepaid_pct', 'cod_pct', 'out_of_stock_skus', 'status_health'
    ];

    const fin = kpis.financials || {};
    const vol = kpis.volume || {};
    const ful = kpis.fulfillment || {};
    const ret = kpis.returns_and_cancellations || {};
    const pay = kpis.payments || {};
    const inv = kpis.inventory || {};

    const newRow = [
      kpis.report_date,
      kpis.company_name,
      fin.gross_gmv,
      fin.net_revenue,
      fin.aov,
      vol.total_orders,
      vol.total_units,
      ful.fulfilled_count,
      ful.fulfillment_rate_pct,
      ful.pending_dispatch_count,
      ret.total_returns_count,
      ret.return_rate_pct,
      ret.cancelled_count,
      ret.cancellation_rate_pct,
      pay.prepaid_pct,
      pay.cod_pct,
      inv.out_of_stock_skus,
      kpis.status_health
    ].join(',');

    if (!fs.existsSync(csvPath)) {
      fs.writeFileSync(csvPath, headers.join(',') + '\n' + newRow + '\n', 'utf-8');
    } else {
      fs.appendFileSync(csvPath, newRow + '\n', 'utf-8');
    }

    return csvPath;
  }
}
