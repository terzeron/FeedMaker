import { mount } from "@vue/test-utils";
import App from "../App.vue";

describe("App.vue", () => {
  it("renders navbar and links", () => {
    const wrapper = mount(App, {
      global: {
        stubs: {
          "router-link": { template: "<a><slot /></a>" },
          "router-view": true,
          "font-awesome-icon": true,
        },
      },
    });

    expect(wrapper.find("nav.navbar").exists()).toBe(true);
    const text = wrapper.text();
    expect(text).toContain("실행 결과");
    expect(text).toContain("문제점과 상태");
    expect(text).toContain("피드 관리");
    expect(text).toContain("사이트 검색");
  });

  it("renders profile image when profilePictureUrl is set", async () => {
    const { authStore } = require("../stores/authStore");
    authStore.state.profilePictureUrl = "https://example.com/photo.jpg";

    const wrapper = mount(App, {
      global: {
        stubs: {
          "router-link": { template: "<a><slot /></a>" },
          "router-view": true,
          "font-awesome-icon": true,
        },
      },
    });

    const img = wrapper.find(".navbar-profile-img");
    expect(img.exists()).toBe(true);
    expect(img.attributes("src")).toBe("https://example.com/photo.jpg");

    // Test onProfileImgError handler
    await img.trigger("error");
    expect(img.element.style.display).toBe("none");

    // Cleanup
    authStore.state.profilePictureUrl = null;
  });
});
