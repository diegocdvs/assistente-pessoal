import { Firestore, Timestamp } from '@google-cloud/firestore';

export class FirestoreAttemptStore {
  constructor({ firestore = new Firestore(), collectionPrefix = 'webhook_monitor' } = {}) {
    this.firestore = firestore;
    this.attempts = firestore.collection(`${collectionPrefix}_attempts`);
    this.incidents = firestore.collection(`${collectionPrefix}_incidents`);
    this.cooldowns = firestore.collection(`${collectionPrefix}_cooldowns`);
  }

  async saveAttempt(attempt) {
    await this.attempts.doc(attempt.id).set({
      ...attempt,
      attemptAt: Timestamp.fromDate(new Date(attempt.attemptAt))
    });
    return attempt;
  }

  async getRecentAttempts(key, { lookbackMinutes = 10, now = new Date() } = {}) {
    const cutoff = new Date(now.getTime() - lookbackMinutes * 60 * 1000);

    const snapshot = await this.attempts
      .where('key', '==', key)
      .where('attemptAt', '>=', Timestamp.fromDate(cutoff))
      .orderBy('attemptAt', 'asc')
      .get();

    return snapshot.docs.map((doc) => {
      const data = doc.data();
      return {
        id: doc.id,
        ...data,
        attemptAt: data.attemptAt?.toDate?.().toISOString?.() || data.attemptAt
      };
    });
  }

  async isInCooldown(key, { now = new Date() } = {}) {
    const doc = await this.cooldowns.doc(key).get();
    if (!doc.exists) return false;

    const data = doc.data();
    const until = data.cooldownUntil?.toDate?.() || new Date(data.cooldownUntil);
    return until.getTime() > now.getTime();
  }

  async setCooldown(key, { cooldownMinutes = 30, now = new Date() } = {}) {
    const cooldownUntil = new Date(now.getTime() + cooldownMinutes * 60 * 1000);
    await this.cooldowns.doc(key).set({
      key,
      cooldownUntil: Timestamp.fromDate(cooldownUntil),
      updatedAt: Timestamp.fromDate(now)
    });
    return cooldownUntil;
  }

  async createIncident(incident) {
    await this.incidents.doc(incident.id).set({
      ...incident,
      firstAttemptAt: Timestamp.fromDate(new Date(incident.firstAttemptAt)),
      lastAttemptAt: Timestamp.fromDate(new Date(incident.lastAttemptAt)),
      createdAt: Timestamp.fromDate(new Date(incident.createdAt))
    });

    return incident;
  }
}
