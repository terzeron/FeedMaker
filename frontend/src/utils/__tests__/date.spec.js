import {
  getShortDate,
  formatDate,
  getCurrentDate,
  getDaysDifference,
} from "@/utils/date";

describe("utils/date", () => {
  const fixed = new Date("2024-01-15T12:34:56Z");

  beforeAll(() => {
    jest.useFakeTimers();
    jest.setSystemTime(fixed);
  });

  afterAll(() => {
    jest.useRealTimers();
  });

  describe("getShortDate", () => {
    it("returns empty string for falsy input", () => {
      expect(getShortDate("")).toBe("");
      expect(getShortDate(null)).toBe("");
      expect(getShortDate(undefined)).toBe("");
    });

    it("extracts date from ISO 8601 format", () => {
      expect(getShortDate("2024-02-03T10:00:00Z")).toBe("2024-02-03");
      expect(getShortDate("2024-12-31T23:59:59+09:00")).toBe("2024-12-31");
    });

    it("returns YYYY-MM-DD as-is", () => {
      expect(getShortDate("2024-02-03")).toBe("2024-02-03");
    });

    it("parses other date formats via Date constructor", () => {
      const result = getShortDate("Feb 3, 2024");
      // UTC 변환으로 인한 날짜 차이 허용
      expect(result).toMatch(/^2024-02-0[23]$/);
    });

    it("returns empty string for invalid date", () => {
      expect(getShortDate("invalid")).toBe("");
      expect(getShortDate("not-a-date")).toBe("");
    });

    it("returns empty string when Date constructor throws", () => {
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const originalDate = global.Date;
      const OriginalDate = Date;
      // Override Date so getTime returns valid but toISOString throws
      // Input must: not contain 'T', not match YYYY-MM-DD, reach try block
      global.Date = class extends OriginalDate {
        constructor(...args) {
          super(...args);
          if (args.length === 1 && args[0] === "Jan 1, 2024 FORCE") {
            this.getTime = () => 1704067200000;
            this.toISOString = () => {
              throw new Error("Forced error");
            };
          }
        }
      };
      expect(getShortDate("Jan 1, 2024 FORCE")).toBe("");
      expect(consoleErrorSpy).toHaveBeenCalled();
      global.Date = originalDate;
      consoleErrorSpy.mockRestore();
    });
  });

  describe("formatDate", () => {
    it("returns empty string for falsy input", () => {
      expect(formatDate("")).toBe("");
      expect(formatDate(null)).toBe("");
    });

    it("formats date with short format", () => {
      const result = formatDate("2024-02-03", "short");
      expect(result).toMatch(/2024/);
    });

    it("formats date with long format", () => {
      const result = formatDate("2024-02-03", "long");
      expect(result).toMatch(/2024/);
    });

    it("formats date with time format", () => {
      const result = formatDate("2024-02-03T10:30:00Z", "time");
      expect(result).toMatch(/2024/);
    });

    it("uses short format as default", () => {
      const result = formatDate("2024-02-03");
      expect(result).toMatch(/2024/);
    });

    it("falls back to short for unknown format", () => {
      const result = formatDate("2024-02-03", "unknown");
      expect(result).toMatch(/2024/);
    });

    it("returns empty string for invalid date", () => {
      expect(formatDate("invalid")).toBe("");
    });

    it("returns empty string when formatting throws", () => {
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const originalDate = global.Date;
      const OriginalDate = Date;
      global.Date = class extends OriginalDate {
        constructor(...args) {
          if (args.length === 1 && args[0] === "FORMAT_THROW") {
            throw new Error("Format error");
          }
          super(...args);
        }
      };
      expect(formatDate("FORMAT_THROW")).toBe("");
      global.Date = originalDate;
      consoleErrorSpy.mockRestore();
    });
  });

  describe("getCurrentDate", () => {
    it("returns current date in YYYY-MM-DD", () => {
      expect(getCurrentDate()).toBe("2024-01-15");
    });
  });

  describe("getDaysDifference", () => {
    it("calculates difference between two dates", () => {
      expect(getDaysDifference("2024-01-10", "2024-01-15")).toBe(5);
    });

    it("uses current date as default end date", () => {
      // Math.ceil + 타임존 차이로 인해 5~6 허용
      const result = getDaysDifference("2024-01-10");
      expect(result).toBeGreaterThanOrEqual(5);
      expect(result).toBeLessThanOrEqual(6);
    });

    it("returns absolute difference regardless of order", () => {
      expect(getDaysDifference("2024-01-20", "2024-01-15")).toBe(5);
    });

    it("returns 0 for invalid start date", () => {
      expect(getDaysDifference("invalid", "2024-01-15")).toBe(0);
    });

    it("returns 0 for invalid end date", () => {
      expect(getDaysDifference("2024-01-15", "invalid")).toBe(0);
    });

    it("returns 0 when calculation throws", () => {
      const consoleErrorSpy = jest
        .spyOn(console, "error")
        .mockImplementation(() => {});
      const originalDate = global.Date;
      const OriginalDate = Date;
      global.Date = class extends OriginalDate {
        constructor(...args) {
          if (args.length === 1 && args[0] === "DIFF_THROW") {
            throw new Error("Diff error");
          }
          super(...args);
        }
      };
      expect(getDaysDifference("DIFF_THROW")).toBe(0);
      global.Date = originalDate;
      consoleErrorSpy.mockRestore();
    });
  });
});
