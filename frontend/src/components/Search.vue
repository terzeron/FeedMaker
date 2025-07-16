<template>
  <BContainer fluid>
    <!-- Search Window -->
    <BRow>
      <BCol md="12" lg="ᆺ6">
        <div class="d-flex p-1">
          <BFormInput
            v-model="searchKeyword"
            class="m-0"
            placeholder="키워드"
            @keyup.enter="search"
          >
            {{ searchKeyword }}
          </BFormInput>
          <my-button
            ref="searchButton"
            label="검색"
            @click="search"
            :initial-icon="['fas', 'search']"
            :show-initial-icon="true"
            variant="dark"
            class="ms-2 text-nowrap"
          />
        </div>
      </BCol>
    </BRow>

    <!-- Search Results -->
    <BRow>
      <BCol id="search_result" cols="12" class="m-0 p-1" v-if="showSearchResult">
        <BTableSimple
          v-if="Array.isArray(searchResultlist) && searchResultlist.length > 0"
          class="m-0 p-1 text-break"
          small
        >
          <BThead head-variant="light" table-variant="light">
            <BTr>
              <BTh colspan="2">검색 결과</BTh>
            </BTr>
          </BThead>
          <BTbody>
            <BTr v-for="item in searchResultlist" :key="item.url">
              <BTd>{{ item.title }}</BTd>
              <BTd>
                <a :href="item.url">{{ item.url }}</a>
              </BTd>
            </BTr>
          </BTbody>
        </BTableSimple>
        <div v-else-if="searchError" class="alert alert-danger">
          {{ searchError }}
        </div>
        <div v-else class="alert alert-info">
          검색 결과가 없습니다.
        </div>
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

<script>
import axios from "axios";
import { getApiUrlPath } from "../utils/api";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faSearch } from "@fortawesome/free-solid-svg-icons";
import MyButton from "./MyButton";

library.add(faSearch);

export default {
  name: "FeedManagement",
  components: {
    MyButton,
  },
  props: [],
  data: function () {
    return {
      showSearchResult: false,
      searchKeyword: "",
      searchResultlist: [],
      searchError: "",
    };
  },
  computed: {
    adminEmail: function () {
      return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
    },
    appVersion: function () {
      return process.env.VUE_APP_VERSION || 'dev';
    },
  },
  watch: {},
  methods: {
    startButton: function (ref) {
      this.$refs[ref].doShowInitialIcon = false;
      this.$refs[ref].doShowSpinner = true;
    },
    endButton: function (ref) {
      this.$refs[ref].doShowInitialIcon = true;
      this.$refs[ref].doShowSpinner = false;
    },
    resetButton: function (ref) {
      this.$refs[ref].doShowInitialIcon = true;
      this.$refs[ref].doShowSpinner = false;
    },
    search: function () {
      this.startButton("searchButton");
      this.showSearchResult = true;
      this.searchError = "";

      const url = getApiUrlPath() + `/search_site/${this.searchKeyword}`;
      axios
        .get(url)
        .then((res) => {
          if (res.data.status === "failure") {
            this.searchError = res.data.message || "검색 중 오류가 발생했습니다.";
            this.searchResultlist = [];
          } else {
            const list = res.data.search_result_list;
            if (Array.isArray(list)) {
              this.searchResultlist = list.map((o) => {
                if (Array.isArray(o) && o.length >= 2) {
                  return { title: o[0], url: o[1] };
                }
                if (typeof o === "object" && o !== null) {
                  return {
                    title: o.title || o[0] || "",
                    url: o.url || o[1] || "",
                  };
                }
                return { title: String(o), url: "" };
              });
            } else {
              this.searchResultlist = [];
            }
          }
          this.endButton("searchButton");
        })
        .catch((error) => {
          this.searchError = "검색 중 오류가 발생했습니다.";
          this.searchResultlist = [];
          this.resetButton("searchButton");
        });
    },
  },
  mounted: function () {
    // Check session expiry before authorization check
    const sessionExpiry = localStorage.getItem("session_expiry");
    if (sessionExpiry && new Date().getTime() > parseInt(sessionExpiry)) {
      console.log("Session expired, redirecting to login");
      this.$session.clear();
      this.$router.push("/login");
      return;
    }

    if (!this.$session.get("is_authorized")) {
      this.$router.push("/login");
    }
  },
};
</script>