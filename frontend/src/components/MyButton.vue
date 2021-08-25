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
import {library} from '@fortawesome/fontawesome-svg-core'
import {faCheckCircle} from '@fortawesome/free-regular-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome'

library.add(faCheckCircle);

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
