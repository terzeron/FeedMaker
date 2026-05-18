/**
 * Dependency-pinning test for the external dependency `dompurify`.
 *
 * Purpose
 * -------
 * Pin the DOMPurify XSS-sanitization surface used by Search.vue and
 * ExecResult.vue. A dompurify upgrade that renames `sanitize`, changes
 * ALLOWED_TAGS / ALLOWED_ATTR semantics, or stops stripping `<script>` /
 * `onerror` would silently re-introduce XSS. This is a SECURITY-CRITICAL
 * pin.
 *
 * Reference call sites:
 *   src/components/Search.vue:210
 *     DOMPurify.sanitize(rawHtml, {
 *       ALLOWED_TAGS: ["a", "b", "i", "em", "strong", "span", "div", "p",
 *                      "br", "ul", "ol", "li", "img"],
 *       ALLOWED_ATTR: ["href", "src", "alt", "title", "class", "target", "rel"],
 *     });
 *   src/components/ExecResult.vue:89
 *     DOMPurify.sanitize(md.render(source.value), {
 *       ALLOWED_TAGS: ["h1"..."img"],
 *       ALLOWED_ATTR: ["href", "src", "alt", "title", "class", "id", "target", "rel"],
 *     });
 */

import DOMPurify from "dompurify";

describe("dompurify: import surface", () => {
  test("default export exposes sanitize() as a function", () => {
    expect(typeof DOMPurify.sanitize).toBe("function");
  });
});

describe("dompurify: sanitize(html) with no options (defaults)", () => {
  test("strips <script> by default", () => {
    const out = DOMPurify.sanitize("<p>hi</p><script>alert(1)</script>");
    expect(out.toLowerCase()).not.toContain("<script");
    expect(out).toContain("<p>hi</p>");
  });

  test("strips inline event handlers like onerror", () => {
    const out = DOMPurify.sanitize('<img src="x" onerror="alert(1)">');
    expect(out.toLowerCase()).not.toContain("onerror");
  });

  test("strips javascript: URI in href", () => {
    const out = DOMPurify.sanitize('<a href="javascript:alert(1)">click</a>');
    expect(out.toLowerCase()).not.toContain("javascript:");
  });
});

describe("dompurify: sanitize(html, { ALLOWED_TAGS, ALLOWED_ATTR })", () => {
  // The exact option shape used by Search.vue and ExecResult.vue.
  const SEARCH_OPTS = {
    ALLOWED_TAGS: [
      "a",
      "b",
      "i",
      "em",
      "strong",
      "span",
      "div",
      "p",
      "br",
      "ul",
      "ol",
      "li",
      "img",
    ],
    ALLOWED_ATTR: ["href", "src", "alt", "title", "class", "target", "rel"],
  };

  test("tags NOT in ALLOWED_TAGS are stripped (script kept out)", () => {
    const out = DOMPurify.sanitize(
      "<p>ok</p><script>evil()</script>",
      SEARCH_OPTS,
    );
    expect(out).toContain("<p>ok</p>");
    expect(out.toLowerCase()).not.toContain("<script");
  });

  test("tags NOT in ALLOWED_TAGS are stripped (iframe kept out)", () => {
    // <iframe> is not in the allowlist; it must not survive.
    const out = DOMPurify.sanitize(
      '<iframe src="https://evil"></iframe><p>ok</p>',
      SEARCH_OPTS,
    );
    expect(out.toLowerCase()).not.toContain("<iframe");
    expect(out).toContain("<p>ok</p>");
  });

  test("allowed tags survive", () => {
    const html =
      '<a href="https://example.com" target="_blank" rel="noopener">link</a><strong>bold</strong>';
    const out = DOMPurify.sanitize(html, SEARCH_OPTS);
    expect(out).toContain("<a ");
    expect(out).toContain("<strong>bold</strong>");
  });

  test("attributes NOT in ALLOWED_ATTR are stripped", () => {
    // `style` is not in the allowlist -- must be removed.
    const out = DOMPurify.sanitize(
      '<p style="color:red" class="ok">x</p>',
      SEARCH_OPTS,
    );
    expect(out.toLowerCase()).not.toContain("style=");
    expect(out).toContain('class="ok"');
  });

  test("allowed attributes survive on allowed tags", () => {
    const out = DOMPurify.sanitize(
      '<img src="https://example.com/x.jpg" alt="x" title="t" />',
      SEARCH_OPTS,
    );
    expect(out).toContain("src=");
    expect(out).toContain("alt=");
    expect(out).toContain("title=");
  });
});

describe("dompurify: ExecResult markdown output options", () => {
  const EXEC_OPTS = {
    ALLOWED_TAGS: [
      "h1",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "p",
      "div",
      "blockquote",
      "pre",
      "code",
      "ul",
      "ol",
      "li",
      "table",
      "thead",
      "tbody",
      "tr",
      "th",
      "td",
      "a",
      "strong",
      "em",
      "b",
      "i",
      "del",
      "ins",
      "span",
      "br",
      "hr",
      "img",
    ],
    ALLOWED_ATTR: [
      "href",
      "src",
      "alt",
      "title",
      "class",
      "id",
      "target",
      "rel",
    ],
  };

  test("table tags are preserved (markdown table output)", () => {
    const html =
      "<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>d</td></tr></tbody></table>";
    const out = DOMPurify.sanitize(html, EXEC_OPTS);
    expect(out).toContain("<table>");
    expect(out).toContain("<th>h</th>");
    expect(out).toContain("<td>d</td>");
  });

  test("id attribute is allowed here but not in the search-options set", () => {
    // ExecResult allows `id`; Search doesn't.
    const out = DOMPurify.sanitize('<div id="anchor">x</div>', EXEC_OPTS);
    expect(out).toContain('id="anchor"');
  });
});
