<template>
  <BButton
    :variant="variant"
    :size="size"
    :disabled="disabled"
    @click="handleClick"
    :class="buttonClass"
  >
    <BSpinner small v-if="doShowSpinner"></BSpinner>
    <font-awesome-icon
      v-if="showInitialIcon"
      :icon="initialIcon"
      class="me-1"
    />
    {{ label }}
  </BButton>
</template>

<script setup>
import { ref, computed } from "vue";
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

const buttonClass = computed(() => {
  return {
    "btn-loading": doShowSpinner.value,
  };
});

const handleClick = async (event) => {
  if (props.disabled) return;

  doShowSpinner.value = true;
  emit("click", event);

  // 스피너를 잠시 보여줌
  setTimeout(() => {
    doShowSpinner.value = false;
  }, 500);
};
</script>

<style scoped>
.btn-loading {
  pointer-events: none;
}
</style>
