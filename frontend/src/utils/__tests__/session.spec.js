import session from '@/utils/session';

describe('utils/session', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe('set', () => {
    it('stores JSON-serialized value', () => {
      session.set('k', { a: 1 });
      expect(JSON.parse(localStorage.getItem('k'))).toEqual({ a: 1 });
    });

    it('handles storage error gracefully', () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const setItemSpy = jest.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
        throw new Error('QuotaExceededError');
      });
      session.set('k', 'v');
      expect(consoleErrorSpy).toHaveBeenCalledWith('Session set error:', expect.any(Error));
      setItemSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('get', () => {
    it('returns parsed value', () => {
      session.set('k', { a: 1 });
      expect(session.get('k')).toEqual({ a: 1 });
    });

    it('returns default when key not found', () => {
      expect(session.get('missing')).toBeNull();
      expect(session.get('missing', 'fallback')).toBe('fallback');
    });

    it('returns default on parse error', () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const getItemSpy = jest.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
        throw new Error('SecurityError');
      });
      expect(session.get('k', 'default')).toBe('default');
      expect(consoleErrorSpy).toHaveBeenCalledWith('Session get error:', expect.any(Error));
      getItemSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('remove', () => {
    it('removes a key', () => {
      session.set('k1', 1);
      session.remove('k1');
      expect(session.has('k1')).toBe(false);
    });

    it('handles remove error gracefully', () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const removeItemSpy = jest.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
        throw new Error('SecurityError');
      });
      session.remove('k');
      expect(consoleErrorSpy).toHaveBeenCalledWith('Session remove error:', expect.any(Error));
      removeItemSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('clear', () => {
    it('clears all keys', () => {
      session.set('k1', 1);
      session.set('k2', 2);
      session.clear();
      expect(session.has('k1')).toBe(false);
      expect(session.has('k2')).toBe(false);
    });

    it('handles clear error gracefully', () => {
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      const clearSpy = jest.spyOn(Storage.prototype, 'clear').mockImplementation(() => {
        throw new Error('SecurityError');
      });
      session.clear();
      expect(consoleErrorSpy).toHaveBeenCalledWith('Session clear error:', expect.any(Error));
      clearSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });
  });

  describe('has', () => {
    it('returns true for existing key', () => {
      session.set('k', 'v');
      expect(session.has('k')).toBe(true);
    });

    it('returns false for non-existing key', () => {
      expect(session.has('missing')).toBe(false);
    });
  });
});
