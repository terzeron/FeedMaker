<template>
  <b-container fluid>
    <b-row>
      <b-col cols="12">
        <vue-simple-markdown :source="source"></vue-simple-markdown>
      </b-col>
    </b-row>

    <b-row>
      <b-col cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
div.vue-simple-markdown {
  white-space: normal !important;
}

div.markdown-body > * {
  margin-top: 5px !important;
  margin-bottom: 5px !important;
  line-height: 1.1;
}

div.markdown-body > h1 {
  font-size: 1.3em;
  padding-bottom: 0.1em;
  margin-block-start: 0.3em;
  margin-block-end: 0.3em;
}

div.markdown-body > h2 {
  font-size: 1.2em;
  padding-bottom: 0.1em;
  margin-block-start: 0.3em;
  margin-block-end: 0.3em;
}

div.markdown-body > h3 {
  font-size: 1.1em;
}

div.markdown-body > h4 {
  font-size: 1.0em;
}

div.markdown-body > h5 {
  font-size: 1.0em;
}

div.markdown-body li {
  font-size: 0.9em;
}
</style>

<script>
import axios from 'axios';

export default {
  name: 'ExecResult',
  components: {
  },
  data: function () {
    return {
      source: '### No result',
      isLogged: false,
    }
  },
  computed: {
    adminEmail: function () {
      return process.env.VUE_APP_ADMIN_EMAIL;
    },
  },
  methods: {
    getApiUrlPath: function () {
      let path_prefix = 'https://api.terzeron.com/fm';
      if (process.env.NODE_ENV === 'development') {
        path_prefix = 'http://localhost:5000';
      }
      return path_prefix;
    },
    getExecResult: function () {
      const path = this.getApiUrlPath() + '/exec_result';
      axios.get(path)
          .then((res) => {
            this.source = res.data['exec_result'];
          })
          .catch((error) => {
            console.error(error);
          });
    },
  },
  mounted: function () {
    if (this.$session.get('is_authorized')) {
      this.getExecResult();
    } else {
      this.$router.push('/login');
    }
  },
};
</script>
