/**
 * Dependency-pinning test for the external dependency `dayjs`.
 *
 * Purpose
 * -------
 * Pin the minimal dayjs surface Problems.vue uses to format dates in the
 * dashboard. (Migrated from `moment` because moment is in maintenance
 * mode; dayjs has an API-compatible subset for these calls.) A dayjs
 * upgrade that changes "YY-MM-DD" tokenization or `isValid()` semantics
 * would silently corrupt date cells.
 *
 * Reference call sites:
 *   src/components/Problems.vue:1054  import dayjs from "dayjs";
 *   src/components/Problems.vue:1361  let d = dayjs(date);
 *   src/components/Problems.vue:1362  if (!d.isValid()) return "";
 *   src/components/Problems.vue:1365  return d.format("YY-MM-DD");
 */

import dayjs from "dayjs";

describe("dayjs: import surface", () => {
  test("default export is a function", () => {
    expect(typeof dayjs).toBe("function");
  });
});

describe("dayjs(date) constructor", () => {
  test("dayjs(iso-string) yields a valid instance", () => {
    const d = dayjs("2026-05-18T12:34:56Z");
    expect(d.isValid()).toBe(true);
  });

  test("dayjs(undefined) yields the current time (still valid)", () => {
    // Problems.vue:1358 guards on `if (!date) return "";` before calling
    // dayjs, but the library contract still has to be predictable here.
    const d = dayjs(undefined);
    expect(d.isValid()).toBe(true);
  });

  test("dayjs(bad-string) yields an invalid instance", () => {
    // Problems.vue:1362 -- `if (!d.isValid()) return "";`
    const d = dayjs("definitely-not-a-date");
    expect(d.isValid()).toBe(false);
  });
});

describe("dayjs().format('YY-MM-DD')", () => {
  test("YY-MM-DD produces a two-digit year, padded month and day", () => {
    // Problems.vue:1365 -- d.format("YY-MM-DD")
    const d = dayjs("2026-05-08T01:02:03Z");
    expect(d.format("YY-MM-DD")).toMatch(/^\d{2}-\d{2}-\d{2}$/);
  });

  test("YY token gives the last two digits of the year (UTC-anchored)", () => {
    // Use UTC indirectly: a date that lives in year 2026 in every common
    // timezone the CI might run in.
    const d = dayjs("2026-06-15T12:00:00Z");
    expect(d.format("YY")).toBe("26");
    expect(d.format("YY-MM-DD")).toMatch(/^26-06-15$/);
  });
});
