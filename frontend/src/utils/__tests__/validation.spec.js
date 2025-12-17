import { isValidEmail, isValidUrl, isRequired, minLength, maxLength, isNumber, isInteger, isPositive, inRange, isValidJson, hasValidExtension, isValidFeedName, isValidGroupName } from '@/utils/validation';

describe('utils/validation', () => {
  it('validates email', () => {
    expect(isValidEmail('a@b.com')).toBe(true);
    expect(isValidEmail('bad')).toBe(false);
  });

  it('validates url', () => {
    expect(isValidUrl('https://example.com')).toBe(true);
    expect(isValidUrl('not a url')).toBe(false);
  });

  it('required validation', () => {
    expect(isRequired('a')).toBe(true);
    expect(isRequired('')).toBe(false);
    expect(isRequired([])).toBe(false);
    expect(isRequired(['x'])).toBe(true);
    expect(isRequired({})).toBe(false);
    expect(isRequired({ a: 1 })).toBe(true);
  });

  it('length/number validations', () => {
    expect(minLength('abc', 2)).toBe(true);
    expect(minLength('a', 2)).toBe(false);
    expect(maxLength('abc', 3)).toBe(true);
    expect(maxLength('abcd', 3)).toBe(false);
    expect(isNumber('3.14')).toBe(true);
    expect(isInteger('2')).toBe(true);
    expect(isPositive('5')).toBe(true);
    expect(inRange('5', 1, 10)).toBe(true);
  });

  it('json and extensions', () => {
    expect(isValidJson('{"a":1}')).toBe(true);
    expect(isValidJson('no')).toBe(false);
    expect(hasValidExtension('a.jpg', ['jpg', 'png'])).toBe(true);
    expect(hasValidExtension('a.gif', ['jpg', 'png'])).toBe(false);
  });

  it('project-specific names', () => {
    expect(isValidFeedName('feed-01')).toBe(true);
    expect(isValidFeedName('!bad')).toBe(false);
    expect(isValidGroupName('group_1')).toBe(true);
    expect(isValidGroupName('bad name')).toBe(false);
  });
});

