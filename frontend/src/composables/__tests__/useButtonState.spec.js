import { useButtonState } from '@/composables/useButtonState';

describe('composables/useButtonState', () => {
  const makeRefs = () => ({
    btn: { value: { doShowInitialIcon: true, doShowSpinner: false } },
    other: { value: { doShowInitialIcon: true, doShowSpinner: false } }
  });

  it('start/end button toggles flags and state', () => {
    const refs = makeRefs();
    const { startButton, endButton, isButtonLoading } = useButtonState();
    startButton('btn', refs);
    expect(refs.btn.value.doShowSpinner).toBe(true);
    expect(isButtonLoading('btn')).toBe(true);
    endButton('btn', refs);
    expect(refs.btn.value.doShowSpinner).toBe(false);
    expect(isButtonLoading('btn')).toBe(false);
  });

  it('resetAllButtons resets tracked buttons', () => {
    const refs = makeRefs();
    const { startButton, resetAllButtons } = useButtonState();
    startButton('btn', refs);
    startButton('other', refs);
    resetAllButtons(refs);
    expect(refs.btn.value.doShowSpinner).toBe(false);
    expect(refs.other.value.doShowSpinner).toBe(false);
  });
});

