/**
 * Dependency-pinning test for the external dependency `moment`.
 *
 * Purpose
 * -------
 * Pin the minimal moment() surface Problems.vue uses to format dates in
 * the dashboard. A moment upgrade that changes the format-token mapping
 * for "YY-MM-DD" or breaks `isValid()` semantics would silently corrupt
 * the table-cell display.
 *
 * Reference call sites:
 *   src/components/Problems.vue:1361  let d = moment(date);
 *   src/components/Problems.vue:1362  if (!d.isValid()) return "";
 *   src/components/Problems.vue:1365  return d.format("YY-MM-DD");
 */

import moment from "moment";

describe("moment: import surface", () => {
  test("default export is a function", () => {
    expect(typeof moment).toBe("function");
  });
});

describe("moment(date) constructor", () => {
  test("moment(iso-string) yields a valid moment", () => {
    const m = moment("2026-05-18T12:34:56Z");
    expect(m.isValid()).toBe(true);
  });

  test("moment(undefined) yields the current time (still valid)", () => {
    // Problems.vue accepts arbitrary input; we depend on isValid() catching bad shapes.
    const m = moment(undefined);
    expect(m.isValid()).toBe(true);
  });

  test("moment(bad-string) yields an invalid moment", () => {
    // Problems.vue:1362 -- `if (!d.isValid()) return "";`
    const m = moment("definitely-not-a-date");
    expect(m.isValid()).toBe(false);
  });
});

describe("moment().format('YY-MM-DD')", () => {
  test("YY-MM-DD produces a two-digit year, padded month and day", () => {
    // Problems.vue:1365 -- d.format("YY-MM-DD")
    const m = moment("2026-05-08T01:02:03Z");
    expect(m.format("YY-MM-DD")).toMatch(/^\d{2}-\d{2}-\d{2}$/);
  });

  test("YY token gives last two digits of the year", () => {
    const m = moment("2026-01-02T00:00:00Z");
    // utc to avoid timezone shift on the test runner
    expect(moment.utc("2026-01-02T00:00:00Z").format("YY")).toBe("26");
    // and the full format pattern is reachable
    expect(m.format("YY-MM-DD")).toMatch(/^26-/); // any TZ keeps the year for this date
  });
});
