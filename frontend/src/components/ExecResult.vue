<template>
  <div class="exec-result-markdown">
    <div v-if="loading" class="text-center">
      Loading...
    </div>
    <div v-else-if="error" class="alert alert-danger">
      {{ error }}
    </div>
    <div v-else>
      <div class="markdown-content" v-html="renderedMarkdown"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useStorage } from "@vueuse/core";
import axios from "axios";
import { getApiUrlPath } from "../utils/api";

// markdown-it을 동적으로 import하여 안전하게 처리
let MarkdownIt = null;
let md = null;

const initMarkdownIt = async () => {
  try {
    if (!MarkdownIt) {
      const markdownItModule = await import('markdown-it');
      MarkdownIt = markdownItModule.default;
    }
    if (!md && MarkdownIt) {
      md = new MarkdownIt({
        html: true,
        linkify: true,
        typographer: true
      });
    }
  } catch (err) {
    console.error("Failed to initialize markdown-it:", err);
  }
};

const router = useRouter();
const source = ref("### No result");
const loading = ref(false);
const error = ref("");

const isAuthorized = useStorage("is_authorized", false, sessionStorage);

const getExecResult = async () => {
  loading.value = true;
  error.value = "";
  try {
    const path = getApiUrlPath() + "/exec_result";
    const res = await axios.get(path);
    if (res.data && res.data.exec_result) {
      source.value = res.data.exec_result;
    } else {
      source.value = "### No execution result available";
    }
  } catch (err) {
    error.value = `Error loading execution result: ${err.message}`;
    source.value = "### Error loading execution result";
  } finally {
    loading.value = false;
  }
};

// 마크다운을 HTML로 변환
const renderedMarkdown = computed(() => {
  try {
    if (!source.value) {
      return "";
    }
    if (!md) {
      return source.value;
    }
    return md.render(source.value);
  } catch (err) {
    console.error("Markdown rendering error:", err);
    return source.value || "";
  }
});

onMounted(async () => {
  await initMarkdownIt();
  if (isAuthorized.value) {
    getExecResult();
  } else {
    router.push("/login");
  }
});
</script>

<style>
.exec-result-markdown {
  max-width: 900px;
  margin: 5px 0;
  padding: 14px 1rem;
  min-height: 60vh;
  text-align: left !important;
}

.markdown-content {
  font-size: 0.85rem;
  line-height: 1.5;
  word-break: break-all;
  text-align: left !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.markdown-content * {
  text-align: left !important;
}

.markdown-content h1,
.markdown-content h2,
.markdown-content h3,
.markdown-content h4,
.markdown-content h5,
.markdown-content h6 {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: bold;
  text-align: left !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.markdown-content h1 { font-size: 1.5em; }
.markdown-content h2 { font-size: 1.3em; }
.markdown-content h3 { font-size: 1.1em; }
.markdown-content h4 { font-size: 1em; }
.markdown-content h5 { font-size: 0.9em; }
.markdown-content h6 { font-size: 0.8em; }

.markdown-content ul,
.markdown-content ol {
  padding-left: 2em;
  margin: 0.5em 0;
  text-align: left !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.markdown-content li {
  margin: 0;
  text-align: left !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.markdown-content p {
  margin: 0.5em 0;
  text-align: left !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

@media (max-width: 600px) {
  .exec-result-markdown {
    padding: 1rem 0.2rem;
    font-size: 0.8rem;
  }
  .markdown-content {
    font-size: 0.8rem;
  }
}
</style>
