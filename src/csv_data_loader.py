"""EasyEcom CSV Data Loader.

Ingests manual or scheduled CSV exports downloaded from the EasyEcom Portal
(e.g., from Dashboard -> Sales Details -> Queue Report).
Normalizes columns into standardized dictionary format for the KPI Engine.
"""

import csv
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class EasyEcomCsvLoader:
    """Parses and normalizes CSV exports from EasyEcom."""

    # Common aliases used in EasyEcom exports
    COLUMN_MAPPINGS = {
        "order_id": ["order_id", "easyecom_order_id", "order id", "reference_id"],
        "channel_name": ["channel", "channel_name", "marketplace", "source"],
        "order_date": ["order_date", "created_at", "order date", "invoice_date"],
        "status": ["status", "order_status", "current_status", "fulfillment_status"],
        "total_amount": ["total_amount", "invoice_amount", "grand_total", "total", "amount"],
        "item_count": ["item_count", "quantity", "qty", "items_count", "total_quantity"],
        "payment_mode": ["payment_mode", "payment_type", "payment_method", "prepaid/cod"],
        "warehouse": ["warehouse", "warehouse_name", "fulfillment_location"],
    }

    @classmethod
    def load_from_csv(cls, filepath: str) -> List[Dict[str, Any]]:
        """Load and normalize orders from an EasyEcom CSV export file."""
        logger.info("Reading EasyEcom daily export CSV: %s", filepath)
        orders = []

        with open(filepath, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = [h.strip().lower() for h in (reader.fieldnames or [])]

            # Build inverted mapping: header_name -> canonical_field
            header_map = {}
            for canonical, variations in cls.COLUMN_MAPPINGS.items():
                for header in headers:
                    if header in variations or any(v in header for v in variations):
                        header_map[header] = canonical
                        break

            for idx, raw_row in enumerate(reader, start=1):
                clean_row = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

                order = {
                    "order_id": clean_row.get(cls._find_header(clean_row, "order_id"), f"ROW-{idx}"),
                    "channel_name": clean_row.get(cls._find_header(clean_row, "channel_name"), "Direct/Other"),
                    "order_date": clean_row.get(cls._find_header(clean_row, "order_date"), ""),
                    "status": clean_row.get(cls._find_header(clean_row, "status"), "Delivered"),
                    "total_amount": cls._parse_float(clean_row.get(cls._find_header(clean_row, "total_amount"), 0.0)),
                    "item_count": cls._parse_int(clean_row.get(cls._find_header(clean_row, "item_count"), 1)),
                    "payment_mode": clean_row.get(cls._find_header(clean_row, "payment_mode"), "Prepaid"),
                    "warehouse": clean_row.get(cls._find_header(clean_row, "warehouse"), "Primary Warehouse"),
                }
                orders.append(order)

        logger.info("Successfully ingested and normalized %d orders from CSV", len(orders))
        return orders

    @classmethod
    def _find_header(cls, row: Dict[str, Any], canonical_key: str) -> str:
        variations = cls.COLUMN_MAPPINGS.get(canonical_key, [])
        for k in row.keys():
            if k in variations or any(v == k for v in variations):
                return k
        # Fallback partial matching
        for k in row.keys():
            if any(v in k for v in variations):
                return k
        return ""

    @staticmethod
    def _parse_float(value: Any) -> float:
        try:
            val_str = str(value).replace(",", "").replace("₹", "").replace("$", "").strip()
            return float(val_str) if val_str else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_int(value: Any) -> int:
        try:
            val_str = str(value).replace(",", "").strip()
            return int(float(val_str)) if val_str else 1
        except ValueError:
            return 1
