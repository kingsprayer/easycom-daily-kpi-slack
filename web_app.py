#!/usr/bin/env python3
"""EasyEcom Daily KPI Reporting & Slack Automation Web Dashboard.

Provides an interactive executive web console on http://localhost:5000:
- Interactive Executive KPI Cards (Gross GMV, Volume, AOV, Fulfillment, Returns, OOS SKUs)
- Realistic Slack messenger mockup displaying the live Slack Block Kit card in #easycom-daily-kpi
- On-demand pipeline execution triggers (Mock, CSV, and Anomaly simulation)
- Historical performance log view with direct CSV download
- One-click access to the standalone print-to-PDF ready HTML report
"""

import csv
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

# Add current folder to sys.path to ensure src imports work cleanly
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from run_daily_kpi import run_pipeline, load_config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("easycom_web_app")

app = FastAPI(title="EasyEcom Daily KPI Dashboard", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = os.path.join(CURRENT_DIR, "reports")
SAMPLE_CSV_PATH = os.path.join(CURRENT_DIR, "sample_data", "sample_easyecom_orders.csv")
CONFIG_PATH = os.path.join(CURRENT_DIR, "config.json")
MASTER_CSV_PATH = os.path.join(REPORTS_DIR, "master_kpi_history.csv")

# In-memory cache of the latest pipeline run
latest_run_cache: Dict[str, Any] = {}


class PipelineRunRequest(BaseModel):
    mode: str = "mock"  # "mock" | "csv" | "anomaly"
    date: Optional[str] = None


def get_or_create_initial_run() -> Dict[str, Any]:
    """Ensure at least one run exists in cache for the dashboard on initial load."""
    global latest_run_cache
    if not latest_run_cache:
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            logger.info("Initializing baseline KPI run for date %s", target_date)
            latest_run_cache = run_pipeline(
                report_date=target_date,
                mock=True,
                simulate_anomaly=False,
                dry_run=True,
                config_path=CONFIG_PATH,
            )
        except Exception as e:
            logger.error("Error creating initial run: %s", e)
    return latest_run_cache


@app.get("/api/kpi/latest")
async def get_latest_kpi():
    """Return latest KPI metrics, Slack blocks, and generated artifacts."""
    run_data = get_or_create_initial_run()
    if not run_data:
        raise HTTPException(status_code=500, detail="Failed to initialize KPI data.")
    return JSONResponse(run_data)


@app.post("/api/pipeline/run")
async def execute_pipeline(req: PipelineRunRequest):
    """Execute pipeline on-demand: mock, from-csv, or simulate-anomaly."""
    global latest_run_cache
    target_date = req.date or (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    mode = req.mode.lower()

    logger.info("Executing pipeline on-demand: mode=%s, date=%s", mode, target_date)
    try:
        if mode == "csv":
            if not os.path.exists(SAMPLE_CSV_PATH):
                raise HTTPException(status_code=404, detail="Sample CSV not found.")
            res = run_pipeline(
                report_date=target_date,
                from_csv=SAMPLE_CSV_PATH,
                mock=False,
                simulate_anomaly=False,
                dry_run=True,
                config_path=CONFIG_PATH,
            )
        elif mode == "anomaly":
            res = run_pipeline(
                report_date=target_date,
                mock=True,
                simulate_anomaly=True,
                dry_run=True,
                config_path=CONFIG_PATH,
            )
        else:  # mock default
            res = run_pipeline(
                report_date=target_date,
                mock=True,
                simulate_anomaly=False,
                dry_run=True,
                config_path=CONFIG_PATH,
            )

        latest_run_cache = res
        return JSONResponse({"success": True, "data": res})
    except Exception as e:
        logger.exception("Pipeline execution failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history():
    """Return historical records from master_kpi_history.csv."""
    records = []
    if os.path.exists(MASTER_CSV_PATH):
        with open(MASTER_CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    return JSONResponse({"history": list(reversed(records))})


@app.get("/reports/{filename}")
async def serve_report_file(filename: str):
    """Serve generated report files (HTML, JSON, Markdown, CSV)."""
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(REPORTS_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested report file not found.")
    
    media_type = "text/plain"
    if safe_filename.endswith(".html"):
        media_type = "text/html"
    elif safe_filename.endswith(".json"):
        media_type = "application/json"
    elif safe_filename.endswith(".csv"):
        media_type = "text/csv"
    elif safe_filename.endswith(".pdf"):
        media_type = "application/pdf"

    return FileResponse(file_path, media_type=media_type)


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the single-page executive web dashboard."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EasyEcom Daily KPI Reporting & Slack Automation</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-dark: #0a0d14;
      --bg-card: rgba(18, 24, 38, 0.85);
      --bg-card-hover: rgba(26, 35, 54, 0.95);
      --border-subtle: rgba(255, 255, 255, 0.08);
      --border-bright: rgba(255, 255, 255, 0.16);
      --accent-blue: #3b82f6;
      --accent-purple: #8b5cf6;
      --accent-emerald: #10b981;
      --accent-amber: #f59e0b;
      --accent-rose: #ef4444;
      --text-main: #f3f4f6;
      --text-muted: #9ca3af;
      --text-faint: #6b7280;
      --slack-bg: #1a1d21;
      --slack-border: #2c3136;
      --slack-sidebar: #121016;
      --slack-accent: #1264a3;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background: radial-gradient(circle at 15% 15%, #131929 0%, #0a0d14 70%);
      color: var(--text-main);
      min-height: 100vh;
      line-height: 1.5;
      padding-bottom: 60px;
    }

    /* Header Nav */
    header {
      background: rgba(10, 13, 20, 0.8);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 16px 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-icon {
      width: 42px;
      height: 42px;
      background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      box-shadow: 0 4px 16px rgba(59, 130, 246, 0.3);
    }

    .brand h1 {
      font-size: 1.25rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      background: linear-gradient(to right, #ffffff, #cbd5e1);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand p {
      font-size: 0.8rem;
      color: var(--text-muted);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.02em;
      background: rgba(16, 185, 129, 0.12);
      border: 1px solid rgba(16, 185, 129, 0.3);
      color: var(--accent-emerald);
      transition: all 0.3s ease;
    }

    .status-badge.critical {
      background: rgba(239, 68, 68, 0.12);
      border-color: rgba(239, 68, 68, 0.3);
      color: var(--accent-rose);
    }

    .status-badge.attention {
      background: rgba(245, 158, 11, 0.12);
      border-color: rgba(245, 158, 11, 0.3);
      color: var(--accent-amber);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 8px currentColor;
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border-bright);
      color: var(--text-main);
      padding: 8px 14px;
      border-radius: 8px;
      font-size: 0.84rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    .btn-secondary:hover {
      background: rgba(255, 255, 255, 0.12);
      border-color: rgba(255, 255, 255, 0.3);
    }

    /* Main Container */
    main {
      max-width: 1360px;
      margin: 0 auto;
      padding: 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 28px;
    }

    /* Pipeline Control Bar */
    .control-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 16px;
      padding: 20px 24px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }

    .control-info h2 {
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 4px;
    }

    .control-info p {
      font-size: 0.82rem;
      color: var(--text-muted);
    }

    .control-triggers {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }

    .date-input-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid var(--border-subtle);
      padding: 6px 12px;
      border-radius: 8px;
    }

    .date-input-wrapper label {
      font-size: 0.76rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .date-input-wrapper input {
      background: transparent;
      border: none;
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.85rem;
      outline: none;
    }

    .trigger-btn {
      padding: 9px 16px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid transparent;
      transition: all 0.2s ease;
    }

    .trigger-btn.mock {
      background: linear-gradient(135deg, #2563eb, #3b82f6);
      color: #fff;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3);
    }

    .trigger-btn.mock:hover {
      box-shadow: 0 6px 20px rgba(37, 99, 235, 0.5);
      transform: translateY(-1px);
    }

    .trigger-btn.csv {
      background: rgba(16, 185, 129, 0.15);
      border-color: rgba(16, 185, 129, 0.4);
      color: #34d399;
    }

    .trigger-btn.csv:hover {
      background: rgba(16, 185, 129, 0.25);
      transform: translateY(-1px);
    }

    .trigger-btn.anomaly {
      background: rgba(239, 68, 68, 0.15);
      border-color: rgba(239, 68, 68, 0.4);
      color: #f87171;
    }

    .trigger-btn.anomaly:hover {
      background: rgba(239, 68, 68, 0.25);
      transform: translateY(-1px);
    }

    .trigger-btn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none !important;
    }

    /* KPI Metric Cards Grid */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .kpi-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 20px;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      position: relative;
      overflow: hidden;
    }

    .kpi-card:hover {
      border-color: var(--border-bright);
      background: var(--bg-card-hover);
      transform: translateY(-2px);
      box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    }

    .kpi-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .kpi-title {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .kpi-icon {
      font-size: 1.15rem;
    }

    .kpi-value {
      font-size: 1.65rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      margin-bottom: 6px;
      color: #ffffff;
      font-family: 'JetBrains Mono', monospace;
    }

    .kpi-sub {
      font-size: 0.78rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .kpi-sub b {
      color: var(--text-main);
    }

    .kpi-tag {
      display: inline-block;
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .tag-emerald { background: rgba(16, 185, 129, 0.15); color: #34d399; }
    .tag-rose { background: rgba(239, 68, 68, 0.15); color: #f87171; }
    .tag-amber { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }

    /* Operational Warning Banner */
    .anomaly-banner {
      background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(185, 28, 28, 0.08));
      border: 1px solid rgba(239, 68, 68, 0.4);
      border-radius: 12px;
      padding: 16px 20px;
      display: none;
      align-items: flex-start;
      gap: 14px;
      box-shadow: 0 4px 20px rgba(239, 68, 68, 0.1);
      animation: pulse 2s infinite ease-in-out;
    }

    .anomaly-banner.visible {
      display: flex;
    }

    @keyframes pulse {
      0%, 100% { border-color: rgba(239, 68, 68, 0.4); }
      50% { border-color: rgba(239, 68, 68, 0.8); }
    }

    .anomaly-icon {
      font-size: 24px;
      line-height: 1;
    }

    .anomaly-content h3 {
      font-size: 0.95rem;
      font-weight: 700;
      color: #fca5a5;
      margin-bottom: 4px;
    }

    .anomaly-content ul {
      list-style: none;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.82rem;
      color: #fee2e2;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    /* Split Section: Slack Mockup & Performance Breakdown */
    .dashboard-split {
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 24px;
    }

    @media (max-width: 1024px) {
      .dashboard-split {
        grid-template-columns: 1fr;
      }
    }

    /* Slack Mockup Window */
    .slack-window {
      background: var(--slack-bg);
      border: 1px solid var(--slack-border);
      border-radius: 14px;
      overflow: hidden;
      box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
      display: flex;
      flex-direction: column;
    }

    .slack-header {
      background: var(--slack-sidebar);
      padding: 12px 18px;
      border-bottom: 1px solid var(--slack-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .slack-channel-name {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 0.92rem;
      color: #f8f8f8;
    }

    .slack-channel-name span {
      color: #868686;
      font-weight: 400;
      font-size: 0.82rem;
    }

    .slack-header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
      color: #a0a0a0;
      font-size: 0.8rem;
    }

    .slack-body {
      padding: 20px;
      display: flex;
      gap: 14px;
      background: #1a1d21;
    }

    .slack-avatar {
      width: 40px;
      height: 40px;
      background: linear-gradient(135deg, #10b981, #059669);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      flex-shrink: 0;
    }

    .slack-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .slack-meta {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .slack-bot-name {
      font-weight: 800;
      font-size: 0.95rem;
      color: #f8f8f8;
    }

    .slack-app-badge {
      background: #383f45;
      color: #d1d5db;
      font-size: 0.65rem;
      font-weight: 700;
      padding: 1px 5px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .slack-timestamp {
      color: #9ca3af;
      font-size: 0.75rem;
    }

    /* Slack Block Kit Card Inner */
    .slack-block-card {
      background: #222529;
      border-left: 4px solid var(--slack-accent);
      border-radius: 6px;
      padding: 14px 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    .slack-block-card.critical {
      border-left-color: var(--accent-rose);
    }

    .slack-block-card.attention {
      border-left-color: var(--accent-amber);
    }

    .slack-card-header {
      font-size: 1.05rem;
      font-weight: 800;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .slack-context-text {
      font-size: 0.8rem;
      color: #9ca3af;
      padding-bottom: 6px;
      border-bottom: 1px solid #33383e;
    }

    .slack-alert-callout {
      background: rgba(239, 68, 68, 0.12);
      border: 1px solid rgba(239, 68, 68, 0.3);
      border-radius: 6px;
      padding: 10px 12px;
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.78rem;
      color: #fca5a5;
      white-space: pre-wrap;
    }

    .slack-fields-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .slack-field-box {
      font-size: 0.82rem;
      background: rgba(255, 255, 255, 0.02);
      padding: 8px 10px;
      border-radius: 4px;
      border-left: 2px solid #3e444b;
    }

    .slack-field-box b {
      color: #d1d5db;
      display: block;
      margin-bottom: 3px;
    }

    .slack-field-box .slack-val {
      color: #ffffff;
      font-weight: 700;
      font-size: 0.95rem;
      font-family: 'JetBrains Mono', monospace;
    }

    .slack-field-box .slack-muted {
      color: #9ca3af;
      font-size: 0.74rem;
      display: block;
      margin-top: 2px;
    }

    .slack-channels-list {
      font-size: 0.82rem;
      border-top: 1px solid #33383e;
      padding-top: 10px;
      color: #e5e7eb;
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .slack-action-row {
      margin-top: 6px;
      display: flex;
      gap: 8px;
    }

    .slack-btn {
      background: #007a5a;
      color: #ffffff;
      border: none;
      padding: 8px 14px;
      border-radius: 4px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .slack-btn:hover {
      background: #148567;
    }

    .slack-footer-bar {
      background: #1a1d21;
      border-top: 1px solid var(--slack-border);
      padding: 10px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #717274;
      font-size: 0.78rem;
    }

    /* Channel Performance Cards & Artifacts */
    .side-stack {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }

    .panel-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 20px;
    }

    .panel-card h3 {
      font-size: 0.95rem;
      font-weight: 700;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .channel-item {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 12px;
    }

    .channel-meta {
      display: flex;
      justify-content: space-between;
      font-size: 0.82rem;
    }

    .channel-meta .name {
      font-weight: 600;
      color: #f3f4f6;
    }

    .channel-meta .rev {
      font-family: 'JetBrains Mono', monospace;
      color: #93c5fd;
      font-weight: 700;
    }

    .channel-bar-bg {
      height: 7px;
      background: rgba(255, 255, 255, 0.08);
      border-radius: 4px;
      overflow: hidden;
    }

    .channel-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple));
      border-radius: 4px;
      transition: width 0.5s ease;
    }

    .artifacts-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .artifact-link {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(255, 255, 255, 0.03);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 10px 14px;
      text-decoration: none;
      color: var(--text-main);
      font-size: 0.82rem;
      font-weight: 500;
      transition: all 0.2s ease;
    }

    .artifact-link:hover {
      background: rgba(255, 255, 255, 0.07);
      border-color: rgba(255, 255, 255, 0.2);
      transform: translateX(3px);
    }

    .artifact-link span {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    /* History Table */
    .history-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 22px;
      overflow-x: auto;
    }

    .history-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .history-header h3 {
      font-size: 1.05rem;
      font-weight: 700;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
      text-align: left;
    }

    th {
      color: var(--text-muted);
      font-weight: 600;
      padding: 10px 14px;
      border-bottom: 1px solid var(--border-bright);
      text-transform: uppercase;
      letter-spacing: 0.03em;
      font-size: 0.74rem;
    }

    td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-main);
      font-family: 'JetBrains Mono', monospace;
    }

    tr:hover td {
      background: rgba(255, 255, 255, 0.02);
    }

    /* Toast Notification */
    .toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: rgba(18, 24, 38, 0.95);
      border: 1px solid var(--accent-blue);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
      border-radius: 10px;
      padding: 14px 20px;
      color: #fff;
      font-size: 0.86rem;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      z-index: 1000;
      opacity: 0;
      transform: translateY(20px);
      transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      pointer-events: none;
    }

    .toast.show {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }

    /* Loading Spinner */
    .spinner {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.3);
      border-radius: 50%;
      border-top-color: #fff;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header>
    <div class="brand">
      <div class="brand-icon">📦</div>
      <div>
        <h1>EasyEcom Operations & KPI Automation</h1>
        <p>Production Analytics & Slack Morning Broadcast Console</p>
      </div>
    </div>
    <div class="header-actions">
      <div id="system-status-badge" class="status-badge">
        <span class="status-dot"></span>
        <span id="system-status-text">🟢 HEALTHY</span>
      </div>
      <a id="btn-view-report" href="/reports/daily_kpi_2026-09-22.html" target="_blank" class="btn-secondary">
        📄 View HTML Report ↗
      </a>
      <a href="/reports/master_kpi_history.csv" download class="btn-secondary">
        📥 Master CSV
      </a>
    </div>
  </header>

  <main>

    <!-- Operational Anomaly Warning Banner (Dynamic) -->
    <div id="anomaly-banner" class="anomaly-banner">
      <div class="anomaly-icon">🚨</div>
      <div class="anomaly-content">
        <h3 id="anomaly-title">Operational Anomaly Detected</h3>
        <ul id="anomaly-list">
          <li>⚠️ Fulfillment Rate dropped below safety threshold</li>
        </ul>
      </div>
    </div>

    <!-- Pipeline On-Demand Execution Control Bar -->
    <section class="control-card">
      <div class="control-info">
        <h2>⚡ Pipeline Dispatcher & Trigger Controller</h2>
        <p>Trigger automated report generation and real-time Slack notification payloads on demand.</p>
      </div>
      <div class="control-triggers">
        <div class="date-input-wrapper">
          <label for="pipeline-date">Target Date</label>
          <input type="date" id="pipeline-date">
        </div>
        <button id="btn-run-mock" class="trigger-btn mock" onclick="triggerPipeline('mock')">
          <span>🚀 Run Mock Baseline</span>
        </button>
        <button id="btn-run-csv" class="trigger-btn csv" onclick="triggerPipeline('csv')">
          <span>📂 Ingest Sample CSV</span>
        </button>
        <button id="btn-run-anomaly" class="trigger-btn anomaly" onclick="triggerPipeline('anomaly')">
          <span>⚠️ Simulate Anomaly</span>
        </button>
      </div>
    </section>

    <!-- 6 Executive KPI Metric Cards -->
    <section class="kpi-grid">
      <!-- 1. Gross GMV -->
      <div class="kpi-card" id="card-gmv">
        <div class="kpi-card-header">
          <span class="kpi-title">Gross GMV</span>
          <span class="kpi-icon">💰</span>
        </div>
        <div class="kpi-value" id="val-gmv">₹0.00</div>
        <div class="kpi-sub">Net Realized: <b id="val-net-rev">₹0.00</b></div>
      </div>

      <!-- 2. Total Volume -->
      <div class="kpi-card" id="card-volume">
        <div class="kpi-card-header">
          <span class="kpi-title">Order Volume</span>
          <span class="kpi-icon">📦</span>
        </div>
        <div class="kpi-value" id="val-orders">0</div>
        <div class="kpi-sub"><b id="val-units">0</b> units (<span id="val-units-per-order">1.2</span> / ord)</div>
      </div>

      <!-- 3. AOV -->
      <div class="kpi-card" id="card-aov">
        <div class="kpi-card-header">
          <span class="kpi-title">Average Order Value</span>
          <span class="kpi-icon">📈</span>
        </div>
        <div class="kpi-value" id="val-aov">₹0.00</div>
        <div class="kpi-sub">Prepaid: <b id="val-prepaid-pct">0%</b> | COD: <b id="val-cod-pct">0%</b></div>
      </div>

      <!-- 4. Fulfillment Rate -->
      <div class="kpi-card" id="card-fulfillment">
        <div class="kpi-card-header">
          <span class="kpi-title">Fulfillment Rate</span>
          <span class="kpi-icon">🚚</span>
        </div>
        <div class="kpi-value" id="val-fulfillment-rate">0%</div>
        <div class="kpi-sub"><b id="val-fulfilled-count">0</b> dispatched | SLA: <span id="val-pending-count">0</span></div>
      </div>

      <!-- 5. Returns & RTO -->
      <div class="kpi-card" id="card-returns">
        <div class="kpi-card-header">
          <span class="kpi-title">Returns & RTO %</span>
          <span class="kpi-icon">↩️</span>
        </div>
        <div class="kpi-value" id="val-return-rate">0%</div>
        <div class="kpi-sub">RTO: <b id="val-rto-count">0</b> | Cust: <b id="val-cust-return-count">0</b></div>
      </div>

      <!-- 6. Stockout SKUs -->
      <div class="kpi-card" id="card-stock">
        <div class="kpi-card-header">
          <span class="kpi-title">Stockout Health</span>
          <span class="kpi-icon">🏭</span>
        </div>
        <div class="kpi-value" id="val-oos-skus">0</div>
        <div class="kpi-sub">Low stock alerts: <b id="val-low-stock">0</b> SKUs</div>
      </div>
    </section>

    <!-- Split Section: Slack Mockup & Channel Breakdown -->
    <div class="dashboard-split">
      
      <!-- Realistic Slack Messenger Mockup -->
      <div class="slack-window">
        <div class="slack-header">
          <div class="slack-channel-name">
            # easycom-daily-kpi
            <span>Daily 08:30 AM IST Automated Executive Broadcast</span>
          </div>
          <div class="slack-header-actions">
            <span>👥 28 members</span>
            <span>📌 3 pinned</span>
          </div>
        </div>

        <div class="slack-body">
          <div class="slack-avatar">🤖</div>
          <div class="slack-content">
            <div class="slack-meta">
              <span class="slack-bot-name">Easycom KPI Bot</span>
              <span class="slack-app-badge">APP</span>
              <span class="slack-timestamp">Today at 08:30 AM</span>
            </div>

            <!-- Block Kit Message Card -->
            <div id="slack-card-preview" class="slack-block-card">
              <div class="slack-card-header" id="slack-preview-header">
                📊 Easycom Daily KPI Briefing
              </div>
              <div class="slack-context-text" id="slack-preview-context">
                📅 Period: <code id="slack-period">2026-09-22</code> | Status: <b id="slack-status">🟢 HEALTHY</b> | Source: EasyEcom ERP
              </div>

              <!-- Anomaly Callout in Slack Card -->
              <div id="slack-alert-box" class="slack-alert-callout" style="display: none;"></div>

              <div class="slack-fields-grid">
                <div class="slack-field-box">
                  <b>💰 Gross Sales (GMV)</b>
                  <div class="slack-val" id="slack-gmv">₹0.00</div>
                  <span class="slack-muted" id="slack-net">Net: ₹0.00</span>
                </div>
                <div class="slack-field-box">
                  <b>📦 Orders & Volume</b>
                  <div class="slack-val" id="slack-orders">0 Orders</div>
                  <span class="slack-muted" id="slack-units">0 Units (1.2 / ord)</span>
                </div>
                <div class="slack-field-box">
                  <b>📈 Average Order Value</b>
                  <div class="slack-val" id="slack-aov">₹0.00</div>
                </div>
                <div class="slack-field-box">
                  <b>🚚 Fulfillment Rate</b>
                  <div class="slack-val" id="slack-fulfillment">0%</div>
                  <span class="slack-muted" id="slack-dispatched">0 Dispatched</span>
                </div>
                <div class="slack-field-box">
                  <b>↩️ Total Returns & RTO</b>
                  <div class="slack-val" id="slack-returns">0%</div>
                  <span class="slack-muted" id="slack-returns-detail">0 Returns</span>
                </div>
                <div class="slack-field-box">
                  <b>🏭 Stockout Health</b>
                  <div class="slack-val" id="slack-oos">0 OOS SKUs</div>
                  <span class="slack-muted" id="slack-low-stock">0 Low Stock</span>
                </div>
              </div>

              <!-- Channel performance preview inside Slack Card -->
              <div class="slack-channels-list">
                <b>🛒 Sales Channel Performance:</b>
                <div id="slack-channel-lines"></div>
              </div>

              <!-- Action button inside Slack Card -->
              <div class="slack-action-row">
                <a href="https://dashboard.easyecom.io" target="_blank" class="slack-btn">
                  Open EasyEcom Dashboard ↗
                </a>
              </div>
            </div>
          </div>
        </div>

        <div class="slack-footer-bar">
          <span>⚡ Live Slack Block Kit Payload preview verified via incoming webhook contract</span>
          <span>Slack v4.38.1</span>
        </div>
      </div>

      <!-- Right Column: Channel Breakdown & Artifacts -->
      <div class="side-stack">
        <!-- Sales Channel Breakdown -->
        <div class="panel-card">
          <h3>
            <span>🛒 Sales Channel Share</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">Revenue & Volume</span>
          </h3>
          <div id="channel-bars-container">
            <!-- Rendered dynamically -->
          </div>
        </div>

        <!-- Generated Pipeline Artifacts -->
        <div class="panel-card">
          <h3>
            <span>📁 Pipeline Artifacts</span>
            <span style="font-size: 0.75rem; color: var(--text-muted); font-weight: normal;">Output Files</span>
          </h3>
          <div class="artifacts-list" id="artifacts-list-container">
            <a id="art-html-link" href="#" target="_blank" class="artifact-link">
              <span>📄 Standalone Styled HTML Dashboard</span>
              <span style="color: var(--accent-blue)">Open ↗</span>
            </a>
            <a id="art-md-link" href="#" target="_blank" class="artifact-link">
              <span>📝 Executive Markdown Briefing</span>
              <span style="color: var(--accent-purple)">View ↗</span>
            </a>
            <a id="art-json-link" href="#" target="_blank" class="artifact-link">
              <span>🧩 Slack Block Kit JSON Payload</span>
              <span style="color: var(--accent-emerald)">JSON ↗</span>
            </a>
            <a href="/reports/master_kpi_history.csv" download class="artifact-link">
              <span>📊 Master History CSV Log</span>
              <span style="color: var(--accent-amber)">Download ⤓</span>
            </a>
          </div>
        </div>
      </div>

    </div>

    <!-- Historical Performance Log Table -->
    <section class="history-card">
      <div class="history-header">
        <div>
          <h3>📜 Master Historical Performance Log</h3>
          <p style="font-size: 0.8rem; color: var(--text-muted);">Recorded by pipeline execution into reports/master_kpi_history.csv</p>
        </div>
        <a href="/reports/master_kpi_history.csv" download class="btn-secondary">
          ⤓ Download Full CSV
        </a>
      </div>
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Gross GMV</th>
            <th>Net Revenue</th>
            <th>Orders</th>
            <th>AOV</th>
            <th>Fulfillment</th>
            <th>Pending SLA</th>
            <th>Returns</th>
            <th>Health Status</th>
          </tr>
        </thead>
        <tbody id="history-table-body">
          <tr><td colspan="9" style="text-align: center; color: var(--text-muted);">Loading historical records...</td></tr>
        </tbody>
      </table>
    </section>

  </main>

  <!-- Notification Toast -->
  <div id="toast" class="toast">
    <span id="toast-icon">✨</span>
    <span id="toast-message">Pipeline execution completed</span>
  </div>

  <script>
    // Format helpers
    const formatCurrency = (num) => '₹' + Number(num || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    const formatNumber = (num) => Number(num || 0).toLocaleString('en-IN');

    // Default yesterday date
    const today = new Date();
    today.setDate(today.getDate() - 1);
    document.getElementById('pipeline-date').value = today.toISOString().split('T')[0];

    function showToast(msg, icon = '✨') {
      const toast = document.getElementById('toast');
      document.getElementById('toast-message').textContent = msg;
      document.getElementById('toast-icon').textContent = icon;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3500);
    }

    async function loadLatestData() {
      try {
        const res = await fetch('/api/kpi/latest');
        if (!res.ok) throw new Error('Failed to load KPI data');
        const data = await res.json();
        renderDashboard(data);
      } catch (err) {
        console.error('Error fetching initial KPI data:', err);
      }
    }

    async function loadHistoryData() {
      try {
        const res = await fetch('/api/history');
        if (!res.ok) return;
        const data = await res.json();
        renderHistoryTable(data.history || []);
      } catch (err) {
        console.error('Error loading history table:', err);
      }
    }

    function renderDashboard(pipelineData) {
      const kpis = pipelineData.kpi_summary;
      if (!kpis) return;

      const fin = kpis.financials || {};
      const vol = kpis.volume || {};
      const ful = kpis.fulfillment || {};
      const ret = kpis.returns_and_cancellations || {};
      const inv = kpis.inventory || {};
      const pay = kpis.payments || {};
      const date = kpis.report_date || '';
      const statusHealth = kpis.status_health || '🟢 HEALTHY';
      const alerts = kpis.alerts || [];

      // 1. Status Badges & Banners
      const sysStatusBadge = document.getElementById('system-status-badge');
      const sysStatusText = document.getElementById('system-status-text');
      sysStatusText.textContent = statusHealth;

      sysStatusBadge.classList.remove('critical', 'attention');
      if (statusHealth.includes('CRITICAL')) sysStatusBadge.classList.add('critical');
      else if (statusHealth.includes('ATTENTION')) sysStatusBadge.classList.add('attention');

      // Anomaly Banner
      const anomalyBanner = document.getElementById('anomaly-banner');
      const anomalyList = document.getElementById('anomaly-list');
      if (alerts && alerts.length > 0) {
        anomalyBanner.classList.add('visible');
        anomalyList.innerHTML = alerts.map(a => `<li>${a}</li>`).join('');
      } else {
        anomalyBanner.classList.remove('visible');
      }

      // 2. Executive KPI Cards
      document.getElementById('val-gmv').textContent = formatCurrency(fin.gross_gmv);
      document.getElementById('val-net-rev').textContent = formatCurrency(fin.net_revenue);

      document.getElementById('val-orders').textContent = formatNumber(vol.total_orders);
      document.getElementById('val-units').textContent = formatNumber(vol.total_units);
      document.getElementById('val-units-per-order').textContent = vol.units_per_order || '1.0';

      document.getElementById('val-aov').textContent = formatCurrency(fin.aov);
      document.getElementById('val-prepaid-pct').textContent = (pay.prepaid_pct || 0) + '%';
      document.getElementById('val-cod-pct').textContent = (pay.cod_pct || 0) + '%';

      document.getElementById('val-fulfillment-rate').textContent = (ful.fulfillment_rate_pct || 0) + '%';
      document.getElementById('val-fulfilled-count').textContent = formatNumber(ful.fulfilled_count);
      document.getElementById('val-pending-count').textContent = formatNumber(ful.pending_dispatch_count);

      document.getElementById('val-return-rate').textContent = (ret.return_rate_pct || 0) + '%';
      document.getElementById('val-rto-count').textContent = formatNumber(ret.rto_returns_count);
      document.getElementById('val-cust-return-count').textContent = formatNumber(ret.customer_returns_count);

      document.getElementById('val-oos-skus').textContent = inv.out_of_stock_skus || 0;
      document.getElementById('val-low-stock').textContent = inv.low_stock_skus || 0;

      // 3. Slack Mockup Synchronization
      document.getElementById('slack-period').textContent = date;
      document.getElementById('slack-status').textContent = statusHealth;

      const slackCard = document.getElementById('slack-card-preview');
      slackCard.classList.remove('critical', 'attention');
      if (statusHealth.includes('CRITICAL')) slackCard.classList.add('critical');
      else if (statusHealth.includes('ATTENTION')) slackCard.classList.add('attention');

      const slackAlertBox = document.getElementById('slack-alert-box');
      if (alerts && alerts.length > 0) {
        slackAlertBox.style.display = 'block';
        slackAlertBox.textContent = '*⚠️ Operational Action Required:*\n' + alerts.join('\\n');
      } else {
        slackAlertBox.style.display = 'none';
      }

      document.getElementById('slack-gmv').textContent = formatCurrency(fin.gross_gmv);
      document.getElementById('slack-net').textContent = 'Net: ' + formatCurrency(fin.net_revenue);
      document.getElementById('slack-orders').textContent = formatNumber(vol.total_orders) + ' Orders';
      document.getElementById('slack-units').textContent = formatNumber(vol.total_units) + ' Units (' + vol.units_per_order + ' / ord)';
      document.getElementById('slack-aov').textContent = formatCurrency(fin.aov);
      document.getElementById('slack-fulfillment').textContent = (ful.fulfillment_rate_pct || 0) + '%';
      document.getElementById('slack-dispatched').textContent = formatNumber(ful.fulfilled_count) + ' dispatched';
      document.getElementById('slack-returns').textContent = (ret.return_rate_pct || 0) + '%';
      document.getElementById('slack-returns-detail').textContent = 'RTO: ' + ret.rto_returns_count + ' | Cust: ' + ret.customer_returns_count;
      document.getElementById('slack-oos').textContent = (inv.out_of_stock_skus || 0) + ' OOS SKUs';
      document.getElementById('slack-low-stock').textContent = (inv.low_stock_skus || 0) + ' low stock';

      // Slack Channel lines
      const channels = kpis.channels || [];
      const channelLines = channels.map(c => `• <b>${c.channel}</b>: ${c.orders} ord | ${formatCurrency(c.revenue)} (<b>${c.revenue_share_pct}%</b>)`).join('<br>');
      document.getElementById('slack-channel-lines').innerHTML = channelLines;

      // 4. Channel Breakdown Progress Bars
      const channelContainer = document.getElementById('channel-bars-container');
      channelContainer.innerHTML = channels.map(c => `
        <div class="channel-item">
          <div class="channel-meta">
            <span class="name">${c.channel} (${c.orders} orders)</span>
            <span class="rev">${formatCurrency(c.revenue)} &bull; ${c.revenue_share_pct}%</span>
          </div>
          <div class="channel-bar-bg">
            <div class="channel-bar-fill" style="width: ${Math.min(c.revenue_share_pct, 100)}%;"></div>
          </div>
        </div>
      `).join('');

      // 5. Artifact Links
      const htmlFile = `/reports/daily_kpi_${date}.html`;
      const mdFile = `/reports/daily_kpi_${date}.md`;
      const jsonFile = `/reports/slack_payload_${date}.json`;

      document.getElementById('btn-view-report').href = htmlFile;
      document.getElementById('art-html-link').href = htmlFile;
      document.getElementById('art-md-link').href = mdFile;
      document.getElementById('art-json-link').href = jsonFile;
    }

    function renderHistoryTable(records) {
      const tbody = document.getElementById('history-table-body');
      if (!records || records.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" style="text-align: center; color: var(--text-muted);">No records found.</td></tr>';
        return;
      }
      tbody.innerHTML = records.map(r => `
        <tr>
          <td><b>${r.report_date || '-'}</b></td>
          <td>${formatCurrency(r.gross_gmv)}</td>
          <td>${formatCurrency(r.net_revenue)}</td>
          <td>${r.total_orders || '-'}</td>
          <td>${formatCurrency(r.aov)}</td>
          <td><span class="kpi-tag ${parseFloat(r.fulfillment_rate_pct) < 85 ? 'tag-rose' : 'tag-emerald'}">${r.fulfillment_rate_pct || '0'}%</span></td>
          <td>${r.pending_dispatch || '0'}</td>
          <td><span class="kpi-tag ${parseFloat(r.return_rate_pct) > 12 ? 'tag-rose' : 'tag-emerald'}">${r.return_rate_pct || '0'}%</span></td>
          <td>${r.status_health || '🟢 HEALTHY'}</td>
        </tr>
      `).join('');
    }

    async function triggerPipeline(mode) {
      const btnMock = document.getElementById('btn-run-mock');
      const btnCsv = document.getElementById('btn-run-csv');
      const btnAnomaly = document.getElementById('btn-run-anomaly');
      const targetDate = document.getElementById('pipeline-date').value;

      [btnMock, btnCsv, btnAnomaly].forEach(b => b.disabled = true);
      const activeBtn = mode === 'csv' ? btnCsv : (mode === 'anomaly' ? btnAnomaly : btnMock);
      const origText = activeBtn.innerHTML;
      activeBtn.innerHTML = '<span class="spinner"></span> Running...';

      try {
        const res = await fetch('/api/pipeline/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ mode: mode, date: targetDate })
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Execution failed');
        }

        const data = await res.json();
        renderDashboard(data.data);
        await loadHistoryData();
        showToast(`Pipeline executed (${mode.toUpperCase()}) for ${targetDate}!`, '🚀');
      } catch (err) {
        alert('Pipeline execution error: ' + err.message);
      } finally {
        [btnMock, btnCsv, btnAnomaly].forEach(b => b.disabled = false);
        activeBtn.innerHTML = origText;
      }
    }

    // Initialize on load
    window.addEventListener('DOMContentLoaded', () => {
      loadLatestData();
      loadHistoryData();
    });
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html_content)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    logger.info("Starting EasyEcom Web Dashboard on http://localhost:%d", port)
    uvicorn.run("web_app:app", host="0.0.0.0", port=port, reload=False)
