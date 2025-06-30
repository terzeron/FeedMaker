// Simple session management utility for Vue 3
class SessionManager {
  constructor() {
    this.storage = sessionStorage;
  }

  set(key, value) {
    try {
      this.storage.setItem(key, JSON.stringify(value));
    } catch (error) {
      console.error('Session set error:', error);
    }
  }

  get(key, defaultValue = null) {
    try {
      const item = this.storage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch (error) {
      console.error('Session get error:', error);
      return defaultValue;
    }
  }

  remove(key) {
    try {
      this.storage.removeItem(key);
    } catch (error) {
      console.error('Session remove error:', error);
    }
  }

  clear() {
    try {
      this.storage.clear();
    } catch (error) {
      console.error('Session clear error:', error);
    }
  }

  has(key) {
    return this.storage.getItem(key) !== null;
  }
}

// Create global session instance
const session = new SessionManager();

export default session; 