/**
 * EasyEcom CSV Data Loader and Schema Normalizer for Node.js.
 */

import fs from 'node:fs';

export class EasyEcomCsvLoader {
  static COLUMN_ALIASES = {
    order_id: ['order_id', 'order id', 'reference_number', 'invoice_number'],
    channel_order_id: ['channel_order_id', 'marketplace_order_id', 'channel id'],
    channel_name: ['channel_name', 'marketplace', 'channel', 'source'],
    order_date: ['order_date', 'order date', 'created_at', 'invoice_date'],
    status: ['status', 'order_status', 'current_status'],
    item_count: ['item_count', 'quantity', 'total_quantity', 'units'],
    total_amount: ['total_amount', 'grand_total', 'invoice_amount', 'order_total', 'amount'],
    payment_mode: ['payment_mode', 'payment_method', 'payment_type'],
    customer_city: ['customer_city', 'city', 'shipping_city', 'destination_city'],
    warehouse: ['warehouse', 'hub', 'location', 'fulfillment_center']
  };

  /**
   * Parse a CSV string into an array of line tokens respecting quotes.
   */
  static parseCsvLine(line) {
    const row = [];
    let insideQuotes = false;
    let entry = '';

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        insideQuotes = !insideQuotes;
      } else if (char === ',' && !insideQuotes) {
        row.push(entry.trim());
        entry = '';
      } else {
        entry += char;
      }
    }
    row.push(entry.trim());
    return row.map(cell => cell.replace(/^"|"$/g, '').trim());
  }

  static cleanNumber(val, defaultVal = 0.0) {
    if (!val) return defaultVal;
    const cleanStr = String(val).replace(/[₹$,]/g, '').trim();
    const num = parseFloat(cleanStr);
    return isNaN(num) ? defaultVal : num;
  }

  static normalizeStatus(statusRaw) {
    if (!statusRaw) return 'Open';
    const s = String(statusRaw).toLowerCase();
    if (s.includes('deliver')) return 'Delivered';
    if (s.includes('ship') || s.includes('handover') || s.includes('dispatch')) return 'Shipped';
    if (s.includes('transit') || s.includes('out for delivery')) return 'In-Transit';
    if (s.includes('pending') || s.includes('breach') || s.includes('unfulfill')) return 'Pending Dispatch (Breached SLA)';
    if (s.includes('cancel') || s.includes('void')) return 'Cancelled';
    if (s.includes('rto') || s.includes('undelivered return')) return 'RTO (Courier Return)';
    if (s.includes('return')) return 'Customer Return';
    return statusRaw;
  }

  /**
   * Load and normalize raw orders from an EasyEcom CSV file.
   */
  static loadFromCsv(csvPath) {
    console.log(`[EasyEcomCsvLoader] Reading EasyEcom daily export CSV: ${csvPath}`);
    const fileContent = fs.readFileSync(csvPath, 'utf-8');
    const lines = fileContent.split(/\r?\n/).filter(line => line.trim().length > 0);

    if (lines.length === 0) return [];

    const headers = this.parseCsvLine(lines[0]).map(h => h.toLowerCase().trim());
    const headerMap = {};

    for (const [canonicalKey, aliases] of Object.entries(this.COLUMN_ALIASES)) {
      for (const alias of aliases) {
        const idx = headers.indexOf(alias);
        if (idx !== -1) {
          headerMap[canonicalKey] = idx;
          break;
        }
      }
    }

    const orders = [];
    for (let i = 1; i < lines.length; i++) {
      const row = this.parseCsvLine(lines[i]);
      if (row.length < headers.length / 2) continue;

      const getVal = (key, defaultVal = '') => {
        const idx = headerMap[key];
        return (idx !== undefined && row[idx] !== undefined) ? row[idx] : defaultVal;
      };

      const orderId = getVal('order_id', `ORD-${i}`);
      const rawStatus = getVal('status', 'Delivered');

      orders.push({
        order_id: orderId,
        channel_order_id: getVal('channel_order_id', `CH-${orderId}`),
        channel_name: getVal('channel_name', 'Direct'),
        order_date: getVal('order_date', ''),
        status: this.normalizeStatus(rawStatus),
        item_count: parseInt(getVal('item_count', '1'), 10) || 1,
        total_amount: this.cleanNumber(getVal('total_amount', '0.0')),
        payment_mode: getVal('payment_mode', 'Prepaid'),
        customer_city: getVal('customer_city', 'Metro'),
        warehouse: getVal('warehouse', 'Default Warehouse')
      });
    }

    console.log(`[EasyEcomCsvLoader] Successfully ingested and normalized ${orders.length} orders from CSV`);
    return orders;
  }
}
