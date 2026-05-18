/**
 * Dependency-pinning test for the external dependency `markdown-it`.
 *
 * Purpose
 * -------
 * Pin the markdown-it surface used by ExecResult.vue's dynamic-import
 * markdown rendering pipeline. A markdown-it upgrade that drops the
 * `default` interop, renames `render`, or changes how `html: true`
 * passes through raw HTML would break the exec-result view's markdown
 * output (and the XSS guarantee paired with DOMPurify).
 *
 * Reference call sites:
 *   src/components/ExecResult.vue:36-44
 *     const markdownItModule = await import('markdown-it');
 *     MarkdownIt = markdownItModule.default;
 *     md = new MarkdownIt({ html: true, linkify: true, typographer: true });
 *   src/components/ExecResult.vue:89
 *     DOMPurify.sanitize(md.render(source.value), { ALLOWED_TAGS: [...], ... });
 */

describe("markdown-it: dynamic import + .default interop", () => {
  test("await import('markdown-it') exposes a .default constructor", async () => {
    // ExecResult.vue:36-37 -- const mod = await import('markdown-it'); MarkdownIt = mod.default;
    const mod = await import("markdown-it");
    expect(mod).toBeTruthy();
    expect(typeof mod.default).toBe("function");
  });
});

describe("markdown-it: new MarkdownIt(options) constructor", () => {
  let MarkdownIt;
  beforeAll(async () => {
    const mod = await import("markdown-it");
    MarkdownIt = mod.default;
  });

  test("accepts { html, linkify, typographer } options object", () => {
    // ExecResult.vue:40-44
    const md = new MarkdownIt({ html: true, linkify: true, typographer: true });
    expect(md).toBeTruthy();
    expect(typeof md.render).toBe("function");
  });
});

describe("markdown-it: md.render(source) output shape", () => {
  let md;
  beforeAll(async () => {
    const { default: MarkdownIt } = await import("markdown-it");
    md = new MarkdownIt({ html: true, linkify: true, typographer: true });
  });

  test("render('# h') wraps text in an <h1> tag", () => {
    const out = md.render("# Heading");
    expect(out).toContain("<h1>");
    expect(out).toContain("Heading");
  });

  test("render('* a\\n* b') produces an unordered list", () => {
    const out = md.render("* a\n* b\n");
    expect(out).toContain("<ul>");
    expect(out).toContain("<li>a</li>");
    expect(out).toContain("<li>b</li>");
  });

  test("html: true passes raw HTML through (DOMPurify is the gate afterwards)", () => {
    // The production pipeline relies on markdown-it NOT escaping <div>; the
    // sanitizer downstream is what enforces safety. If markdown-it ever flips
    // the default to escape HTML, the pipeline still works but the sanitizer
    // pairing assumption needs review -- so we pin the current behavior.
    const out = md.render('<div class="raw">x</div>');
    expect(out).toContain('<div class="raw">');
  });

  test("render returns a string (DOMPurify.sanitize expects a string)", () => {
    // ExecResult.vue:89 -- DOMPurify.sanitize(md.render(source.value), { ... })
    expect(typeof md.render("text")).toBe("string");
  });
});
