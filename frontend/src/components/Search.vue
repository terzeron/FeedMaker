<template>
  <b-container fluid>
    <!-- 검색 창 -->
    <b-row>
      <b-col
          cols="12"
          class="m-0 p-1">
        <b-input-group
            class="m-0 p-1"
            style="width: 400px">
          <b-form-input
              v-model="searchKeyword"
              class="m-0"
              placeholder="키워드"
              @keyup.enter="search">
            {{ searchKeyword }}
          </b-form-input>
          <b-input-group-append>
            <my-button
                ref="searchButton"
                label="검색"
                @click="search"
                :initial-icon="['fas', 'search']"
                :show-initial-icon="true"
                variant="dark"/>
          </b-input-group-append>
        </b-input-group>
      </b-col>
    </b-row>

    <!-- 검색 결과 -->
    <b-row>
      <b-col
          id="search_result"
          cols="12"
          class="m-0 p-1"
          v-if="1">
        <b-table-simple
            class="m-0 p-1 text-break"
            small>
          <b-thead head-variant="light" table-variant="light">
            <b-tr>
              <b-th colspan="2">검색 결과</b-th>
            </b-tr>
          </b-thead>
          <b-tbody>
            <b-tr
                v-for="item in searchResultList"
                :key="item.url">
              <b-td>{{ item.title }}</b-td>
              <b-td>
                <a :href="item.url">{{ item.url }}</a>
              </b-td>
            </b-tr>
          </b-tbody>
        </b-table-simple>
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
</style>

<script>
import axios from 'axios';
import _ from 'lodash';

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
      searchResultList: [],
    };
  },
  computed: {},
  watch: {},
  methods: {
    getApiUrlPath: function () {
      let pathPrefix = 'https://api.terzeron.com/fm';
      if (process.env.NODE_ENV === 'development') {
        pathPrefix = 'http://localhost:5000';
      }
      return pathPrefix;
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
                  this.searchResultList = _.map(res.data['search_result_list'], (o) => {
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
