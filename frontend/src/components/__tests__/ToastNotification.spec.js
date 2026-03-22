import { mount } from "@vue/test-utils";
import ToastNotification from "../ToastNotification.vue";

const stubs = {
  "font-awesome-icon": {
    template: '<i :class="icon"></i>',
    props: ["icon"],
  },
  Teleport: { template: "<div><slot /></div>" },
};

describe("ToastNotification.vue", () => {
  const createWrapper = (type, message = "Test message") => {
    return mount(ToastNotification, {
      props: {
        notification: { show: true, type, message },
      },
      global: { stubs },
    });
  };

  it("renders with success type (text-bg-success class and circle-check icon)", () => {
    const wrapper = createWrapper("success");
    const toast = wrapper.find(".toast");
    expect(toast.classes()).toContain("text-bg-success");
    expect(wrapper.text()).toContain("Test message");
    // Check icon prop passed to font-awesome-icon
    const icon = wrapper.findComponent(stubs["font-awesome-icon"]);
    expect(icon.props("icon")).toEqual(["fa", "circle-check"]);
  });

  it("renders with error type (text-bg-danger class and circle-xmark icon)", () => {
    const wrapper = createWrapper("error");
    const toast = wrapper.find(".toast");
    expect(toast.classes()).toContain("text-bg-danger");
    const icon = wrapper.findComponent(stubs["font-awesome-icon"]);
    expect(icon.props("icon")).toEqual(["fa", "circle-xmark"]);
  });

  it("renders with warning type (text-bg-warning text-dark class and triangle-exclamation icon)", () => {
    const wrapper = createWrapper("warning");
    const toast = wrapper.find(".toast");
    expect(toast.classes()).toContain("text-bg-warning");
    expect(toast.classes()).toContain("text-dark");
    const icon = wrapper.findComponent(stubs["font-awesome-icon"]);
    expect(icon.props("icon")).toEqual(["fa", "triangle-exclamation"]);
  });

  it("renders with info type (text-bg-info class and circle-info icon)", () => {
    const wrapper = createWrapper("info");
    const toast = wrapper.find(".toast");
    expect(toast.classes()).toContain("text-bg-info");
    const icon = wrapper.findComponent(stubs["font-awesome-icon"]);
    expect(icon.props("icon")).toEqual(["fa", "circle-info"]);
  });

  it("renders with unknown type (defaults to info)", () => {
    const wrapper = createWrapper("unknown-type");
    const toast = wrapper.find(".toast");
    expect(toast.classes()).toContain("text-bg-info");
    const icon = wrapper.findComponent(stubs["font-awesome-icon"]);
    expect(icon.props("icon")).toEqual(["fa", "circle-info"]);
  });

  it("emits hide when close button is clicked", async () => {
    const wrapper = createWrapper("success");
    const closeBtn = wrapper.find(".btn-close");
    await closeBtn.trigger("click");
    expect(wrapper.emitted("hide")).toBeTruthy();
    expect(wrapper.emitted("hide").length).toBe(1);
  });

  it("does not render toast when notification.show is false", () => {
    const wrapper = mount(ToastNotification, {
      props: {
        notification: { show: false, type: "success", message: "Hidden" },
      },
      global: { stubs },
    });
    expect(wrapper.find(".toast").exists()).toBe(false);
  });
});
