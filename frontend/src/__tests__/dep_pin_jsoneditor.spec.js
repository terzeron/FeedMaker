/**
 * Dependency-pinning test for the external dependency `jsoneditor`.
 *
 * Purpose
 * -------
 * Pin the JSONEditor surface used by FeedManagement.vue to edit feed
 * config JSON. A jsoneditor upgrade that renames `set`/`get`/`destroy`
 * or changes `mode/modes` option names would break the config UI.
 *
 * Reference call sites:
 *   src/components/FeedManagement.vue:508  import JSONEditor from "jsoneditor";
 *   src/components/FeedManagement.vue:1343 new JSONEditor(container, { mode, modes, onChange })
 *   src/components/FeedManagement.vue:1348 this.jsonEditor.get()
 *   src/components/FeedManagement.vue:1356 this.jsonEditor.set(this.jsonData)
 *   src/components/FeedManagement.vue:1357 this.jsonEditor.expandAll()
 *   src/components/FeedManagement.vue:1393 this.jsonEditor.destroy()
 */

import JSONEditor from "jsoneditor";

// jsoneditor needs a DOM container.
function makeContainer() {
  const c = document.createElement("div");
  document.body.appendChild(c);
  return c;
}

describe("jsoneditor: import surface", () => {
  test("default export is a constructor function/class", () => {
    expect(typeof JSONEditor).toBe("function");
  });
});

describe("jsoneditor: new JSONEditor(container, options)", () => {
  test("accepts mode/modes/onChange options used in production", () => {
    // FeedManagement.vue:1343-1353
    const container = makeContainer();
    const editor = new JSONEditor(container, {
      mode: "tree",
      modes: ["tree", "code", "text"],
      onChange: () => {},
    });
    expect(editor).toBeTruthy();
    editor.destroy();
    container.remove();
  });
});

describe("jsoneditor: set / get round-trip", () => {
  test("set(obj) then get() returns an equal-shape object", () => {
    // FeedManagement.vue:1356 + 1348
    const container = makeContainer();
    const editor = new JSONEditor(container, {
      mode: "tree",
      modes: ["tree", "code", "text"],
      onChange: () => {},
    });

    editor.set({ feed_name: "x", url_list: ["a", "b"] });
    const round = editor.get();
    expect(round).toEqual({ feed_name: "x", url_list: ["a", "b"] });

    editor.destroy();
    container.remove();
  });
});

describe("jsoneditor: expandAll and destroy methods exist", () => {
  test("editor exposes expandAll() and destroy()", () => {
    const container = makeContainer();
    const editor = new JSONEditor(container, {
      mode: "tree",
      modes: ["tree", "code", "text"],
      onChange: () => {},
    });
    editor.set({ a: 1 });
    expect(typeof editor.expandAll).toBe("function");
    expect(typeof editor.destroy).toBe("function");
    editor.expandAll(); // must not throw
    editor.destroy(); // must not throw
    container.remove();
  });
});
