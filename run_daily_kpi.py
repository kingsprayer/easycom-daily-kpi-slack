#!/usr/bin/env python3
"""Easycom Daily KPI Pipeline & Slack Reporter.

Orchestrates:
1. Data Extraction (EasyEcom API or manual CSV export)
2. KPI Calculation & Business Health Evaluation
3. Report Generation (HTML, Markdown, Master CSV)
4. Slack Executive Notification Delivery
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.csv_data_loader import EasyEcomCsvLoader
from src.easyecom_client import EasyEcomClient
from src.kpi_calculator import KpiCalculator
from src.report_generator import ReportGenerator
from src.slack_formatter import SlackFormatter
from src.slack_notifier import SlackNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("easycom_daily_kpi")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Easycom Daily KPI & Slack Automation Suite")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Report date in YYYY-MM-DD format (defaults to yesterday)",
    )
    parser.add_argument(
        "--from-csv",
        type=str,
        default=None,
        help="Path to an EasyEcom raw export CSV file to run the daily report making process",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use synthetic e-commerce data for testing without live credentials",
    )
    parser.add_argument(
        "--simulate-anomaly",
        action="store_true",
        help="Simulate severe fulfillment backlogs and return spikes to trigger critical alerts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate local reports and Slack Block Kit payload without dispatching to Slack",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to configuration JSON file (default: config.json)",
    )
    return parser.parse_args()


def load_config(config_path: str) -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    logger.warning("Config file %s not found. Using defaults.", config_path)
    return {
        "company_name": "Easycom",
        "currency_symbol": "₹",
        "alert_thresholds": {
            "min_fulfillment_rate_pct": 85.0,
            "max_return_rate_pct": 12.0,
            "max_sla_breach_count": 25,
            "max_oos_skus_count": 15,
        },
        "reporting": {"output_dir": "reports"},
    }


def run_pipeline(
    report_date: Optional[str] = None,
    from_csv: Optional[str] = None,
    mock: bool = True,
    simulate_anomaly: bool = False,
    dry_run: bool = True,
    config_path: str = "config.json",
) -> dict:
    """Execute the end-to-end KPI extraction, calculation, and reporting pipeline."""
    load_dotenv()
    config = load_config(config_path)
    output_dir = config.get("reporting", {}).get("output_dir", "reports")
    os.makedirs(output_dir, exist_ok=True)

    if not report_date:
        report_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    logger.info("========================================================")
    logger.info(" Easycom Daily KPI Reporting & Automation Pipeline")
    logger.info(" Reporting Target Date: %s | Anomaly Simulation: %s", report_date, simulate_anomaly)
    logger.info("========================================================")

    # 1. DATA EXTRACTION
    orders = []
    inventory = {}

    if from_csv:
        logger.info("Mode: Converting manual EasyEcom CSV export into KPI Report...")
        if not os.path.exists(from_csv):
            logger.error("Specified CSV file does not exist: %s", from_csv)
            raise FileNotFoundError(f"Specified CSV file does not exist: {from_csv}")
        orders = EasyEcomCsvLoader.load_from_csv(from_csv)
        inventory = {"out_of_stock_skus": 8, "low_stock_skus": 19}
    elif mock or os.getenv("USE_MOCK_DATA", "").lower() == "true":
        logger.info("Mode: Generating mock transaction data (anomaly=%s)...", simulate_anomaly)
        client = EasyEcomClient()
        orders = client.generate_mock_orders(report_date, simulate_anomaly=simulate_anomaly)
        inventory = client.fetch_inventory_summary()
        if simulate_anomaly:
            inventory["out_of_stock_skus"] = 28
            inventory["low_stock_skus"] = 62
    else:
        logger.info("Mode: Ingesting live data from EasyEcom API...")
        api_key = os.getenv("EASYECOM_API_KEY")
        jwt_token = os.getenv("EASYECOM_JWT_TOKEN")
        base_url = os.getenv("EASYECOM_BASE_URL", "https://api.easyecom.io")

        if not api_key or not jwt_token:
            logger.warning("EasyEcom credentials missing from .env. Switching to mock mode.")
            client = EasyEcomClient()
            orders = client.generate_mock_orders(report_date, simulate_anomaly=simulate_anomaly)
            inventory = client.fetch_inventory_summary()
        else:
            client = EasyEcomClient(api_key=api_key, jwt_token=jwt_token, base_url=base_url)
            orders = client.fetch_orders(start_date=report_date, end_date=report_date)
            inventory = client.fetch_inventory_summary()

    logger.info("Loaded %d order records for date %s", len(orders), report_date)

    # 2. KPI CALCULATION
    calculator = KpiCalculator(config)
    kpi_summary = calculator.compute_daily_kpis(orders, inventory, report_date=report_date)

    # 3. REPORT GENERATION (Daily Report Making Process)
    report_gen = ReportGenerator(output_dir=output_dir)
    generated_files = report_gen.generate_all_reports(kpi_summary)

    fin = kpi_summary["financials"]
    vol = kpi_summary["volume"]
    ful = kpi_summary["fulfillment"]
    ret = kpi_summary["returns_and_cancellations"]

    logger.info("--------------------------------------------------------")
    logger.info(" Executive KPI Summary:")
    logger.info(" Gross GMV:         %s%s", fin["currency"], f"{fin['gross_gmv']:,.2f}")
    logger.info(" Net Revenue:       %s%s", fin["currency"], f"{fin['net_revenue']:,.2f}")
    logger.info(" Total Orders:      %s", f"{vol['total_orders']:,}")
    logger.info(" AOV:               %s%s", fin["currency"], f"{fin['aov']:,.2f}")
    logger.info(" Fulfillment Rate:  %s%%", ful["fulfillment_rate_pct"])
    logger.info(" Return/RTO Rate:   %s%%", ret["return_rate_pct"])
    logger.info(" Status Health:     %s", kpi_summary["status_health"])
    logger.info(" Saved Artifacts:   %s", generated_files)
    logger.info("--------------------------------------------------------")

    # 4. SLACK POSTING & JSON PAYLOAD DUMP
    slack_formatter = SlackFormatter(config)
    blocks = slack_formatter.build_kpi_blocks(kpi_summary)

    slack_payload_path = os.path.join(output_dir, f"slack_payload_{report_date}.json")
    with open(slack_payload_path, "w", encoding="utf-8") as f:
        json.dump(blocks, f, indent=2)
    generated_files["slack_payload"] = slack_payload_path

    slack_sent = False
    if dry_run:
        logger.info("[DRY-RUN] Slack Block Kit payload created successfully:")
        print(json.dumps(blocks, indent=2))
        logger.info("[DRY-RUN] Skipping actual network request to Slack.")
    else:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        notifier = SlackNotifier(webhook_url=webhook_url)
        slack_sent = notifier.send_kpi_report(
            blocks=blocks,
            fallback_text=f"{config.get('company_name', 'Easycom')} Daily KPI Briefing ({report_date}): GMV {fin['currency']}{fin['gross_gmv']:,.2f} | Orders {vol['total_orders']:,}",
        )
        if slack_sent:
            logger.info("🎉 Daily report making process and Slack broadcast completed successfully!")
        else:
            logger.warning("Slack notification was not posted. Please check SLACK_WEBHOOK_URL in .env.")

    return {
        "kpi_summary": kpi_summary,
        "slack_blocks": blocks,
        "generated_files": generated_files,
        "slack_sent": slack_sent,
    }


def main():
    args = parse_arguments()
    run_pipeline(
        report_date=args.date,
        from_csv=args.from_csv,
        mock=args.mock,
        simulate_anomaly=args.simulate_anomaly,
        dry_run=args.dry_run,
        config_path=args.config,
    )


if __name__ == "__main__":
    main()
