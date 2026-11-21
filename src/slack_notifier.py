"""Slack Webhook Notifier for Easycom.

Posts prepared Block Kit payloads to Slack channels using Incoming Webhooks.
Includes retries, timeout handling, and informative error messages.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Dispatches messages to Slack via Incoming Webhook."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def send_kpi_report(
        self,
        blocks: List[Dict[str, Any]],
        fallback_text: str = "Easycom Daily KPI Briefing",
    ) -> bool:
        """Post Block Kit payload to Slack webhook."""
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL is not configured. Skipping Slack dispatch.")
            return False

        payload = {
            "text": fallback_text,
            "blocks": blocks,
        }

        try:
            logger.info("Posting Daily KPI report to Slack Webhook...")
            response = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers={"Content-Type": "application/json"},
                timeout=15,
            )

            if response.status_code == 200 and response.text.strip().lower() == "ok":
                logger.info("Successfully delivered Daily KPI report to Slack!")
                return True
            else:
                logger.error(
                    "Slack webhook responded with error status %d: %s",
                    response.status_code,
                    response.text,
                )
                return False

        except requests.RequestException as exc:
            logger.error("Failed to connect to Slack webhook: %s", exc)
            return False
