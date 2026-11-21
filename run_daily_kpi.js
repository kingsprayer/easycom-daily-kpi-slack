#!/usr/bin/env node
/**
 * Easycom Daily KPI Pipeline & Slack Reporter for Node.js.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import dotenv from 'dotenv';

import { EasyEcomClient } from './src/easyecomClient.js';
import { EasyEcomCsvLoader } from './src/csvDataLoader.js';
import { KpiCalculator } from './src/kpiCalculator.js';
import { ReportGenerator } from './src/reportGenerator.js';
import { SlackFormatter } from './src/slackFormatter.js';
import { SlackNotifier } from './src/slackNotifier.js';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export function loadConfig(configPath = 'config.json') {
  const fullPath = path.isAbsolute(configPath) ? configPath : path.join(__dirname, configPath);
  if (fs.existsSync(fullPath)) {
    try {
      return JSON.parse(fs.readFileSync(fullPath, 'utf-8'));
    } catch (e) {
      console.warn(`[Config] Failed to parse config file: ${fullPath}`, e.message);
    }
  }
  return {
    company_name: 'Easycom',
    currency_symbol: '₹',
    alert_thresholds: {
      min_fulfillment_rate_pct: 85.0,
      max_return_rate_pct: 12.0,
      max_sla_breach_count: 25,
      max_oos_skus_count: 15
    },
    reporting: { output_dir: 'reports' }
  };
}

export async function runPipeline({
  reportDate = null,
  fromCsv = null,
  mock = true,
  simulateAnomaly = false,
  dryRun = true,
  configPath = 'config.json'
} = {}) {
  const config = loadConfig(configPath);
  const outputDir = path.isAbsolute(config.reporting?.output_dir || 'reports')
    ? config.reporting.output_dir
    : path.join(__dirname, config.reporting?.output_dir || 'reports');

  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  if (!reportDate) {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    reportDate = d.toISOString().split('T')[0];
  }

  console.log('========================================================');
  console.log(' Easycom Daily KPI Reporting & Automation Pipeline (Node.js)');
  console.log(` Target Date: ${reportDate} | Anomaly Simulation: ${simulateAnomaly}`);
  console.log('========================================================');

  // 1. DATA EXTRACTION
  let orders = [];
  let inventory = {};

  if (fromCsv) {
    const csvPath = path.isAbsolute(fromCsv) ? fromCsv : path.join(__dirname, fromCsv);
    if (!fs.existsSync(csvPath)) {
      throw new Error(`Specified CSV file does not exist: ${csvPath}`);
    }
    orders = EasyEcomCsvLoader.loadFromCsv(csvPath);
    inventory = { out_of_stock_skus: 8, low_stock_skus: 19 };
  } else if (mock || process.env.USE_MOCK_DATA?.toLowerCase() === 'true') {
    console.log(`[Mode] Generating synthetic mock orders (anomaly=${simulateAnomaly})...`);
    const client = new EasyEcomClient();
    orders = client.generateMockOrders(reportDate, simulateAnomaly);
    inventory = await client.fetchInventorySummary();
    if (simulateAnomaly) {
      inventory.out_of_stock_skus = 28;
      inventory.low_stock_skus = 62;
    }
  } else {
    console.log('[Mode] Ingesting live data from EasyEcom REST API...');
    const apiKey = process.env.EASYECOM_API_KEY;
    const jwtToken = process.env.EASYECOM_JWT_TOKEN;
    const baseUrl = process.env.EASYECOM_BASE_URL || 'https://api.easyecom.io';

    if (!apiKey || !jwtToken) {
      console.warn('[Warning] Missing EasyEcom credentials in .env. Falling back to mock generator.');
      const client = new EasyEcomClient();
      orders = client.generateMockOrders(reportDate, simulateAnomaly);
      inventory = await client.fetchInventorySummary();
    } else {
      const client = new EasyEcomClient(apiKey, jwtToken, baseUrl);
      orders = await client.fetchOrders(reportDate, reportDate);
      inventory = await client.fetchInventorySummary();
    }
  }

  console.log(`Loaded ${orders.length} order records for date ${reportDate}`);

  // 2. KPI CALCULATION
  const calculator = new KpiCalculator(config);
  const kpiSummary = calculator.computeDailyKpis(orders, inventory, reportDate);

  // 3. REPORT GENERATION
  const reportGen = new ReportGenerator(outputDir);
  const generatedFiles = reportGen.generateAllReports(kpiSummary);

  const fin = kpiSummary.financials;
  const vol = kpiSummary.volume;
  const ful = kpiSummary.fulfillment;
  const ret = kpiSummary.returns_and_cancellations;

  console.log('--------------------------------------------------------');
  console.log(' Executive KPI Summary:');
  console.log(` Gross GMV:         ${fin.currency}${fin.gross_gmv.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`);
  console.log(` Net Revenue:       ${fin.currency}${fin.net_revenue.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`);
  console.log(` Total Orders:      ${vol.total_orders.toLocaleString('en-IN')}`);
  console.log(` AOV:               ${fin.currency}${fin.aov.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`);
  console.log(` Fulfillment Rate:  ${ful.fulfillment_rate_pct}%`);
  console.log(` Return/RTO Rate:   ${ret.return_rate_pct}%`);
  console.log(` Status Health:     ${kpiSummary.status_health}`);
  console.log(' Saved Artifacts:  ', generatedFiles);
  console.log('--------------------------------------------------------');

  // 4. SLACK POSTING
  const slackFormatter = new SlackFormatter(config);
  const blocks = slackFormatter.buildKpiBlocks(kpiSummary);

  const slackPayloadPath = path.join(outputDir, `slack_payload_${reportDate}.json`);
  fs.writeFileSync(slackPayloadPath, JSON.stringify(blocks, null, 2), 'utf-8');
  generatedFiles.slack_payload = slackPayloadPath;

  let slackSent = false;
  if (dryRun) {
    console.log('[DRY-RUN] Slack Block Kit payload created successfully:');
    console.log(JSON.stringify(blocks, null, 2));
    console.log('[DRY-RUN] Skipping actual network request to Slack.');
  } else {
    const webhookUrl = process.env.SLACK_WEBHOOK_URL;
    const notifier = new SlackNotifier(webhookUrl);
    slackSent = await notifier.sendKpiReport(
      blocks,
      `${config.company_name || 'Easycom'} Daily KPI Briefing (${reportDate}): GMV ${fin.currency}${fin.gross_gmv.toLocaleString('en-IN')} | Orders ${vol.total_orders}`
    );
    if (slackSent) {
      console.log('🎉 Daily report making process and Slack broadcast completed successfully!');
    } else {
      console.warn('Slack notification was not posted. Please check SLACK_WEBHOOK_URL in .env.');
    }
  }

  return {
    kpi_summary: kpiSummary,
    slack_blocks: blocks,
    generated_files: generatedFiles,
    slack_sent: slackSent
  };
}

// Parse CLI flags when executed directly
function parseArgs() {
  const args = process.argv.slice(2);
  const parsed = {
    date: null,
    fromCsv: null,
    mock: false,
    simulateAnomaly: false,
    dryRun: false,
    config: 'config.json'
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--date' && args[i + 1]) {
      parsed.date = args[++i];
    } else if (arg === '--from-csv' && args[i + 1]) {
      parsed.fromCsv = args[++i];
    } else if (arg === '--mock') {
      parsed.mock = true;
    } else if (arg === '--simulate-anomaly') {
      parsed.simulateAnomaly = true;
    } else if (arg === '--dry-run') {
      parsed.dryRun = true;
    } else if (arg === '--config' && args[i + 1]) {
      parsed.config = args[++i];
    }
  }
  return parsed;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cliArgs = parseArgs();
  runPipeline({
    reportDate: cliArgs.date,
    fromCsv: cliArgs.fromCsv,
    mock: cliArgs.mock,
    simulateAnomaly: cliArgs.simulateAnomaly,
    dryRun: cliArgs.dryRun,
    configPath: cliArgs.config
  }).catch(err => {
    console.error('Fatal execution error:', err);
    process.exit(1);
  });
}
