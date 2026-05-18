/**
 * Dependency-pinning test for the `@fortawesome/*` family.
 *
 * Pinned packages (used by frontend production code):
 *   @fortawesome/fontawesome-svg-core    -- `library` singleton with .add(...)
 *   @fortawesome/vue-fontawesome         -- <FontAwesomeIcon> Vue component
 *   @fortawesome/free-solid-svg-icons    -- faUserCircle/faRotateRight/faSearch/etc.
 *   @fortawesome/free-regular-svg-icons  -- faTrashAlt/faSave
 *   @fortawesome/free-brands-svg-icons   -- faFacebook
 *
 * Reference call sites:
 *   src/App.vue:104-109
 *   src/components/Login.vue:104-117      library.add(faFacebook, faRotateRight)
 *   src/components/ToastNotification.vue  library.add(faCircleCheck, faCircleXmark,
 *                                                     faTriangleExclamation, faCircleInfo)
 *   src/components/FeedManagement.vue:496/506/512
 *   src/components/Search.vue:123-127     library.add(faSearch)
 *   src/components/Problems.vue:1056-1060 library.add(faTrashAlt)
 *
 * A FontAwesome upgrade that renames any of these specific icon exports
 * or drops `library.add(...)` would break the icons rendered across the
 * navbar / toasts / forms.
 */

import { library } from "@fortawesome/fontawesome-svg-core";
import { faFacebook } from "@fortawesome/free-brands-svg-icons";
import { faSave, faTrashAlt } from "@fortawesome/free-regular-svg-icons";
import {
  faCircleCheck,
  faCircleInfo,
  faCircleXmark,
  faRotateRight,
  faSearch,
  faTriangleExclamation,
  faUserCircle,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { createApp, h } from "vue";

describe("@fortawesome/fontawesome-svg-core: library singleton", () => {
  test("library is an object with an add() method", () => {
    expect(library).toBeTruthy();
    expect(typeof library.add).toBe("function");
  });
});

describe("@fortawesome/vue-fontawesome: FontAwesomeIcon component", () => {
  test("FontAwesomeIcon is a Vue component value (object or function)", () => {
    expect(FontAwesomeIcon).toBeTruthy();
    const t = typeof FontAwesomeIcon;
    expect(t === "object" || t === "function").toBe(true);
  });

  test("FontAwesomeIcon is registrable via app.component()", () => {
    const app = createApp({ render: () => h("div") });
    expect(() =>
      app.component("FontAwesomeIcon", FontAwesomeIcon),
    ).not.toThrow();
  });
});

describe("icon-package named exports (one per production-imported icon)", () => {
  const ICONS = {
    // free-solid-svg-icons -- the largest set
    faUserCircle,
    faRotateRight,
    faSearch,
    faCircleCheck,
    faCircleXmark,
    faCircleInfo,
    faTriangleExclamation,
    // free-regular-svg-icons
    faTrashAlt,
    faSave,
    // free-brands-svg-icons
    faFacebook,
  };

  test.each(Object.entries(ICONS))("%s is exported (truthy)", (name, icon) => {
    expect(icon).toBeTruthy();
  });

  test.each(Object.entries(ICONS))(
    "%s has iconName + prefix + icon definition fields",
    (name, icon) => {
      // FontAwesome icon objects expose at minimum these fields, which
      // `library.add()` reads internally. If the shape ever changes, library
      // registration silently no-ops.
      expect(typeof icon.iconName).toBe("string");
      expect(typeof icon.prefix).toBe("string");
      expect(Array.isArray(icon.icon)).toBe(true);
    },
  );
});

describe("library.add(...) accepts all production-used icons", () => {
  test("library.add does not throw when given the full production icon list", () => {
    // Combines every library.add(...) call seen across components.
    expect(() =>
      library.add(
        faUserCircle,
        faFacebook,
        faRotateRight,
        faSearch,
        faTrashAlt,
        faSave,
        faCircleCheck,
        faCircleXmark,
        faTriangleExclamation,
        faCircleInfo,
      ),
    ).not.toThrow();
  });
});
