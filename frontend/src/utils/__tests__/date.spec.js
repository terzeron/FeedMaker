import { getShortDate, formatDate, getCurrentDate, getDaysDifference } from '@/utils/date';

describe('utils/date', () => {
  const fixed = new Date('2024-01-15T12:34:56Z');

  beforeAll(() => {
    jest.useFakeTimers();
    jest.setSystemTime(fixed);
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  it('getShortDate handles ISO and plain formats', () => {
    expect(getShortDate('2024-02-03T10:00:00Z')).toBe('2024-02-03');
    expect(getShortDate('2024-02-03')).toBe('2024-02-03');
    expect(getShortDate('invalid')).toBe('');
  });

  it('formatDate returns expected formats', () => {
    expect(formatDate('2024-02-03', 'short')).toMatch(/2024/);
    expect(formatDate('2024-02-03', 'long')).toMatch(/2024/);
    expect(formatDate('2024-02-03', 'time')).toMatch(/2024/);
    expect(formatDate('invalid')).toBe('');
  });

  it('getCurrentDate uses system time', () => {
    expect(getCurrentDate()).toBe('2024-01-15');
  });

  it('getDaysDifference calculates days', () => {
    expect(getDaysDifference('2024-01-10', '2024-01-15')).toBe(5);
    expect(getDaysDifference('invalid', '2024-01-15')).toBe(0);
  });
});

