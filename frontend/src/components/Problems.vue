<template>
  <BContainer fluid>
    <BRow>
      <BCol cols="12" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          피드 상태
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="hasStatusInfo" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break">
            <thead>
              <tr>
                <th v-for="field in statusInfoFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedStatusInfolist" :key="index">
                <td v-for="field in statusInfoFields" :key="field.key">
                  <span v-if="field.key === 'feed_title'" v-html="item[field.key]"></span>
                  <span v-else-if="field.key === 'action'">
                    <font-awesome-icon
                      :icon="['far', 'trash-alt']"
                      @click="statusInfoDeleteClicked({item: item})"
                      v-if="showStatusInfoDeleteButton({item: item})"
                    />
                  </span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="8" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          진행중 피드 현황
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="hasProgressInfo" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0">
            <thead>
              <tr>
                <th v-for="field in progressInfoFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedProgressInfolist" :key="index">
                <td v-for="field in progressInfoFields" :key="field.key">
                  <span v-if="field.key === 'feed_title'" v-html="item[field.key]"></span>
                  <span v-else-if="field.key === 'progress_ratio'">{{ item[field.key] }}%</span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          피드 URL 개수
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="hasListUrlInfo" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0">
            <thead>
              <tr>
                <th v-for="field in listUrlInfoFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedListUrlInfolist" :key="index">
                <td v-for="field in listUrlInfoFields" :key="field.key">
                  <span v-if="field.key === 'feed_title'" v-html="item[field.key]"></span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          작은 HTML 파일
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="sortedHtmlFileSizelist && Array.isArray(sortedHtmlFileSizelist) && sortedHtmlFileSizelist.length >= 0" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break">
            <thead>
              <tr>
                <th v-for="field in htmlFileSizeFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedHtmlFileSizelist" :key="index">
                <td v-for="field in htmlFileSizeFields" :key="field.key">
                  <span v-if="field.key === 'action'">
                    <font-awesome-icon
                      :icon="['far', 'trash-alt']"
                      @click="htmlFileSizeDeleteClicked({item: item})"
                    />
                  </span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          이미지 태그 없는 HTML 파일
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="sortedHtmlFileWithoutImageTaglist && Array.isArray(sortedHtmlFileWithoutImageTaglist) && sortedHtmlFileWithoutImageTaglist.length >= 0" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break">
            <thead>
              <tr>
                <th v-for="field in htmlFileWithoutImageTagFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedHtmlFileWithoutImageTaglist" :key="index">
                <td v-for="field in htmlFileWithoutImageTagFields" :key="field.key">
                  <span v-if="field.key === 'action'">
                    <font-awesome-icon
                      :icon="['far', 'trash-alt']"
                      @click="imageWithoutImageTagDeleteClicked({item: item})"
                    />
                  </span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          이미지 태그 많은 HTML 파일
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="sortedHtmlFileWithManyImageTaglist && Array.isArray(sortedHtmlFileWithManyImageTaglist) && sortedHtmlFileWithManyImageTaglist.length >= 0" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break">
            <thead>
              <tr>
                <th v-for="field in htmlFileWithManyImageTagFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedHtmlFileWithManyImageTaglist" :key="index">
                <td v-for="field in htmlFileWithManyImageTagFields" :key="field.key">
                  <span v-if="field.key === 'action'">
                    <font-awesome-icon
                      :icon="['far', 'trash-alt']"
                      @click="imageWithManyImageTagDeleteClicked({item: item})"
                    />
                  </span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          이미지 없는 HTML 파일
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="sortedHtmlFileWithImageNotFoundlist && Array.isArray(sortedHtmlFileWithImageNotFoundlist) && sortedHtmlFileWithImageNotFoundlist.length >= 0" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break">
            <thead>
              <tr>
                <th v-for="field in htmlFileWithImageNotFoundFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedHtmlFileWithImageNotFoundlist" :key="index">
                <td v-for="field in htmlFileWithImageNotFoundFields" :key="field.key">
                  <span v-if="field.key === 'action'">
                    <font-awesome-icon
                      :icon="['far', 'trash-alt']"
                      @click="imageNotFoundDeleteClicked({item: item})"
                    />
                  </span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          엘리먼트 사용 개수
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="sortedElementInfolist && Array.isArray(sortedElementInfolist) && sortedElementInfolist.length >= 0" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0">
            <thead>
              <tr>
                <th v-for="field in elementInfoFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedElementInfolist" :key="index">
                <td v-for="field in elementInfoFields" :key="field.key">
                  {{ item[field.key] }}
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>

      <BCol cols="12" lg="4" class="m-0 p-0">
        <BCardHeader
          header-bg-variant="dark"
          header-text-variant="white"
          header-tag="header"
        >
          공개 피드 파일 크기
        </BCardHeader>
        <BCardBody class="m-0 p-0">
          <table v-if="sortedPublicFeedInfolist && Array.isArray(sortedPublicFeedInfolist) && sortedPublicFeedInfolist.length >= 0" 
                 class="table table-striped table-hover table-sm table-bordered m-0 p-0">
            <thead>
              <tr>
                <th v-for="field in publicFeedInfoFields" :key="field.key" 
                    :class="{ 'sortable': field.sortable }">
                  {{ field.label }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, index) in sortedPublicFeedInfolist" :key="index">
                <td v-for="field in publicFeedInfoFields" :key="field.key">
                  <span v-if="field.key === 'feed_title'" v-html="item[field.key]"></span>
                  <span v-else-if="field.key === 'size'"
                        :class="{
                          'text-danger': item.sizeIsDanger,
                          'text-warning': item.sizeIsWarning,
                        }" v-html="item[field.key]"></span>
                  <span v-else-if="field.key === 'num_items'"
                        :class="{
                          'text-danger': item.numItemsIsDanger,
                          'text-warning': item.numItemsIsWarning,
                        }" v-html="item[field.key]"></span>
                  <span v-else-if="field.key === 'upload_date'"
                        :class="{
                          'text-danger': item.uploadDateIsDanger,
                          'text-warning': item.uploadDateIsWarning,
                        }" v-html="item[field.key]"></span>
                  <span v-else-if="field.key === 'action'">
                    <font-awesome-icon
                      :icon="['far', 'trash-alt']"
                      @click="publicFeedInfoDeleteClicked({item: item})"
                    />
                  </span>
                  <span v-else>{{ item[field.key] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>
    </BRow>

    <BRow>
      <BCol cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup>
import { ref, computed, onMounted, inject } from 'vue';
import axios from 'axios';
import _ from 'lodash';
import { library } from '@fortawesome/fontawesome-svg-core';
import { faTrashAlt } from '@fortawesome/free-regular-svg-icons';
import { FontAwesomeIcon } from '@fortawesome/vue-fontawesome';
import { getApiUrlPath, handleApiError } from '@/utils/api';
import { getShortDate } from '@/utils/date';

// FontAwesome 설정
library.add(faTrashAlt);

// Dependencies injection
const $session = inject('$session');
const $router = inject('$router');
const $bvModal = inject('$bvModal');

// Data (reactive)
const problems = ref({});
const statusInfolist = ref([]);
const progressInfolist = ref([]);
const listUrlInfolist = ref([]);
const elementInfolist = ref([]);
const htmlFileSizelist = ref([]);
const htmlFileWithoutImageTaglist = ref([]);
const htmlFileWithManyImageTaglist = ref([]);
const htmlFileWithImageNotFoundlist = ref([]);
const publicFeedInfolist = ref([]);

// Field definitions
const statusInfoFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'feed_name', label: '이름', sortable: true },
  { key: 'feedmaker', label: '제작자', sortable: true },
  { key: 'public_html', label: '등록됨', sortable: true },
  { key: 'http_request', label: '요청', sortable: true },
  { key: 'update_date', label: '생성일', sortable: true },
  { key: 'upload_date', label: '등록일', sortable: true },
  { key: 'access_date', label: '요청일', sortable: true },
  { key: 'view_date', label: '조회일', sortable: true },
  { key: 'action', label: '작업', sortable: false },
]);

const progressInfoFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'current_index', label: '현재', sortable: true },
  { key: 'total_item_count', label: '개수', sortable: true },
  { key: 'unit_size_per_day', label: '단위', sortable: true },
  { key: 'progress_ratio', label: '진행률', sortable: true },
  { key: 'due_date', label: '마감일', sortable: true },
]);

const listUrlInfoFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'count', label: '개수', sortable: true },
]);

const elementInfoFields = ref([
  { key: 'element_name', label: '엘리먼트', sortable: true },
  { key: 'count', label: '개수', sortable: true },
]);

const htmlFileSizeFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'file_path', label: '파일 경로', sortable: true },
  { key: 'size', label: '크기', sortable: true },
  { key: 'action', label: '작업', sortable: false },
]);

const htmlFileWithoutImageTagFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'file_path', label: '파일 경로', sortable: true },
  { key: 'action', label: '작업', sortable: false },
]);

const htmlFileWithManyImageTagFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'file_path', label: '파일 경로', sortable: true },
  { key: 'num_img_tags', label: '이미지 태그 수', sortable: true },
  { key: 'action', label: '작업', sortable: false },
]);

const htmlFileWithImageNotFoundFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'file_path', label: '파일 경로', sortable: true },
  { key: 'action', label: '작업', sortable: false },
]);

const publicFeedInfoFields = ref([
  { key: 'feed_title', label: '제목', sortable: true },
  { key: 'size', label: '크기', sortable: true },
  { key: 'num_items', label: '아이템 수', sortable: true },
  { key: 'upload_date', label: '업로드일', sortable: true },
  { key: 'action', label: '작업', sortable: false },
]);

// Sort configurations
const progressInfoSortBy = ref('progress_ratio');
const progressInfoSortDesc = ref(true);
const listUrlInfoSortBy = ref('count');
const listUrlInfoSortDesc = ref(true);
const elementInfoSortBy = ref('count');
const elementInfoSortDesc = ref(true);
const htmlFileSizeSortBy = ref('size');
const htmlFileSizeSortDesc = ref(true);
const htmlFileWithoutImageTagSortBy = ref('feed_title');
const htmlFileWithoutImageTagSortDesc = ref(true);
const htmlFileWithManyImageTagSortBy = ref('num_img_tags');
const htmlFileWithManyImageTagSortDesc = ref(true);
const htmlFileWithImageNotFoundSortBy = ref('feed_title');
const htmlFileWithImageNotFoundSortDesc = ref(true);
const publicFeedInfoSortBy = ref('size');
const publicFeedInfoSortDesc = ref(true);

// Computed properties
const adminEmail = computed(() => {
  return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
});

// Sorted data with safety checks
const sortedStatusInfolist = computed(() => {
  return Array.isArray(statusInfolist.value) ? statusInfolist.value : [];
});

const sortedProgressInfolist = computed(() => {
  return Array.isArray(progressInfolist.value) ? progressInfolist.value : [];
});

const sortedListUrlInfolist = computed(() => {
  return Array.isArray(listUrlInfolist.value) ? listUrlInfolist.value : [];
});

const sortedElementInfolist = computed(() => {
  return Array.isArray(elementInfolist.value) ? elementInfolist.value : [];
});

const sortedHtmlFileSizelist = computed(() => {
  return Array.isArray(htmlFileSizelist.value) ? htmlFileSizelist.value : [];
});

const sortedHtmlFileWithoutImageTaglist = computed(() => {
  return Array.isArray(htmlFileWithoutImageTaglist.value) ? htmlFileWithoutImageTaglist.value : [];
});

const sortedHtmlFileWithManyImageTaglist = computed(() => {
  return Array.isArray(htmlFileWithManyImageTaglist.value) ? htmlFileWithManyImageTaglist.value : [];
});

const sortedHtmlFileWithImageNotFoundlist = computed(() => {
  return Array.isArray(htmlFileWithImageNotFoundlist.value) ? htmlFileWithImageNotFoundlist.value : [];
});

const sortedPublicFeedInfolist = computed(() => {
  return Array.isArray(publicFeedInfolist.value) ? publicFeedInfolist.value : [];
});

// Template optimization computed properties
const hasStatusInfo = computed(() => {
  return Array.isArray(sortedStatusInfolist.value) && sortedStatusInfolist.value.length > 0;
});

const hasProgressInfo = computed(() => {
  return Array.isArray(sortedProgressInfolist.value) && sortedProgressInfolist.value.length > 0;
});

const hasListUrlInfo = computed(() => {
  return Array.isArray(sortedListUrlInfolist.value) && sortedListUrlInfolist.value.length > 0;
});

const hasElementInfo = computed(() => {
  return Array.isArray(sortedElementInfolist.value) && sortedElementInfolist.value.length > 0;
});

const hasHtmlFileSizeInfo = computed(() => {
  return Array.isArray(sortedHtmlFileSizelist.value) && sortedHtmlFileSizelist.value.length > 0;
});

const hasHtmlFileWithoutImageInfo = computed(() => {
  return Array.isArray(sortedHtmlFileWithoutImageTaglist.value) && sortedHtmlFileWithoutImageTaglist.value.length > 0;
});

const hasHtmlFileWithManyImageInfo = computed(() => {
  return Array.isArray(sortedHtmlFileWithManyImageTaglist.value) && sortedHtmlFileWithManyImageTaglist.value.length > 0;
});

const hasHtmlFileWithImageNotFoundInfo = computed(() => {
  return Array.isArray(sortedHtmlFileWithImageNotFoundlist.value) && sortedHtmlFileWithImageNotFoundlist.value.length > 0;
});

const hasPublicFeedInfo = computed(() => {
  return Array.isArray(sortedPublicFeedInfolist.value) && sortedPublicFeedInfolist.value.length > 0;
});

// Methods
const showStatusInfoDeleteButton = (data) => {
  return data.item['feed_title'] === '' && data.item['public_html'] === 'O';
};

const removePublicFeed = async (feedName) => {
  try {
    const path = getApiUrlPath() + `/public_feeds/${feedName}`;
    const res = await axios.delete(path);
    
    if (res.data.status === 'failure') {
      $bvModal.msgBoxOk(
        '피드 삭제 중에 오류가 발생하였습니다. ' + res.data.message
      );
    }
  } catch (error) {
    handleApiError(error, 'removePublicFeed');
    $bvModal.msgBoxOk(
      '피드 삭제 요청 중에 오류가 발생하였습니다. ' + error.message
    );
  }
};

const statusInfoDeleteClicked = async (data) => {
  console.log(`statusInfoDeleteClicked(${data})`);
  console.log(data.item);
  
  try {
    const value = await $bvModal.msgBoxConfirm('정말로 실행하시겠습니까?');
    if (value) {
      const feedName = data.item['feed_name'];
      await removePublicFeed(feedName);
      statusInfolist.value = statusInfolist.value.filter(
        (item) => item !== data.item
      );
    }
  } catch (error) {
    handleApiError(error, 'statusInfoDeleteClicked');
  }
};

const publicFeedInfoDeleteClicked = async (data) => {
  console.log(`publicFeedInfoDeleteClicked(${data})`);
  console.log(data.item);
  
  try {
    const value = await $bvModal.msgBoxConfirm('정말로 실행하시겠습니까?');
    if (value) {
      const feedName = data.item['feed_name'];
      await removePublicFeed(feedName);
      publicFeedInfolist.value = publicFeedInfolist.value.filter(
        (item) => item !== data.item
      );
    }
  } catch (error) {
    handleApiError(error, 'publicFeedInfoDeleteClicked');
  }
};

const removeHtmlFile = async (filePath) => {
  try {
    const parts = filePath.split('/');
    const groupName = parts[0];
    const feedName = parts[1];
    const htmlFileName = parts[3];
    const path = getApiUrlPath() + `/groups/${groupName}/feeds/${feedName}/htmls/${htmlFileName}`;
    
    const res = await axios.delete(path);
    
    if (res.data.status === 'failure') {
      $bvModal.msgBoxOk(
        '실행 중에 오류가 발생하였습니다. ' + res.data.message
      );
    }
    return true;
  } catch (error) {
    handleApiError(error, 'removeHtmlFile');
    $bvModal.msgBoxOk(
      '실행 요청 중에 오류가 발생하였습니다. ' + error.message
    );
    return false;
  }
};

const imageWithoutImageTagDeleteClicked = async (data) => {
  console.log(`imageWithoutImageTagDeleteClicked(${data})`);
  console.log(data.item);
  
  try {
    const value = await $bvModal.msgBoxConfirm('정말로 실행하시겠습니까?');
    if (value) {
      await removeHtmlFile(data.item['file_path']);
      htmlFileWithoutImageTaglist.value = htmlFileWithoutImageTaglist.value.filter(
        (item) => item !== data.item
      );
    }
  } catch (error) {
    handleApiError(error, 'imageWithoutImageTagDeleteClicked');
  }
};

const imageWithManyImageTagDeleteClicked = async (data) => {
  console.log(`imageWithManyImageTagDeleteClicked(${data})`);
  console.log(data.item);
  
  try {
    const value = await $bvModal.msgBoxConfirm('정말로 실행하시겠습니까?');
    if (value) {
      await removeHtmlFile(data.item['file_path']);
      htmlFileWithManyImageTaglist.value = htmlFileWithManyImageTaglist.value.filter(
        (item) => item !== data.item
      );
    }
  } catch (error) {
    handleApiError(error, 'imageWithManyImageTagDeleteClicked');
  }
};

const imageNotFoundDeleteClicked = async (data) => {
  console.log(`imageNotFoundDeleteClicked(${data})`);
  console.log(data.item);
  
  try {
    const value = await $bvModal.msgBoxConfirm('정말로 실행하시겠습니까?');
    if (value) {
      await removeHtmlFile(data.item['file_path']);
      htmlFileWithImageNotFoundlist.value = htmlFileWithImageNotFoundlist.value.filter(
        (item) => item !== data.item
      );
    }
  } catch (error) {
    handleApiError(error, 'imageNotFoundDeleteClicked');
  }
};

const htmlFileSizeDeleteClicked = async (data) => {
  console.log(`htmlFileSizeDeleteClicked(${data})`);
  console.log(data.item);
  
  try {
    const value = await $bvModal.msgBoxConfirm('정말로 실행하시겠습니까?');
    if (value) {
      await removeHtmlFile(data.item['file_path']);
      htmlFileSizelist.value = htmlFileSizelist.value.filter(
        (item) => item !== data.item
      );
    }
  } catch (error) {
    handleApiError(error, 'htmlFileSizeDeleteClicked');
  }
};

const getManagementLink = (feedTitle, groupName, feedName) => {
  return feedTitle
    ? `<a href="/management/${groupName}/${feedName}">${feedTitle}</a>`
    : '';
};

const getProblems = async () => {
  // Initialize all table data as empty arrays for safety
  statusInfolist.value = [];
  progressInfolist.value = [];
  listUrlInfolist.value = [];
  elementInfolist.value = [];
  htmlFileSizelist.value = [];
  htmlFileWithoutImageTaglist.value = [];
  htmlFileWithManyImageTaglist.value = [];
  htmlFileWithImageNotFoundlist.value = [];
  publicFeedInfolist.value = [];

  try {
    // Feed status info
    const pathStatusInfo = getApiUrlPath() + '/problems/status_info';

    const [statusRes, progressRes, publicFeedRes, htmlRes, elementRes, listUrlRes] = await Promise.all([
      axios.get(pathStatusInfo),
      axios.get(getApiUrlPath() + '/problems/progress_info'),
      axios.get(getApiUrlPath() + '/problems/public_feed_info'),
      axios.get(getApiUrlPath() + '/problems/html_info'),
      axios.get(getApiUrlPath() + '/problems/element_info'),
      axios.get(getApiUrlPath() + '/problems/list_url_info')
    ]);

    // Process status info
    if (statusRes.data.status !== 'failure') {
      const result = Array.isArray(statusRes.data['result']) ? statusRes.data['result'] : [];
      statusInfolist.value = _.map(result, (o) => {
        o['feed_title'] = getManagementLink(
          o['feed_title'],
          o['group_name'],
          o['feed_name']
        );
        o['http_request'] = o['http_request'] ? 'O' : 'X';
        o['public_html'] = o['public_html'] ? 'O' : 'X';
        o['feedmaker'] = o['feedmaker'] ? 'O' : 'X';
        o['update_date'] = getShortDate(o['update_date']);
        o['upload_date'] = getShortDate(o['upload_date']);
        o['access_date'] = getShortDate(o['access_date']);
        o['view_date'] = getShortDate(o['view_date']);
        o['action'] = 'Delete';
        return o;
      });
    }

    // Process progress info
    if (progressRes.data.status !== 'failure') {
      const result = Array.isArray(progressRes.data['result']) ? progressRes.data['result'] : [];
      progressInfolist.value = _.map(result, (o) => {
        o['feed_title'] = getManagementLink(
          o['feed_title'],
          o['group_name'],
          o['feed_name']
        );
        o['due_date'] = getShortDate(o['due_date']);
        return o;
      });
    }

    // Process public feed info
    if (publicFeedRes.data.status !== 'failure') {
      const result = Array.isArray(publicFeedRes.data['result']) ? publicFeedRes.data['result'] : [];
      
      // transformation & filtering
      const day2MonthAgo = new Date();
      day2MonthAgo.setTime(day2MonthAgo.getTime() - 2 * 30 * 24 * 60 * 60 * 1000); // 2 months ago
      const day2MonthAgoStr = day2MonthAgo.toISOString().substring(0, 12);
      
      publicFeedInfolist.value = _.filter(result, (o) => {
        return (
          o['upload_date'] < day2MonthAgoStr ||
          o['size'] < 4 * 1024 ||
          o['num_items'] < 5 ||
          o['num_items'] > 20
        );
      }).map((o) => {
        o['feed_title'] = getManagementLink(
          o['feed_title'],
          o['group_name'],
          o['feed_name']
        ) || o['feed_name'];
        
        if (o['file_size'] < 1024) {
          o['sizeIsDanger'] = true;
        } else if (o['file_size'] < 4 * 1024) {
          o['sizeIsWarning'] = true;
        }
        
        if (o['num_items'] < 5) {
          o['numItemsIsWarning'] = true;
        } else if (o['num_items'] > 20) {
          o['numItemsIsDanger'] = true;
        }
        
        o['upload_date'] = getShortDate(o['upload_date']);
        o['action'] = 'Delete';
        
        if (o['upload_date'] < day2MonthAgoStr) {
          o['uploadDateIsWarning'] = true;
        }
        
        return o;
      });
    }

    // Process HTML info
    if (htmlRes.data.status !== 'failure') {
      const htmlFileSizeMap = Array.isArray(htmlRes.data['result']['html_file_size_map']) 
        ? htmlRes.data['result']['html_file_size_map'] : [];
      const htmlFileWithManyImageTagMap = Array.isArray(htmlRes.data['result']['html_file_with_many_image_tag_map']) 
        ? htmlRes.data['result']['html_file_with_many_image_tag_map'] : [];
      const htmlFileWithoutImageTagMap = Array.isArray(htmlRes.data['result']['html_file_without_image_tag_map']) 
        ? htmlRes.data['result']['html_file_without_image_tag_map'] : [];
      const htmlFileImageNotFoundMap = Array.isArray(htmlRes.data['result']['html_file_image_not_found_map']) 
        ? htmlRes.data['result']['html_file_image_not_found_map'] : [];
      
      htmlFileSizelist.value = _.map(htmlFileSizeMap, (o) => {
        o['action'] = 'Delete';
        return o;
      });
      
      htmlFileWithManyImageTaglist.value = _.map(htmlFileWithManyImageTagMap, (o) => {
        o['action'] = 'Delete';
        return o;
      });
      
      htmlFileWithoutImageTaglist.value = _.map(htmlFileWithoutImageTagMap, (o) => {
        o['action'] = 'Delete';
        return o;
      });
      
      htmlFileWithImageNotFoundlist.value = _.map(htmlFileImageNotFoundMap, (o) => {
        o['action'] = 'Delete';
        return o;
      });
    }

    // Process element info
    if (elementRes.data.status !== 'failure') {
      const result = Array.isArray(elementRes.data['result']) ? elementRes.data['result'] : [];
      elementInfolist.value = _.map(result, (o) => o);
    }

    // Process list URL info
    if (listUrlRes.data.status !== 'failure') {
      const result = Array.isArray(listUrlRes.data['result']) ? listUrlRes.data['result'] : [];
      listUrlInfolist.value = _.map(result, (o) => {
        o['feed_title'] = getManagementLink(
          o['feed_title'],
          o['group_name'],
          o['feed_name']
        );
        return o;
      });
    }
  } catch (error) {
    handleApiError(error, 'getProblems');
    console.error('Problems data loading failed:', error);
  }
};

// Lifecycle
onMounted(() => {
  // Initialize all table data as empty arrays for safety
  statusInfolist.value = [];
  progressInfolist.value = [];
  listUrlInfolist.value = [];
  elementInfolist.value = [];
  htmlFileSizelist.value = [];
  htmlFileWithoutImageTaglist.value = [];
  htmlFileWithManyImageTaglist.value = [];
  htmlFileWithImageNotFoundlist.value = [];
  publicFeedInfolist.value = [];

  if ($session.get('is_authorized')) {
    getProblems();
  } else {
    $router.push('/login');
  }
});
</script>

<style scoped>
/* 추가 스타일이 필요한 경우 여기에 작성 */
</style>
