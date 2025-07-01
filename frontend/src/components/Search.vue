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
  </BContainer>
</template>

<style></style>

<script>
import axios from "axios";

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
  computed: {},
  watch: {},
  methods: {
    getApiUrlPath: function () {
      return process.env.VUE_APP_API_URL || "http://localhost:8010";
    },
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

      const url = this.getApiUrlPath() + `/search_site/${this.searchKeyword}`;
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
    if (!this.$session.get("is_authorized")) {
      this.$router.push("/login");
    }
  },
};
</script>
