export class MemoryAttemptStore {
  constructor() {
    this.attemptsByKey = new Map();
    this.cooldownByKey = new Map();
    this.incidents = [];
  }

  async saveAttempt(attempt) {
    const existing = this.attemptsByKey.get(attempt.key) || [];
    existing.push(attempt);
    this.attemptsByKey.set(attempt.key, existing);
    return attempt;
  }

  async getRecentAttempts(key, { lookbackMinutes = 10, now = new Date() } = {}) {
    const cutoff = now.getTime() - lookbackMinutes * 60 * 1000;
    return (this.attemptsByKey.get(key) || []).filter((attempt) => new Date(attempt.attemptAt).getTime() >= cutoff);
  }

  async isInCooldown(key, { now = new Date() } = {}) {
    const until = this.cooldownByKey.get(key);
    if (!until) return false;
    return new Date(until).getTime() > now.getTime();
  }

  async setCooldown(key, { cooldownMinutes = 30, now = new Date() } = {}) {
    const until = new Date(now.getTime() + cooldownMinutes * 60 * 1000);
    this.cooldownByKey.set(key, until.toISOString());
    return until;
  }

  async createIncident(incident) {
    this.incidents.push(incident);
    return incident;
  }
}
