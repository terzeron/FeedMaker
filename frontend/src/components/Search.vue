<template>
  <BContainer fluid>
    <!-- Search Window -->
    <BRow>
      <BCol
          cols="12"
          class="m-0 p-1">
        <BInputGroup
            class="m-0 p-1"
            style="width: 400px">
          <BFormInput
              v-model="searchKeyword"
              class="m-0"
              placeholder="키워드"
              @keyup.enter="search">
            {{ searchKeyword }}
          </BFormInput>
          <BInputGroupAppend>
            <my-button
                ref="searchButton"
                label="검색"
                @click="search"
                :initial-icon="['fas', 'search']"
                :show-initial-icon="true"
                variant="dark"/>
          </BInputGroupAppend>
        </BInputGroup>
      </BCol>
    </BRow>

    <!-- Search Results -->
    <BRow>
      <BCol
          id="search_result"
          cols="12"
          class="m-0 p-1"
          v-if="1">
        <BTableSimple
            v-if="Array.isArray(searchResultlist) && searchResultlist.length >= 0"
            class="m-0 p-1 text-break"
            small>
          <BThead head-variant="light" table-variant="light">
            <BTr>
              <BTh colspan="2">검색 결과</BTh>
            </BTr>
          </BThead>
          <BTbody>
            <BTr
                v-for="item in searchResultlist"
                :key="item.url">
              <BTd>{{ item.title }}</BTd>
              <BTd>
                <a :href="item.url">{{ item.url }}</a>
              </BTd>
            </BTr>
          </BTbody>
        </BTableSimple>
      </BCol>
    </BRow>
  </BContainer>
</template>

<style>
</style>

<script>
import axios from 'axios';

import {library} from '@fortawesome/fontawesome-svg-core';
import {faSearch} from '@fortawesome/free-solid-svg-icons';
import MyButton from './MyButton';

library.add(faSearch);

export default {
  name: 'FeedManagement',
  components: {
    MyButton
  },
  props: [],
  data: function () {
    return {
      showSearchResult: false,
      searchKeyword: '',
      searchResultlist: [],
    };
  },
  computed: {},
  watch: {},
  methods: {
    getApiUrlPath: function () {
      return process.env.VUE_APP_API_URL;
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
      console.log(`search()`);
      this.startButton('searchButton');

      const url = this.getApiUrlPath() + `/search_site/${this.searchKeyword}`;
      axios
          .get(url)
          .then((res) => {
                if (res.data.status === 'failure') {
                  this.alert(res.data.message);
                } else {
                  this.searchResultlist = res.data['search_result_list'].map(o => {
                    o['title'] = o[0];
                    o['url'] = o[1];
                    return o;
                  });
                }
                this.endButton('searchButton');
              }
          )
          .catch((error) => {
            console.error(error);
            this.resetButton('searchButton');
          })
    },
  },
  mounted: function () {
    if (!this.$session.get('is_authorized')) {
      this.$router.push('/login');
    }
  }
};
</script>
