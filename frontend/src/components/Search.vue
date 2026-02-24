<template>
  <BContainer fluid>
    <!-- Search Window -->
    <BRow>
      <BCol cols="12" class="m-0 p-1">
        <BInputGroup class="m-0 p-1" style="width: 400px">
          <BFormInput
            v-model="searchKeyword"
            class="m-0"
            placeholder="키워드"
            @keyup.enter="search"
          >
            {{ searchKeyword }}
          </BFormInput>
          <BInputGroupText>
            <my-button
              ref="searchButton"
              label="검색"
              @click="search"
              :initial-icon="['fas', 'search']"
              :show-initial-icon="true"
              variant="dark"
            />
          </BInputGroupText>
        </BInputGroup>
      </BCol>
    </BRow>

    <!-- Search Results - Per Site Cards -->
    <BRow v-if="siteResults.length > 0">
      <BCol
        cols="12"
        md="6"
        v-for="site in siteResults"
        :key="site.name"
        class="p-1"
      >
        <BCard class="h-100">
          <template #header>
            <div class="d-flex align-items-center justify-content-between">
              <strong>{{ site.name }}</strong>
              <span v-if="site.status === 'loading'">
                <BSpinner small />
              </span>
              <span
                v-else-if="site.status === 'success' && site.html"
                class="badge bg-success"
              >
                결과 있음
              </span>
              <span
                v-else-if="site.status === 'success' && !site.html"
                class="badge bg-secondary"
              >
                결과 없음
              </span>
              <span
                v-else-if="site.status === 'error'"
                class="badge bg-danger"
              >
                오류
              </span>
            </div>
          </template>
          <BCardBody>
            <div v-if="site.status === 'loading'" class="text-muted small">
              검색 중...
            </div>
            <div
              v-else-if="site.status === 'success' && site.html"
              class="search-result-html"
              v-html="site.html"
            ></div>
            <div
              v-else-if="site.status === 'success' && !site.html"
              class="text-muted small"
            >
              이 사이트에서 결과를 찾지 못했습니다.
            </div>
            <div v-else-if="site.status === 'error'" class="text-danger small">
              {{ site.error }}
            </div>
          </BCardBody>
        </BCard>
      </BCol>
    </BRow>

    <BRow>
      <BCol cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
        <div class="text-muted small mt-1">v{{ appVersion }}</div>
      </BCol>
    </BRow>
  </BContainer>
</template>

<style scoped>
.search-result-html {
  max-height: 400px;
  overflow-y: auto;
  font-size: 0.85rem;
}

.search-result-html :deep(div) {
  padding: 4px 8px;
  margin-bottom: 2px;
}

.search-result-html :deep(a) {
  color: #0d6efd;
  text-decoration: none;
}

.search-result-html :deep(a:hover) {
  text-decoration: underline;
}
</style>

<script>
import axios from "axios";
import { getApiUrlPath } from "../utils/api";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faSearch } from "@fortawesome/free-solid-svg-icons";
import MyButton from "./MyButton";

library.add(faSearch);

export default {
  name: "SiteSearch",
  components: {
    MyButton,
  },
  props: [],
  data: function () {
    return {
      searchKeyword: "",
      siteResults: [],
      isSearching: false,
    };
  },
  computed: {
    adminEmail: function () {
      return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
    },
    appVersion: function () {
      return process.env.VUE_APP_VERSION || "dev";
    },
  },
  methods: {
    startButton: function (ref) {
      this.$refs[ref].doShowInitialIcon = false;
      this.$refs[ref].doShowSpinner = true;
    },
    endButton: function (ref) {
      this.$refs[ref].doShowInitialIcon = true;
      this.$refs[ref].doShowSpinner = false;
    },
    search: async function () {
      const keyword = this.searchKeyword.trim();
      if (!keyword || this.isSearching) return;

      this.isSearching = true;
      this.startButton("searchButton");
      this.siteResults = [];

      try {
        // 1. 사이트 목록 조회
        const namesUrl = getApiUrlPath() + "/search_sites";
        const namesRes = await axios.get(namesUrl);
        if (namesRes.data.status !== "success" || !namesRes.data.site_names) {
          return;
        }

        const siteNames = namesRes.data.site_names;

        // 2. 사이트별 카드 초기화 (모두 loading 상태)
        this.siteResults = siteNames.map((name) => ({
          name,
          status: "loading",
          html: "",
          error: "",
        }));

        // 3. 사이트별 병렬 검색
        const promises = siteNames.map((siteName, index) => {
          const searchUrl =
            getApiUrlPath() +
            `/search_sites/${encodeURIComponent(siteName)}/${encodeURIComponent(keyword)}`;
          return axios
            .get(searchUrl)
            .then((res) => {
              if (res.data.status === "success") {
                this.siteResults[index].status = "success";
                this.siteResults[index].html = res.data.search_result || "";
              } else {
                this.siteResults[index].status = "error";
                this.siteResults[index].error =
                  res.data.message || "검색 실패";
              }
            })
            .catch(() => {
              this.siteResults[index].status = "error";
              this.siteResults[index].error = "검색 중 오류 발생";
            });
        });

        await Promise.all(promises);
      } catch (error) {
        // 사이트 목록 조회 실패 시에도 이미 표시된 카드는 유지
        console.error("Search failed:", error);
      } finally {
        this.isSearching = false;
        this.endButton("searchButton");
      }
    },
  },
  mounted: function () {
    // 인증 검증은 router guard에서 처리됨 (server-side validation)
  },
};
</script>
