/**
 * EasyEcom API Client and Mock Data Generator for Node.js.
 *
 * Provides authentication and retrieval methods for Orders, Dispatches, Returns,
 * and Inventory metrics from EasyEcom (https://api-docs.easyecom.io).
 */

export class EasyEcomClient {
  constructor(apiKey = null, jwtToken = null, baseUrl = 'https://api.easyecom.io') {
    this.apiKey = apiKey;
    this.jwtToken = jwtToken;
    this.baseUrl = baseUrl.replace(/\/+$/, '');
  }

  get headers() {
    return {
      'x-api-key': this.apiKey || '',
      'Authorization': `Bearer ${this.jwtToken || ''}`,
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };
  }

  /**
   * Fetch orders for a given date window (YYYY-MM-DD).
   */
  async fetchOrders(startDate, endDate, page = 1, limit = 250) {
    if (!this.apiKey || !this.jwtToken) {
      console.warn('[EasyEcomClient] Credentials not configured. Falling back to mock generator.');
      return this.generateMockOrders(startDate);
    }

    const endpoint = `${this.baseUrl}/orders/v2/getAllOrders?start_date=${startDate} 00:00:00&end_date=${endDate} 23:59:59&limit=${limit}&page=${page}`;
    try {
      console.log(`[EasyEcomClient] Fetching orders from EasyEcom API: ${endpoint}`);
      const res = await fetch(endpoint, {
        headers: this.headers,
        signal: AbortSignal.timeout(30000)
      });

      if (res.status === 401) {
        throw new Error('EasyEcom 401 Unauthorized: Invalid X-API-Key or expired Bearer JWT Token.');
      }
      if (!res.ok) {
        throw new Error(`EasyEcom API error: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      return data?.data?.orders || data?.orders || [];
    } catch (err) {
      console.error('[EasyEcomClient] Communication error:', err.message);
      throw err;
    }
  }

  /**
   * Fetch current stock health summary.
   */
  async fetchInventorySummary() {
    if (!this.apiKey || !this.jwtToken) {
      return {
        total_skus: 1420,
        in_stock_skus: 1408,
        out_of_stock_skus: 12,
        low_stock_skus: 34,
        damaged_stock_units: 45
      };
    }

    const endpoint = `${this.baseUrl}/inventory/details`;
    try {
      const res = await fetch(endpoint, {
        headers: this.headers,
        signal: AbortSignal.timeout(25000)
      });
      if (res.ok) {
        const json = await res.json();
        return json.data || {};
      }
    } catch (err) {
      console.warn('[EasyEcomClient] Could not fetch inventory details:', err.message);
    }
    return { total_skus: 0, out_of_stock_skus: 0 };
  }

  /**
   * Generate realistic synthetic transactions for Easycom.
   * Supports simulateAnomaly=true for operational bottleneck testing.
   */
  generateMockOrders(reportDate, simulateAnomaly = false) {
    let seed = parseInt(reportDate.replace(/-/g, ''), 10);
    if (simulateAnomaly) seed += 999;

    // Simple pseudo-random number generator for reproducible seed
    const pseudoRandom = () => {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };

    const weightedChoice = (items) => {
      const totalWeight = items.reduce((sum, item) => sum + item.weight, 0);
      let r = pseudoRandom() * totalWeight;
      for (const item of items) {
        if (r < item.weight) return item.value;
        r -= item.weight;
      }
      return items[0].value;
    };

    const channels = [
      { value: 'Amazon India', weight: 0.38 },
      { value: 'Flipkart', weight: 0.26 },
      { value: 'Shopify (Direct Website)', weight: 0.18 },
      { value: 'Myntra', weight: 0.10 },
      { value: 'Blinkit (QuickCommerce)', weight: 0.08 }
    ];

    let statuses = [];
    if (simulateAnomaly) {
      statuses = [
        { value: 'Delivered', weight: 0.38 },
        { value: 'Shipped', weight: 0.22 },
        { value: 'In-Transit', weight: 0.08 },
        { value: 'Pending Dispatch (Breached SLA)', weight: 0.17 },
        { value: 'Cancelled', weight: 0.05 },
        { value: 'Customer Return', weight: 0.06 },
        { value: 'RTO (Courier Return)', weight: 0.04 }
      ];
    } else {
      statuses = [
        { value: 'Delivered', weight: 0.52 },
        { value: 'Shipped', weight: 0.28 },
        { value: 'In-Transit', weight: 0.08 },
        { value: 'Pending Dispatch (Breached SLA)', weight: 0.04 },
        { value: 'Cancelled', weight: 0.03 },
        { value: 'Customer Return', weight: 0.03 },
        { value: 'RTO (Courier Return)', weight: 0.02 }
      ];
    }

    const totalOrdersCount = Math.floor(480 + pseudoRandom() * 240);
    const mockOrders = [];
    const cities = ['Mumbai', 'Delhi', 'Bengaluru', 'Hyderabad', 'Pune', 'Chennai', 'Kolkata', 'Ahmedabad', 'Jaipur'];
    const warehouses = ['WH-BHIWANDI-01', 'WH-BENGALURU-02', 'WH-GURUGRAM-01'];

    for (let i = 1; i <= totalOrdersCount; i++) {
      const channel = weightedChoice(channels);
      const status = weightedChoice(statuses);
      const unitPrice = Math.round((699 + pseudoRandom() * 2800) * 100) / 100;
      const quantity = pseudoRandom() > 0.15 ? 1 : (Math.floor(pseudoRandom() * 2) + 2);
      const subtotal = Math.round(unitPrice * quantity * 100) / 100;
      const discount = Math.round(subtotal * (pseudoRandom() > 0.5 ? 0.05 : 0.0) * 100) / 100;
      const shipping = subtotal > 999 ? 0.0 : 79.0;
      const tax = Math.round((subtotal - discount) * 0.18 * 100) / 100;
      const totalAmount = Math.round(((subtotal - discount) + tax + shipping) * 100) / 100;

      const hour = String(Math.floor(pseudoRandom() * 24)).padStart(2, '0');
      const minute = String(Math.floor(pseudoRandom() * 60)).padStart(2, '0');
      const orderDate = `${reportDate} ${hour}:${minute}:00`;

      mockOrders.push({
        order_id: `EASY-${reportDate.replace(/-/g, '')}-${1000 + i}`,
        channel_order_id: `CH-${channel.slice(0, 3).toUpperCase()}-${10000 + i}`,
        channel_name: channel,
        order_date: orderDate,
        status: status,
        item_count: quantity,
        subtotal: subtotal,
        discount: discount,
        tax: tax,
        shipping_fee: shipping,
        total_amount: totalAmount,
        payment_mode: pseudoRandom() > 0.35 ? 'Prepaid' : 'COD',
        customer_city: cities[Math.floor(pseudoRandom() * cities.length)],
        warehouse: warehouses[Math.floor(pseudoRandom() * warehouses.length)]
      });
    }

    return mockOrders;
  }
}
