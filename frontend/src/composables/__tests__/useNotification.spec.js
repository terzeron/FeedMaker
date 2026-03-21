import { useNotification } from "@/composables/useNotification";

describe("composables/useNotification", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe("showNotification", () => {
    it("shows and auto hides notification", () => {
      const { notification, showNotification } = useNotification();
      showNotification("hello", "info", 1000);
      expect(notification.value.show).toBe(true);
      expect(notification.value.message).toBe("hello");
      expect(notification.value.type).toBe("info");
      jest.advanceTimersByTime(1000);
      expect(notification.value.show).toBe(false);
    });

    it("does not auto hide when duration is 0", () => {
      const { notification, showNotification } = useNotification();
      showNotification("persistent", "info", 0);
      expect(notification.value.show).toBe(true);
      jest.advanceTimersByTime(10000);
      expect(notification.value.show).toBe(true);
    });
  });

  describe("hideNotification", () => {
    it("hides notification manually", () => {
      const { notification, showNotification, hideNotification } =
        useNotification();
      showNotification("test", "info", 0);
      expect(notification.value.show).toBe(true);
      hideNotification();
      expect(notification.value.show).toBe(false);
    });
  });

  describe("showSuccess", () => {
    it("shows success notification with default duration", () => {
      const { notification, showSuccess } = useNotification();
      showSuccess("saved");
      expect(notification.value.show).toBe(true);
      expect(notification.value.message).toBe("saved");
      expect(notification.value.type).toBe("success");
      expect(notification.value.duration).toBe(3000);
    });

    it("accepts custom duration", () => {
      const { notification, showSuccess } = useNotification();
      showSuccess("saved", 5000);
      expect(notification.value.duration).toBe(5000);
    });
  });

  describe("showError", () => {
    it("shows error notification with default duration", () => {
      const { notification, showError } = useNotification();
      showError("failed");
      expect(notification.value.show).toBe(true);
      expect(notification.value.message).toBe("failed");
      expect(notification.value.type).toBe("error");
      expect(notification.value.duration).toBe(5000);
    });
  });

  describe("showWarning", () => {
    it("shows warning notification with default duration", () => {
      const { notification, showWarning } = useNotification();
      showWarning("caution");
      expect(notification.value.show).toBe(true);
      expect(notification.value.message).toBe("caution");
      expect(notification.value.type).toBe("warning");
      expect(notification.value.duration).toBe(4000);
    });
  });

  describe("showInfo", () => {
    it("shows info notification with default duration", () => {
      const { notification, showInfo } = useNotification();
      showInfo("note");
      expect(notification.value.show).toBe(true);
      expect(notification.value.message).toBe("note");
      expect(notification.value.type).toBe("info");
      expect(notification.value.duration).toBe(3000);
    });
  });

  describe("alert and confirm", () => {
    it("alert delegates to window.alert", () => {
      const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});
      const { alert } = useNotification();
      alert("message");
      expect(alertSpy).toHaveBeenCalledWith("message");
      alertSpy.mockRestore();
    });

    it("confirm delegates to window.confirm", () => {
      const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
      const { confirm } = useNotification();
      expect(confirm("question")).toBe(true);
      expect(confirmSpy).toHaveBeenCalledWith("question");
      confirmSpy.mockRestore();
    });

    it("confirm returns false when user cancels", () => {
      const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(false);
      const { confirm } = useNotification();
      expect(confirm("question")).toBe(false);
      confirmSpy.mockRestore();
    });
  });

  describe("showNotification edge cases", () => {
    it("does not set timeout with negative duration", () => {
      const { notification, showNotification } = useNotification();
      showNotification("negative", "info", -1);
      expect(notification.value.show).toBe(true);
      expect(notification.value.duration).toBe(-1);
      jest.advanceTimersByTime(10000);
      expect(notification.value.show).toBe(true);
    });

    it("uses default type and duration when called with message only", () => {
      const { notification, showNotification } = useNotification();
      showNotification("defaults");
      expect(notification.value.show).toBe(true);
      expect(notification.value.type).toBe("info");
      expect(notification.value.duration).toBe(3000);
      jest.advanceTimersByTime(3000);
      expect(notification.value.show).toBe(false);
    });
  });
});
