<template>
  <BButton
    :variant="variant"
    :size="size"
    :disabled="disabled"
    @click="handleClick"
    :class="buttonClass"
  >
    <div
      v-if="doShowSpinner"
      class="spinner-border spinner-border-sm me-1"
      role="status"
    >
      <span class="visually-hidden">Loading...</span>
    </div>
    <font-awesome-icon
      v-if="doShowInitialIcon"
      :icon="initialIcon"
      class="me-1"
    />
    {{ label }}
  </BButton>
</template>

<script setup>
import { ref, computed, defineExpose } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

const props = defineProps({
  label: {
    type: String,
    default: "버튼",
  },
  variant: {
    type: String,
    default: "primary",
  },
  size: {
    type: String,
    default: "md",
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  initialIcon: {
    type: Array,
    default: () => [],
  },
  showInitialIcon: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["click"]);

const doShowSpinner = ref(false);
const doShowInitialIcon = ref(props.showInitialIcon || false);

const buttonClass = computed(() => {
  return {
    "btn-loading": doShowSpinner.value,
  };
});

const handleClick = async (event) => {
  if (props.disabled) return;

  // 클릭 시 자동으로 스피너를 보여주지 않음 (외부에서 제어)
  emit("click", event);
};

// 외부에서 접근할 수 있도록 ref들을 노출
defineExpose({
  doShowSpinner,
  doShowInitialIcon
});

// 디버깅을 위한 watch 추가
import { watch } from 'vue';

watch(doShowSpinner, (newVal) => {
  console.log('MyButton doShowSpinner changed to:', newVal);
});

watch(doShowInitialIcon, (newVal) => {
  console.log('MyButton doShowInitialIcon changed to:', newVal);
});
</script>

<style scoped>
.btn-loading {
  pointer-events: none;
}
</style>
