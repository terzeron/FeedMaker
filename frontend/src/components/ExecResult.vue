<template>
  <BContainer fluid>
    <BRow>
      <BCol cols="12">
        <VMarkdownView :source="source"></VMarkdownView>
      </BCol>
    </BRow>

    <BRow>
      <BCol cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
      </BCol>
    </BRow>
  </BContainer>
</template>

<style>
div.vue3-markdown {
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
  font-size: 1em;
}

div.markdown-body > h5 {
  font-size: 1em;
}

div.markdown-body li {
  font-size: 0.9em;
}
</style>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useStorage } from "@vueuse/core";
import axios from "axios";

const router = useRouter();
const source = ref("### No result");

const adminEmail = computed(() => {
  return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
});

const isAuthorized = useStorage("is_authorized", false, sessionStorage);

const getApiUrlPath = () => {
  return process.env.VUE_APP_API_URL;
};

const getExecResult = () => {
  const path = getApiUrlPath() + "/exec_result";
  axios
    .get(path)
    .then((res) => {
      source.value = res.data["exec_result"];
    })
    .catch((error) => {
      console.error(error);
    });
};

onMounted(() => {
  if (isAuthorized.value) {
    getExecResult();
  } else {
    router.push("/login");
  }
});
</script>
