"""Slack Block Kit Formatter for Easycom Daily KPI Reports.

Builds interactive, richly formatted Block Kit payloads with metric cards,
alert banners, channel breakdowns, and action buttons.
"""

from typing import Any, Dict, List


class SlackFormatter:
    """Formats KPI summary dictionaries into Slack Block Kit JSON."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.slack_cfg = config.get("slack", {})
        self.currency = config.get("currency_symbol", "₹")

    def build_kpi_blocks(self, kpis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Construct Slack Block Kit layout array."""
        fin = kpis["financials"]
        vol = kpis["volume"]
        ful = kpis["fulfillment"]
        ret = kpis["returns_and_cancellations"]
        pay = kpis["payments"]
        curr = fin["currency"]
        date_str = kpis.get("report_date", "")
        company = kpis.get("company_name", "Easycom")
        health = kpis.get("status_health", "🟢 HEALTHY")

        blocks = []

        # 1. Header Block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📊 {company} Daily KPI Briefing",
                "emoji": True,
            },
        })

        # 2. Context metadata
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"📅 *Period:* `{date_str}` | *Status:* *{health}* | *Source:* EasyEcom ERP",
                }
            ],
        })

        blocks.append({"type": "divider"})

        # 3. Alert Callout (if any)
        if kpis.get("alerts"):
            alert_text = "\n".join(kpis["alerts"])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*⚠️ Operational Action Required:*\n```{alert_text}```",
                },
            })

        # 4. Core Metrics Grid (Section with 4-8 fields)
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*💰 Gross Sales (GMV):*\n>{curr}{fin['gross_gmv']:,.2f}\n>_Net: {curr}{fin['net_revenue']:,.2f}_",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*📦 Orders & Volume:*\n>{vol['total_orders']:,} Orders\n>_{vol['total_units']:,} Units ({vol['units_per_order']} / order)_",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*📈 Average Order Value:*\n>{curr}{fin['aov']:,.2f}",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*🚚 Fulfillment Rate:*\n>*{ful['fulfillment_rate_pct']}%* ({ful['fulfilled_count']:,} dispatched)",
                },
            ],
        })

        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*↩️ Total Returns & RTO:*\n>*{ret['return_rate_pct']}%* ({ret['total_returns_count']:,} returns)\n>_RTO: {ret['rto_returns_count']} | Cust: {ret['customer_returns_count']}_",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*⏳ SLA Aging & Backlog:*\n>{ful['pending_dispatch_count']} orders pending\n>_Cancellations: {ret['cancelled_count']} ({ret['cancellation_rate_pct']}%)_",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*💳 Payment Split:*\n>{pay['prepaid_pct']}% Prepaid | {pay['cod_pct']}% COD",
                },
                {
                    "type": "mrkdwn",
                    "text": f"*🏭 Stockout Health:*\n>{kpis['inventory']['out_of_stock_skus']} OOS SKUs ({kpis['inventory']['low_stock_skus']} low stock)",
                },
            ],
        })

        blocks.append({"type": "divider"})

        # 5. Top Channel Breakdown
        channel_lines = []
        for c in kpis.get("channels", [])[:5]:
            channel_lines.append(
                f"• *{c['channel']}*: {c['orders']:,} orders | {curr}{c['revenue']:,.2f} (*{c['revenue_share_pct']}%*)"
            )

        channel_text = "\n".join(channel_lines) if channel_lines else "No channel activity recorded."
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*🛒 Sales Channel Performance:*\n{channel_text}",
            },
        })

        # 6. Action Button / EasyEcom link
        dashboard_url = self.slack_cfg.get("dashboard_url", "https://dashboard.easyecom.io")
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Open EasyEcom Dashboard ↗",
                        "emoji": True,
                    },
                    "url": dashboard_url,
                    "style": "primary",
                }
            ],
        })

        return blocks
