import {
  isValidEmail,
  isValidUrl,
  isRequired,
  minLength,
  maxLength,
  isNumber,
  isInteger,
  isPositive,
  inRange,
  isValidJson,
  hasValidExtension,
  isValidFeedName,
  isValidGroupName,
} from "@/utils/validation";

describe("utils/validation", () => {
  it("validates email", () => {
    expect(isValidEmail("a@b.com")).toBe(true);
    expect(isValidEmail("bad")).toBe(false);
  });

  it("validates url", () => {
    expect(isValidUrl("https://example.com")).toBe(true);
    expect(isValidUrl("not a url")).toBe(false);
  });

  it("required validation", () => {
    expect(isRequired("a")).toBe(true);
    expect(isRequired("")).toBe(false);
    expect(isRequired([])).toBe(false);
    expect(isRequired(["x"])).toBe(true);
    expect(isRequired({})).toBe(false);
    expect(isRequired({ a: 1 })).toBe(true);
  });

  it("length/number validations", () => {
    expect(minLength("abc", 2)).toBe(true);
    expect(minLength("a", 2)).toBe(false);
    expect(maxLength("abc", 3)).toBe(true);
    expect(maxLength("abcd", 3)).toBe(false);
    expect(isNumber("3.14")).toBe(true);
    expect(isInteger("2")).toBe(true);
    expect(isPositive("5")).toBe(true);
    expect(inRange("5", 1, 10)).toBe(true);
  });

  it("json and extensions", () => {
    expect(isValidJson('{"a":1}')).toBe(true);
    expect(isValidJson("no")).toBe(false);
    expect(hasValidExtension("a.jpg", ["jpg", "png"])).toBe(true);
    expect(hasValidExtension("a.gif", ["jpg", "png"])).toBe(false);
  });

  it("project-specific names", () => {
    expect(isValidFeedName("feed-01")).toBe(true);
    expect(isValidFeedName("!bad")).toBe(false);
    expect(isValidGroupName("group_1")).toBe(true);
    expect(isValidGroupName("bad name")).toBe(false);
  });

  it("isRequired returns true for number and boolean values", () => {
    expect(isRequired(123)).toBe(true);
    expect(isRequired(0)).toBe(false);
    expect(isRequired(true)).toBe(true);
    expect(isRequired(false)).toBe(false);
  });

  it("isRequired returns false for null and undefined", () => {
    expect(isRequired(null)).toBe(false);
    expect(isRequired(undefined)).toBe(false);
  });

  it("hasValidExtension returns false for missing filename or allowedExtensions", () => {
    expect(hasValidExtension("", ["jpg"])).toBe(false);
    expect(hasValidExtension(null, ["jpg"])).toBe(false);
    expect(hasValidExtension("file.jpg", null)).toBe(false);
    expect(hasValidExtension("file.jpg", "not-an-array")).toBe(false);
  });

  it("hasValidExtension returns true for valid extension", () => {
    expect(hasValidExtension("photo.PNG", ["jpg", "png"])).toBe(true);
    expect(hasValidExtension("doc.PDF", ["pdf"])).toBe(true);
  });

  it("isValidGroupName returns false for null/undefined/empty/invalid", () => {
    expect(isValidGroupName(null)).toBe(false);
    expect(isValidGroupName(undefined)).toBe(false);
    expect(isValidGroupName("")).toBe(false);
    expect(isValidGroupName("a")).toBe(false); // too short
    expect(isValidGroupName("bad-name")).toBe(false); // hyphen not allowed
    expect(isValidGroupName("a".repeat(31))).toBe(false); // too long
  });

  it("isValidGroupName returns true for valid names", () => {
    expect(isValidGroupName("ab")).toBe(true);
    expect(isValidGroupName("group_123")).toBe(true);
    expect(isValidGroupName("a".repeat(30))).toBe(true);
  });

  it("isValidFeedName returns false for non-string values", () => {
    expect(isValidFeedName(null)).toBe(false);
    expect(isValidFeedName(undefined)).toBe(false);
    expect(isValidFeedName(123)).toBe(false);
    expect(isValidFeedName("")).toBe(false);
    expect(isValidFeedName("a")).toBe(false); // too short
    expect(isValidFeedName("a".repeat(51))).toBe(false); // too long
  });
});
