"""EasyEcom API Client and Mock Data Generator.

Provides authentication and retrieval methods for Orders, Dispatches, Returns,
and Inventory metrics from EasyEcom (https://api-docs.easyecom.io).
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class EasyEcomClient:
    """Client for communicating with EasyEcom API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        base_url: str = "https://api.easyecom.io",
    ):
        self.api_key = api_key
        self.jwt_token = jwt_token
        self.base_url = base_url.rstrip("/")

    @property
    def headers(self) -> Dict[str, str]:
        """Headers required for EasyEcom API."""
        return {
            "x-api-key": self.api_key or "",
            "Authorization": f"Bearer {self.jwt_token or ''}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def fetch_orders(
        self, start_date: str, end_date: str, page: int = 1, limit: int = 250
    ) -> List[Dict[str, Any]]:
        """Fetch orders for a given date window (YYYY-MM-DD).

        Utilizes the getAllOrdersV2 endpoint.
        """
        if not self.api_key or not self.jwt_token:
            logger.warning("EasyEcom credentials not configured. Falling back to mock generator.")
            return self.generate_mock_orders(start_date)

        endpoint = f"{self.base_url}/orders/v2/getAllOrders"
        all_orders = []
        current_page = page

        # EasyEcom format: Y-m-d H:i:s
        start_datetime = f"{start_date} 00:00:00"
        end_datetime = f"{end_date} 23:59:59"

        params = {
            "start_date": start_datetime,
            "end_date": end_datetime,
            "limit": limit,
            "page": current_page,
        }

        try:
            logger.info("Fetching orders from EasyEcom API: %s (Page %d)", endpoint, current_page)
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=30,
            )

            if response.status_code == 401:
                raise PermissionError(
                    "EasyEcom 401 Unauthorized: Invalid X-API-Key or expired Bearer JWT Token. "
                    "Regenerate credentials in EasyEcom Account Settings > Change Credentials."
                )

            response.raise_for_status()
            data = response.json()

            # EasyEcom response structure typically contains 'data' or 'orders'
            orders_list = data.get("data", {}).get("orders", []) or data.get("orders", []) or []
            all_orders.extend(orders_list)

        except requests.RequestException as exc:
            logger.error("Error communicating with EasyEcom API: %s", exc)
            raise

        return all_orders

    def fetch_inventory_summary(self) -> Dict[str, Any]:
        """Fetch current stock health summary (Active SKUs, Out of Stock SKUs)."""
        if not self.api_key or not self.jwt_token:
            return {
                "total_skus": 1420,
                "in_stock_skus": 1408,
                "out_of_stock_skus": 12,
                "low_stock_skus": 34,
                "damaged_stock_units": 45,
            }

        endpoint = f"{self.base_url}/inventory/details"
        try:
            res = requests.get(endpoint, headers=self.headers, timeout=25)
            if res.ok:
                data = res.json().get("data", {})
                return data
        except Exception as e:
            logger.warning("Could not fetch inventory details: %s", e)

        return {"total_skus": 0, "out_of_stock_skus": 0}

    def generate_mock_orders(self, report_date: str, simulate_anomaly: bool = False) -> List[Dict[str, Any]]:
        """Generate realistic mock e-commerce transactions for Easycom.

        Covers multiple marketplaces, realistic pricing, statuses, and returns.
        When simulate_anomaly is True, injects warehouse operational bottlenecks
        causing fulfillment rate to drop below 85% and returns/SLA breaches to spike.
        """
        seed_val = int(report_date.replace("-", ""))
        if simulate_anomaly:
            seed_val += 999
        random.seed(seed_val)

        channels = [
            ("Amazon India", 0.38),
            ("Flipkart", 0.26),
            ("Shopify (Direct Website)", 0.18),
            ("Myntra", 0.10),
            ("Blinkit (QuickCommerce)", 0.08),
        ]

        channel_names = [c[0] for c in channels]
        channel_weights = [c[1] for c in channels]

        if simulate_anomaly:
            # Significant warehouse backlog and courier return surge
            statuses = [
                ("Delivered", 0.38),
                ("Shipped", 0.22),
                ("In-Transit", 0.08),
                ("Pending Dispatch (Breached SLA)", 0.17),
                ("Cancelled", 0.05),
                ("Customer Return", 0.06),
                ("RTO (Courier Return)", 0.04),
            ]
        else:
            statuses = [
                ("Delivered", 0.52),
                ("Shipped", 0.28),
                ("In-Transit", 0.08),
                ("Pending Dispatch (Breached SLA)", 0.04),
                ("Cancelled", 0.03),
                ("Customer Return", 0.03),
                ("RTO (Courier Return)", 0.02),
            ]
        status_names = [s[0] for s in statuses]
        status_weights = [s[1] for s in statuses]

        total_orders_count = random.randint(480, 720)
        mock_orders = []

        base_dt = datetime.strptime(report_date, "%Y-%m-%d")

        for i in range(1, total_orders_count + 1):
            channel = random.choices(channel_names, weights=channel_weights, k=1)[0]
            status = random.choices(status_names, weights=status_weights, k=1)[0]

            # Price modeling (e.g. ₹699 - ₹4,499)
            unit_price = round(random.uniform(699.0, 3499.0), 2)
            quantity = 1 if random.random() > 0.15 else random.randint(2, 3)
            discount = round(unit_price * quantity * (0.05 if random.random() > 0.5 else 0.0), 2)
            shipping = 0.0 if (unit_price * quantity) > 999 else 79.0
            tax = round((unit_price * quantity - discount) * 0.18, 2)
            total_amount = round((unit_price * quantity - discount) + tax + shipping, 2)

            hour = random.randint(0, 23)
            minute = random.randint(0, 59)
            order_time = base_dt.replace(hour=hour, minute=minute).strftime("%Y-%m-%d %H:%M:%S")

            order = {
                "order_id": f"EASY-{report_date.replace('-', '')}-{1000 + i}",
                "channel_order_id": f"CH-{channel[:3].upper()}-{10000 + i}",
                "channel_name": channel,
                "order_date": order_time,
                "status": status,
                "item_count": quantity,
                "subtotal": round(unit_price * quantity, 2),
                "discount": discount,
                "tax": tax,
                "shipping_fee": shipping,
                "total_amount": total_amount,
                "payment_mode": "Prepaid" if random.random() > 0.35 else "COD",
                "customer_city": random.choice(["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad", "Jaipur"]),
                "warehouse": random.choice(["WH-BHIWANDI-01", "WH-BENGALURU-02", "WH-GURUGRAM-01"]),
            }
            mock_orders.append(order)

        return mock_orders
