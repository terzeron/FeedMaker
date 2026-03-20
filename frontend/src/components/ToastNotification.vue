<template>
  <Teleport to="body">
    <div class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1080">
      <div
        v-if="notification.show"
        class="toast show align-items-center border-0"
        :class="toastClass"
        role="alert"
        aria-live="assertive"
        aria-atomic="true"
      >
        <div class="d-flex">
          <div class="toast-body">
            <font-awesome-icon :icon="toastIcon" class="me-2" />
            {{ notification.message }}
          </div>
          <button
            type="button"
            class="btn-close btn-close-white me-2 m-auto"
            aria-label="Close"
            @click="hideNotification"
          />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from "vue";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCircleCheck, faCircleXmark, faTriangleExclamation, faCircleInfo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faCircleCheck, faCircleXmark, faTriangleExclamation, faCircleInfo);

defineOptions({ name: "ToastNotification" });

const props = defineProps({
  notification: { type: Object, required: true }
});

const emit = defineEmits(["hide"]);

const hideNotification = () => emit("hide");

const toastClass = computed(() => {
  const map = {
    success: "text-bg-success",
    error: "text-bg-danger",
    warning: "text-bg-warning text-dark",
    info: "text-bg-info"
  };
  return map[props.notification.type] || "text-bg-info";
});

const toastIcon = computed(() => {
  const map = {
    success: ["fa", "circle-check"],
    error: ["fa", "circle-xmark"],
    warning: ["fa", "triangle-exclamation"],
    info: ["fa", "circle-info"]
  };
  return map[props.notification.type] || map.info;
});
</script>
