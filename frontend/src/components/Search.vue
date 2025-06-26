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
          <BInputGroupAppend>
            <my-button
              ref="searchButton"
              label="검색"
              @click="search"
              :initial-icon="['fas', 'search']"
              :show-initial-icon="true"
              variant="dark"
            />
          </BInputGroupAppend>
        </BInputGroup>
      </BCol>
    </BRow>

    <!-- Search Results -->
    <BRow>
      <BCol id="search_result" cols="12" class="m-0 p-1" v-if="hasSearchResults">
        <BTableSimple class="m-0 p-1 text-break" small>
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
      </BCol>
    </BRow>
  </BContainer>
</template>

<style>
</style>

<script setup>
import { ref, computed, onMounted, getCurrentInstance } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

import { library } from '@fortawesome/fontawesome-svg-core';
import { faSearch } from '@fortawesome/free-solid-svg-icons';
import MyButton from './MyButton.vue';

import { getApiUrlPath, handleApiError } from '@/utils/api';
import { useButtonState } from '@/composables/useButtonState';

library.add(faSearch);

defineOptions({
  name: 'Search'
});

const router = useRouter();
const instance = getCurrentInstance();

// Reactive state
const searchKeyword = ref('');
const searchResultlist = ref([]);
const showSearchResult = ref(false);

// Button state management
const { startButton, endButton, resetButton } = useButtonState();

// Computed properties
const hasSearchResults = computed(() => {
  return Array.isArray(searchResultlist.value) && searchResultlist.value.length > 0;
});

// Methods
const search = async () => {
  console.log('search()');
  startButton('searchButton', instance.refs);

  try {
    const url = getApiUrlPath() + `/search_site/${searchKeyword.value}`;
    const res = await axios.get(url);
    
    if (res.data.status === 'failure') {
      alert(res.data.message);
    } else {
      searchResultlist.value = res.data['search_result_list'].map(item => ({
        title: item[0],
        url: item[1]
      }));
      showSearchResult.value = true;
    }
    endButton('searchButton', instance.refs);
  } catch (error) {
    handleApiError(error, 'searching sites');
    resetButton('searchButton', instance.refs);
  }
};

// Lifecycle
onMounted(() => {
  const session = instance.appContext.config.globalProperties.$session;
  if (!session.get('is_authorized')) {
    router.push('/login');
  }
});
</script>