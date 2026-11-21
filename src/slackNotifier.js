/**
 * Slack Webhook Notifier for Easycom Daily KPI Briefings (Node.js).
 */

export class SlackNotifier {
  constructor(webhookUrl = null) {
    this.webhookUrl = webhookUrl;
  }

  async sendKpiReport(blocks, fallbackText = 'Easycom Daily KPI Briefing') {
    if (!this.webhookUrl) {
      console.warn('[SlackNotifier] No SLACK_WEBHOOK_URL configured. Skipping broadcast.');
      return false;
    }

    const payload = {
      text: fallbackText,
      blocks: blocks
    };

    try {
      console.log(`[SlackNotifier] Sending KPI briefing to Slack incoming webhook...`);
      const res = await fetch(this.webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(15000)
      });

      if (res.ok) {
        console.log('[SlackNotifier] Successfully posted KPI briefing to Slack channel!');
        return true;
      } else {
        const errorText = await res.text();
        console.error(`[SlackNotifier] Slack API Error (${res.status}): ${errorText}`);
        return false;
      }
    } catch (err) {
      console.error('[SlackNotifier] Connection failed to Slack webhook:', err.message);
      return false;
    }
  }
}
