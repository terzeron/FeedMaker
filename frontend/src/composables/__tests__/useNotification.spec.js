import { useNotification } from '@/composables/useNotification';

describe('composables/useNotification', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('shows and auto hides notification', () => {
    const { notification, showNotification } = useNotification();
    showNotification('hello', 'info', 1000);
    expect(notification.value.show).toBe(true);
    jest.advanceTimersByTime(1000);
    expect(notification.value.show).toBe(false);
  });

  it('alert and confirm delegate to window', () => {
    const alertSpy = jest.spyOn(window, 'alert').mockImplementation(() => {});
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    const { alert, confirm } = useNotification();
    alert('a');
    expect(alertSpy).toHaveBeenCalled();
    expect(confirm('x')).toBe(true);
    alertSpy.mockRestore();
    confirmSpy.mockRestore();
  });
});

