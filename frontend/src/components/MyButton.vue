<template>
  <b-button
    :variant="variant"
    @click="$emit('click')">
    {{ label }}
    <b-spinner small v-if="doShowSpinner"></b-spinner>
    <font-awesome-icon
      :icon="['far', 'check-circle']"
      v-if="doShowCheck"/>
  </b-button>
</template>

<script>
export default {
  name: 'MyButton',
  props: {
    label: {
      type: String,
      default: ''
    },
    click: {
      type: Function,
      default: undefined
    },
    variant: {
      type: String,
      default: 'info'
    },
    showSpinner: {
      type: Boolean,
      default: false,
    },
    showCheck: {
      type: Boolean,
      default: false,
    }
  },
  data: function () {
    return {
      doShowSpinner: this.showSpinner,
      doShowCheck: this.showCheck,
    }
  }
};
</script>
