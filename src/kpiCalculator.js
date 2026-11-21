/**
 * Easycom KPI Calculation & Aggregation Engine for Node.js.
 */

export class KpiCalculator {
  constructor(config = {}) {
    this.config = config;
    this.thresholds = config.alert_thresholds || {};
    this.currency = config.currency_symbol || '₹';
  }

  computeDailyKpis(orders = [], inventory = {}, reportDate = '') {
    if (!orders || orders.length === 0) {
      return this._emptyKpiPayload(reportDate);
    }

    const totalOrders = orders.length;
    let totalUnits = 0;
    let grossGmv = 0.0;

    const deliveredOrders = [];
    const shippedOrders = [];
    const inTransitOrders = [];
    const pendingOrders = [];
    const cancelledOrders = [];
    const customerReturns = [];
    const rtoReturns = [];

    const channelStats = {};
    const paymentStats = { Prepaid: 0, COD: 0 };

    for (const order of orders) {
      const status = String(order.status || '').toLowerCase();
      const ch = order.channel_name || 'Other';
      const amt = Number(order.total_amount || 0.0);
      const units = Number(order.item_count || 1);
      const payMode = String(order.payment_mode || 'Prepaid');

      totalUnits += units;
      grossGmv += amt;

      // Payment mode
      if (payMode.toLowerCase().includes('cod')) {
        paymentStats.COD += 1;
      } else {
        paymentStats.Prepaid += 1;
      }

      // Channel stats
      if (!channelStats[ch]) {
        channelStats[ch] = { orders: 0, revenue: 0.0, units: 0 };
      }
      channelStats[ch].orders += 1;
      channelStats[ch].revenue += amt;
      channelStats[ch].units += units;

      // Status classification
      if (status.includes('deliver')) {
        deliveredOrders.push(order);
      } else if (status.includes('shipped')) {
        shippedOrders.push(order);
      } else if (status.includes('transit')) {
        inTransitOrders.push(order);
      } else if (status.includes('pending') || status.includes('breach') || status.includes('unfulfill')) {
        pendingOrders.push(order);
      } else if (status.includes('cancel')) {
        cancelledOrders.push(order);
      } else if (status.includes('rto')) {
        rtoReturns.push(order);
      } else if (status.includes('return')) {
        customerReturns.push(order);
      } else {
        shippedOrders.push(order);
      }
    }

    const fulfilledCount = deliveredOrders.length + shippedOrders.length + inTransitOrders.length;
    const validOrdersCount = totalOrders - cancelledOrders.length;
    const fulfillmentRate = validOrdersCount > 0 ? (fulfilledCount / validOrdersCount) * 100 : 0.0;

    const totalReturnsCount = customerReturns.length + rtoReturns.length;
    const returnRate = fulfilledCount > 0 ? (totalReturnsCount / fulfilledCount) * 100 : 0.0;
    const cancellationRate = totalOrders > 0 ? (cancelledOrders.length / totalOrders) * 100 : 0.0;

    const cancelledRev = cancelledOrders.reduce((sum, o) => sum + Number(o.total_amount || 0), 0);
    const returnedRev = [...customerReturns, ...rtoReturns].reduce((sum, o) => sum + Number(o.total_amount || 0), 0);
    const netRevenue = grossGmv - cancelledRev - returnedRev;

    const aov = validOrdersCount > 0 ? grossGmv / validOrdersCount : 0.0;
    const unitsPerOrder = totalOrders > 0 ? totalUnits / totalOrders : 1.0;

    // Channels sorted by revenue
    const channels = Object.entries(channelStats).map(([chName, data]) => {
      const share = grossGmv > 0 ? (data.revenue / grossGmv) * 100 : 0.0;
      return {
        channel: chName,
        orders: data.orders,
        revenue: Math.round(data.revenue * 100) / 100,
        revenue_share_pct: Math.round(share * 10) / 10,
        aov: data.orders > 0 ? Math.round((data.revenue / data.orders) * 100) / 100 : 0.0
      };
    }).sort((a, b) => b.revenue - a.revenue);

    // Inventory
    const inv = inventory || {};
    const oosSkus = inv.out_of_stock_skus || 0;
    const lowStockSkus = inv.low_stock_skus || 0;

    // Alert Evaluation
    const alerts = [];
    let statusHealth = '🟢 HEALTHY';

    const minFulf = this.thresholds.min_fulfillment_rate_pct ?? 85.0;
    const maxRet = this.thresholds.max_return_rate_pct ?? 12.0;
    const maxSla = this.thresholds.max_sla_breach_count ?? 25;
    const maxOos = this.thresholds.max_oos_skus_count ?? 15;

    if (fulfillmentRate < minFulf) {
      alerts.push(`⚠️ Fulfillment Rate (${fulfillmentRate.toFixed(1)}%) is below target (${minFulf}%)`);
      statusHealth = fulfillmentRate < (minFulf - 5.0) ? '🔴 CRITICAL' : '🟡 ATTENTION NEEDED';
    }

    if (returnRate > maxRet) {
      alerts.push(`🚨 Total Returns & RTO (${returnRate.toFixed(1)}%) exceeded safe threshold (${maxRet}%)`);
      statusHealth = '🔴 CRITICAL';
    }

    const slaBacklogCount = pendingOrders.length;
    if (slaBacklogCount > maxSla) {
      alerts.push(`⏰ SLA Aging: ${slaBacklogCount} orders pending dispatch (Breached target ${maxSla})`);
      if (statusHealth !== '🔴 CRITICAL') {
        statusHealth = '🟡 ATTENTION NEEDED';
      }
    }

    if (oosSkus > maxOos) {
      alerts.push(`📦 Inventory Warning: ${oosSkus} SKUs are currently Out of Stock`);
    }

    const prepaidPct = totalOrders > 0 ? (paymentStats.Prepaid / totalOrders) * 100 : 0.0;
    const codPct = totalOrders > 0 ? (paymentStats.COD / totalOrders) * 100 : 0.0;

    return {
      report_date: reportDate,
      company_name: this.config.company_name || 'Easycom',
      status_health: statusHealth,
      financials: {
        gross_gmv: Math.round(grossGmv * 100) / 100,
        net_revenue: Math.round(netRevenue * 100) / 100,
        aov: Math.round(aov * 100) / 100,
        currency: this.currency
      },
      volume: {
        total_orders: totalOrders,
        valid_orders: validOrdersCount,
        total_units: totalUnits,
        units_per_order: Math.round(unitsPerOrder * 100) / 100
      },
      fulfillment: {
        fulfilled_count: fulfilledCount,
        fulfillment_rate_pct: Math.round(fulfillmentRate * 10) / 10,
        pending_dispatch_count: slaBacklogCount
      },
      returns_and_cancellations: {
        total_returns_count: totalReturnsCount,
        customer_returns_count: customerReturns.length,
        rto_returns_count: rtoReturns.length,
        return_rate_pct: Math.round(returnRate * 10) / 10,
        cancelled_count: cancelledOrders.length,
        cancellation_rate_pct: Math.round(cancellationRate * 10) / 10
      },
      payments: {
        prepaid_count: paymentStats.Prepaid,
        cod_count: paymentStats.COD,
        prepaid_pct: Math.round(prepaidPct * 10) / 10,
        cod_pct: Math.round(codPct * 10) / 10
      },
      inventory: {
        out_of_stock_skus: oosSkus,
        low_stock_skus: lowStockSkus
      },
      channels: channels,
      alerts: alerts
    };
  }

  _emptyKpiPayload(reportDate) {
    return {
      report_date: reportDate,
      company_name: this.config.company_name || 'Easycom',
      status_health: '⚪ NO DATA',
      financials: { gross_gmv: 0, net_revenue: 0, aov: 0, currency: this.currency },
      volume: { total_orders: 0, valid_orders: 0, total_units: 0, units_per_order: 1.0 },
      fulfillment: { fulfilled_count: 0, fulfillment_rate_pct: 0, pending_dispatch_count: 0 },
      returns_and_cancellations: { total_returns_count: 0, customer_returns_count: 0, rto_returns_count: 0, return_rate_pct: 0, cancelled_count: 0, cancellation_rate_pct: 0 },
      payments: { prepaid_count: 0, cod_count: 0, prepaid_pct: 0, cod_pct: 0 },
      inventory: { out_of_stock_skus: 0, low_stock_skus: 0 },
      channels: [],
      alerts: []
    };
  }
}
