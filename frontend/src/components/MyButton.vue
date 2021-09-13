<template>
  <b-button
      :variant="variant"
      @click="$emit('click')">
    {{ label }}
    <font-awesome-icon
        :icon="initialIcon"
        v-if="doShowInitialIcon"/>
    <b-spinner small v-if="doShowSpinner"></b-spinner>
  </b-button>
</template>

<script>
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'

export default {
  name: 'MyButton',
  components: {
    FontAwesomeIcon
  },
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
    initialIcon: {
      type: Array,
      default: function () {
        return [];
      }
    },
    showInitialIcon: {
      type: Boolean,
      default: false,
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
      doShowInitialIcon: this.showInitialIcon,
      doShowSpinner: this.showSpinner,
    }
  }
};
</script>
