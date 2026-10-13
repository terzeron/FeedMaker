import axios from "axios";

vi.mock("axios", () => ({ default: { defaults: {}, get: vi.fn() } }));
vi.mock("../router", () => ({
  default: { install: vi.fn(), beforeEach: vi.fn() },
}));

describe("main.js bootstrap", () => {
  beforeEach(() => {
    vi.resetModules();
    document.body.innerHTML = '<div id="app"></div>';
  });

  it("axios 전역 withCredentials를 켜고 #app에 앱을 마운트한다", async () => {
    await import("../main.js");
    expect(axios.defaults.withCredentials).toBe(true);
    expect(document.querySelector("#app").innerHTML).not.toBe("");
  });
});
