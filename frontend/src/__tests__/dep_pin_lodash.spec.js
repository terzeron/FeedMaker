/**
 * Dependency-pinning test for the external dependency `lodash`.
 *
 * Purpose
 * -------
 * Pin the lodash functions Problems.vue uses for table data transforms.
 * A lodash upgrade that changes orderBy's signature or map/filter
 * callback shape would silently break the problems dashboard.
 *
 * Reference call sites:
 *   src/components/Problems.vue:1243  _.orderBy(data, [sortBy], [sortDesc ? 'desc' : 'asc'])
 *   src/components/Problems.vue:1407+ _.map(result, (o) => ...)
 *   src/components/Problems.vue:1485  _.filter(result, (o) => ...)
 */

import _ from "lodash";

describe("lodash: import surface", () => {
  test("default export exposes orderBy / map / filter", () => {
    expect(typeof _.orderBy).toBe("function");
    expect(typeof _.map).toBe("function");
    expect(typeof _.filter).toBe("function");
  });
});

describe("lodash: _.orderBy(collection, fields, orders)", () => {
  test("orderBy(rows, [key], ['asc']) sorts ascending", () => {
    // Problems.vue:1243 -- _.orderBy(data, [sortBy], [sortDesc ? 'desc' : 'asc'])
    const data = [{ n: 3 }, { n: 1 }, { n: 2 }];
    const sorted = _.orderBy(data, ["n"], ["asc"]);
    expect(sorted.map((x) => x.n)).toEqual([1, 2, 3]);
  });

  test("orderBy(rows, [key], ['desc']) sorts descending", () => {
    const data = [{ n: 1 }, { n: 3 }, { n: 2 }];
    const sorted = _.orderBy(data, ["n"], ["desc"]);
    expect(sorted.map((x) => x.n)).toEqual([3, 2, 1]);
  });

  test("orderBy does not mutate the input array", () => {
    const data = [{ n: 2 }, { n: 1 }];
    _.orderBy(data, ["n"], ["asc"]);
    expect(data.map((x) => x.n)).toEqual([2, 1]);
  });
});

describe("lodash: _.map(collection, iteratee)", () => {
  test("map(array, fn) returns a new array with transformed elements", () => {
    // Problems.vue:1407 -- _.map(result, (o) => { return { ... }; })
    const result = _.map([1, 2, 3], (x) => x * 10);
    expect(result).toEqual([10, 20, 30]);
  });

  test("map(object, fn) iterates values", () => {
    // Problems.vue:1577 -- _.map(htmlFileSizeMap, (o) => ...)  with an object input
    const out = _.map({ a: 1, b: 2 }, (v) => v + 100);
    expect(out.sort()).toEqual([101, 102]);
  });
});

describe("lodash: _.filter(collection, predicate)", () => {
  test("filter(array, fn) returns elements matching the predicate", () => {
    // Problems.vue:1485 -- _.filter(result, (o) => { return ...; })
    const out = _.filter([1, 2, 3, 4], (x) => x % 2 === 0);
    expect(out).toEqual([2, 4]);
  });

  test("filter(array, fn) returns empty array when nothing matches", () => {
    const out = _.filter([1, 2, 3], (x) => x > 100);
    expect(out).toEqual([]);
  });
});
