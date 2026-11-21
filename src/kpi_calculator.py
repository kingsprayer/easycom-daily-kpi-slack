"""Easycom KPI Calculation and Aggregation Engine.

Processes raw normalized transaction and inventory records into high-level
business KPIs with status classifications and health alerts.
"""

from typing import Any, Dict, List, Optional


class KpiCalculator:
    """Calculates e-commerce KPIs from raw EasyEcom orders."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = config.get("alert_thresholds", {})
        self.currency = config.get("currency_symbol", "₹")

    def compute_daily_kpis(
        self, orders: List[Dict[str, Any]], inventory: Optional[Dict[str, Any]] = None, report_date: str = ""
    ) -> Dict[str, Any]:
        """Transform raw order records into a comprehensive KPI summary dictionary."""
        if not orders:
            return self._empty_kpi_payload(report_date)

        total_orders = len(orders)
        total_units = sum(o.get("item_count", 1) for o in orders)
        gross_gmv = sum(o.get("total_amount", 0.0) for o in orders)

        # Status bucket categorization
        delivered_orders = []
        shipped_orders = []
        in_transit_orders = []
        pending_orders = []
        cancelled_orders = []
        customer_returns = []
        rto_returns = []

        channel_stats: Dict[str, Dict[str, Any]] = {}
        payment_stats = {"Prepaid": 0, "COD": 0}

        for order in orders:
            status = order.get("status", "").lower()
            ch = order.get("channel_name", "Other")
            amt = order.get("total_amount", 0.0)
            pay_mode = order.get("payment_mode", "Prepaid")

            # Payment split
            if "cod" in pay_mode.lower():
                payment_stats["COD"] += 1
            else:
                payment_stats["Prepaid"] += 1

            # Channel aggregation
            if ch not in channel_stats:
                channel_stats[ch] = {"orders": 0, "revenue": 0.0, "units": 0}
            channel_stats[ch]["orders"] += 1
            channel_stats[ch]["revenue"] += amt
            channel_stats[ch]["units"] += order.get("item_count", 1)

            # Status classification
            if "delivered" in status:
                delivered_orders.append(order)
            elif "shipped" in status:
                shipped_orders.append(order)
            elif "transit" in status:
                in_transit_orders.append(order)
            elif "pending" in status or "breach" in status or "unfulfilled" in status:
                pending_orders.append(order)
            elif "cancel" in status:
                cancelled_orders.append(order)
            elif "rto" in status:
                rto_returns.append(order)
            elif "return" in status:
                customer_returns.append(order)
            else:
                # Default open status
                shipped_orders.append(order)

        # Calculations
        fulfilled_count = len(delivered_orders) + len(shipped_orders) + len(in_transit_orders)
        valid_orders_count = total_orders - len(cancelled_orders)
        fulfillment_rate = (fulfilled_count / valid_orders_count * 100) if valid_orders_count > 0 else 0.0

        total_returns_count = len(customer_returns) + len(rto_returns)
        return_rate = (total_returns_count / fulfilled_count * 100) if fulfilled_count > 0 else 0.0
        cancellation_rate = (len(cancelled_orders) / total_orders * 100) if total_orders > 0 else 0.0

        # Net Realized Revenue (GMV minus cancellations and returns)
        cancelled_rev = sum(o.get("total_amount", 0.0) for o in cancelled_orders)
        returned_rev = sum(o.get("total_amount", 0.0) for o in customer_returns + rto_returns)
        net_revenue = gross_gmv - cancelled_rev - returned_rev

        aov = (gross_gmv / valid_orders_count) if valid_orders_count > 0 else 0.0
        units_per_order = (total_units / total_orders) if total_orders > 0 else 1.0

        # Channel formatting and sorting by revenue
        channel_list = []
        for ch_name, data in channel_stats.items():
            share_pct = (data["revenue"] / gross_gmv * 100) if gross_gmv > 0 else 0.0
            channel_list.append({
                "channel": ch_name,
                "orders": data["orders"],
                "revenue": round(data["revenue"], 2),
                "revenue_share_pct": round(share_pct, 1),
                "aov": round(data["revenue"] / data["orders"], 2) if data["orders"] > 0 else 0.0,
            })
        channel_list.sort(key=lambda x: x["revenue"], reverse=True)

        # Inventory statistics
        inv = inventory or {}
        oos_skus = inv.get("out_of_stock_skus", 0)
        low_stock_skus = inv.get("low_stock_skus", 0)

        # Alert evaluation
        alerts = []
        status_health = "🟢 HEALTHY"

        min_fulf = self.thresholds.get("min_fulfillment_rate_pct", 85.0)
        max_ret = self.thresholds.get("max_return_rate_pct", 12.0)
        max_sla = self.thresholds.get("max_sla_breach_count", 25)
        max_oos = self.thresholds.get("max_oos_skus_count", 15)

        if fulfillment_rate < min_fulf:
            alerts.append(f"⚠️ Fulfillment Rate ({fulfillment_rate:.1f}%) is below target ({min_fulf}%)")
            status_health = "🔴 CRITICAL" if fulfillment_rate < (min_fulf - 5.0) else "🟡 ATTENTION NEEDED"

        if return_rate > max_ret:
            alerts.append(f"🚨 Total Returns & RTO ({return_rate:.1f}%) exceeded safe threshold ({max_ret}%)")
            status_health = "🔴 CRITICAL"

        sla_backlog_count = len(pending_orders)
        if sla_backlog_count > max_sla:
            alerts.append(f"⏰ SLA Aging: {sla_backlog_count} orders pending dispatch (Breached target {max_sla})")
            if status_health != "🔴 CRITICAL":
                status_health = "🟡 ATTENTION NEEDED"

        if oos_skus > max_oos:
            alerts.append(f"📦 Inventory Warning: {oos_skus} SKUs are currently Out of Stock")

        return {
            "report_date": report_date,
            "company_name": self.config.get("company_name", "Easycom"),
            "status_health": status_health,
            "financials": {
                "gross_gmv": round(gross_gmv, 2),
                "net_revenue": round(net_revenue, 2),
                "aov": round(aov, 2),
                "currency": self.currency,
            },
            "volume": {
                "total_orders": total_orders,
                "valid_orders": valid_orders_count,
                "total_units": total_units,
                "units_per_order": round(units_per_order, 2),
            },
            "fulfillment": {
                "fulfilled_count": fulfilled_count,
                "fulfillment_rate_pct": round(fulfillment_rate, 1),
                "delivered_count": len(delivered_orders),
                "shipped_count": len(shipped_orders),
                "in_transit_count": len(in_transit_orders),
                "pending_dispatch_count": sla_backlog_count,
            },
            "returns_and_cancellations": {
                "customer_returns_count": len(customer_returns),
                "rto_returns_count": len(rto_returns),
                "total_returns_count": total_returns_count,
                "return_rate_pct": round(return_rate, 1),
                "cancelled_count": len(cancelled_orders),
                "cancellation_rate_pct": round(cancellation_rate, 1),
            },
            "channels": channel_list,
            "payments": {
                "prepaid_count": payment_stats["Prepaid"],
                "prepaid_pct": round((payment_stats["Prepaid"] / total_orders * 100), 1) if total_orders else 0.0,
                "cod_count": payment_stats["COD"],
                "cod_pct": round((payment_stats["COD"] / total_orders * 100), 1) if total_orders else 0.0,
            },
            "inventory": {
                "out_of_stock_skus": oos_skus,
                "low_stock_skus": low_stock_skus,
            },
            "alerts": alerts,
        }

    def _empty_kpi_payload(self, report_date: str) -> Dict[str, Any]:
        return {
            "report_date": report_date,
            "company_name": self.config.get("company_name", "Easycom"),
            "status_health": "⚪ NO DATA",
            "financials": {"gross_gmv": 0.0, "net_revenue": 0.0, "aov": 0.0, "currency": self.currency},
            "volume": {"total_orders": 0, "valid_orders": 0, "total_units": 0, "units_per_order": 0.0},
            "fulfillment": {"fulfilled_count": 0, "fulfillment_rate_pct": 0.0, "pending_dispatch_count": 0},
            "returns_and_cancellations": {"total_returns_count": 0, "return_rate_pct": 0.0, "cancelled_count": 0},
            "channels": [],
            "payments": {"prepaid_pct": 0.0, "cod_pct": 0.0},
            "inventory": {"out_of_stock_skus": 0, "low_stock_skus": 0},
            "alerts": ["No transaction records were received for this date."],
        }
