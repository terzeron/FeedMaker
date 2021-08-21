<template>
  <b-button variant="outline-secondary" @click="onClick" v-if="showButton">
    {{ label }}
    <b-spinner small label="saving..." v-show="showSpinner"></b-spinner>
    <font-awesome-icon
      :icon="['far', 'check-circle']" v-if="showCheck"/>
  </b-button>
</template>

<script>
export default {
  name: 'Button',
  data() {
    return {
      label: '',
      onClick: undefined,
      showButton: true,
      showSpinner: true,
      showCheck: true,
    }
  }
};
</script>
