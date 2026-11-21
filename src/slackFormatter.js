/**
 * Slack Block Kit Formatter for Easycom Daily KPI Reports (Node.js).
 */

export class SlackFormatter {
  constructor(config = {}) {
    this.config = config;
    this.currency = config.currency_symbol || '₹';
  }

  buildKpiBlocks(kpis) {
    const fin = kpis.financials || {};
    const vol = kpis.volume || {};
    const ful = kpis.fulfillment || {};
    const ret = kpis.returns_and_cancellations || {};
    const curr = fin.currency || this.currency;
    const dateStr = kpis.report_date || '';
    const company = kpis.company_name || 'Easycom';
    const health = kpis.status_health || '🟢 HEALTHY';

    const fmtNum = (n) => Number(n || 0).toLocaleString('en-IN');
    const fmtCur = (n) => `${curr}${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    const blocks = [];

    // 1. Header Block
    blocks.push({
      type: 'header',
      text: {
        type: 'plain_text',
        text: `📊 ${company} Daily KPI Briefing`,
        emoji: true
      }
    });

    // 2. Context metadata
    blocks.push({
      type: 'context',
      elements: [
        {
          type: 'mrkdwn',
          text: `📅 *Period:* \`${dateStr}\` | *Status:* *${health}* | *Source:* EasyEcom ERP`
        }
      ]
    });

    blocks.push({ type: 'divider' });

    // 3. Alert Callout (if any)
    if (kpis.alerts && kpis.alerts.length > 0) {
      blocks.push({
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*⚠️ Operational Action Required:*\n\`\`\`${kpis.alerts.join('\n')}\`\`\``
        }
      });
    }

    // 4. Core Metrics Grid (2 Columns)
    blocks.push({
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*💰 Gross Sales (GMV):*\n>${fmtCur(fin.gross_gmv)}\n>_Net: ${fmtCur(fin.net_revenue)}_`
        },
        {
          type: 'mrkdwn',
          text: `*📦 Orders & Volume:*\n>${fmtNum(vol.total_orders)} Orders\n>_${fmtNum(vol.total_units)} Units (${vol.units_per_order} / order)_`
        },
        {
          type: 'mrkdwn',
          text: `*📈 Average Order Value:*\n>${fmtCur(fin.aov)}`
        },
        {
          type: 'mrkdwn',
          text: `*🚚 Fulfillment Rate:*\n>*${ful.fulfillment_rate_pct}%* (${fmtNum(ful.fulfilled_count)} dispatched)`
        }
      ]
    });

    blocks.push({
      type: 'section',
      fields: [
        {
          type: 'mrkdwn',
          text: `*↩️ Total Returns & RTO:*\n>*${ret.return_rate_pct}%* (${fmtNum(ret.total_returns_count)} returns)\n>_RTO: ${ret.rto_returns_count} | Cust: ${ret.customer_returns_count}_`
        },
        {
          type: 'mrkdwn',
          text: `*⏳ SLA Aging & Backlog:*\n>${ful.pending_dispatch_count} orders pending\n>_Cancellations: ${ret.cancelled_count} (${ret.cancellation_rate_pct}%)_`
        },
        {
          type: 'mrkdwn',
          text: `*💳 Payment Split:*\n>${kpis.payments?.prepaid_pct || 0}% Prepaid | ${kpis.payments?.cod_pct || 0}% COD`
        },
        {
          type: 'mrkdwn',
          text: `*🏭 Stockout Health:*\n>${kpis.inventory?.out_of_stock_skus || 0} OOS SKUs (${kpis.inventory?.low_stock_skus || 0} low stock)`
        }
      ]
    });

    blocks.push({ type: 'divider' });

    // 5. Channels List
    if (kpis.channels && kpis.channels.length > 0) {
      const channelLines = kpis.channels.map(c => `• *${c.channel}*: ${c.orders} orders | ${fmtCur(c.revenue)} (*${c.revenue_share_pct}%*)`).join('\n');
      blocks.push({
        type: 'section',
        text: {
          type: 'mrkdwn',
          text: `*🛒 Sales Channel Performance:*\n${channelLines}`
        }
      });
    }

    // 6. Action Button
    blocks.push({
      type: 'actions',
      elements: [
        {
          type: 'button',
          text: {
            type: 'plain_text',
            text: 'Open EasyEcom Dashboard ↗',
            emoji: true
          },
          url: 'https://dashboard.easyecom.io',
          style: 'primary'
        }
      ]
    });

    return blocks;
  }
}
