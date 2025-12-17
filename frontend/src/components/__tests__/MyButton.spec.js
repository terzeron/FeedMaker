import { mount } from '@vue/test-utils';
import MyButton from '../MyButton.vue';

const stubs = {
  'font-awesome-icon': true,
  BButton: {
    template: '<button @click="$emit(\'click\', $event)"><slot /></button>'
  }
};

describe('MyButton.vue', () => {
  it('emits click when enabled', async () => {
    const wrapper = mount(MyButton, {
      props: { label: '확인', showInitialIcon: true },
      global: { stubs }
    });

    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeTruthy();
  });

  it('does not emit click when disabled', async () => {
    const wrapper = mount(MyButton, {
      props: { label: '확인', disabled: true },
      global: { stubs }
    });

    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toBeFalsy();
  });

  it('toggles spinner and icon via exposed refs', async () => {
    const wrapper = mount(MyButton, {
      props: { label: '로딩', showInitialIcon: true },
      global: { stubs }
    });

    const vm = wrapper.vm;
    // initial icon shown
    expect(vm.doShowInitialIcon).toBe(true);
    expect(vm.doShowSpinner).toBe(false);

    // show spinner, hide icon
    vm.doShowSpinner = true;
    vm.doShowInitialIcon = false;
    await wrapper.vm.$nextTick();

    expect(vm.doShowSpinner).toBe(true);
    expect(vm.doShowInitialIcon).toBe(false);
  });
});

