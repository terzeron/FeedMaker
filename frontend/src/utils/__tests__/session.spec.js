import session from '@/utils/session';

describe('utils/session', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('sets and gets values', () => {
    session.set('k', { a: 1 });
    expect(session.get('k')).toEqual({ a: 1 });
    expect(session.has('k')).toBe(true);
  });

  it('removes and clears', () => {
    session.set('k1', 1);
    session.remove('k1');
    expect(session.has('k1')).toBe(false);

    session.set('k2', 2);
    session.clear();
    expect(session.has('k2')).toBe(false);
  });
});

