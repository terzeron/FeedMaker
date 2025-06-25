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
          <table v-if="sortedStatusInfolist && Array.isArray(sortedStatusInfolist) && sortedStatusInfolist.length >= 0" 
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
          <table v-if="sortedProgressInfolist && Array.isArray(sortedProgressInfolist) && sortedProgressInfolist.length >= 0" 
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
          <table v-if="sortedListUrlInfolist && Array.isArray(sortedListUrlInfolist) && sortedListUrlInfolist.length >= 0" 
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

<style></style>

<script>
import axios from "axios";
import _ from "lodash";
import moment from "moment";

import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrashAlt } from "@fortawesome/free-regular-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

library.add(faTrashAlt);

export default {
  name: "ProblemList",
  components: {
    FontAwesomeIcon,
  },
  computed: {
    adminEmail: function () {
      return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
    },
    // Computed properties for sorted data with stronger safety checks
    sortedStatusInfolist: function() {
      return Array.isArray(this.statusInfolist) ? this.statusInfolist : [];
    },
    sortedProgressInfolist: function() {
      return Array.isArray(this.progressInfolist) ? this.progressInfolist : [];
    },
    sortedListUrlInfolist: function() {
      return Array.isArray(this.listUrlInfolist) ? this.listUrlInfolist : [];
    },
    sortedElementInfolist: function() {
      return Array.isArray(this.elementInfolist) ? this.elementInfolist : [];
    },
    sortedHtmlFileSizelist: function() {
      return Array.isArray(this.htmlFileSizelist) ? this.htmlFileSizelist : [];
    },
    sortedHtmlFileWithoutImageTaglist: function() {
      return Array.isArray(this.htmlFileWithoutImageTaglist) ? this.htmlFileWithoutImageTaglist : [];
    },
    sortedHtmlFileWithManyImageTaglist: function() {
      return Array.isArray(this.htmlFileWithManyImageTaglist) ? this.htmlFileWithManyImageTaglist : [];
    },
    sortedHtmlFileWithImageNotFoundlist: function() {
      return Array.isArray(this.htmlFileWithImageNotFoundlist) ? this.htmlFileWithImageNotFoundlist : [];
    },
    sortedPublicFeedInfolist: function() {
      return Array.isArray(this.publicFeedInfolist) ? this.publicFeedInfolist : [];
    }
  },
  data: function () {
    return {
      problems: {},
      statusInfoFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "feed_name", label: "이름", sortable: true },
        { key: "feedmaker", label: "제작자", sortable: true },
        { key: "public_html", label: "등록됨", sortable: true },
        { key: "http_request", label: "요청", sortable: true },
        { key: "update_date", label: "생성일", sortable: true },
        { key: "upload_date", label: "등록일", sortable: true },
        { key: "access_date", label: "요청일", sortable: true },
        { key: "view_date", label: "조회일", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      statusInfolist: [],
      progressInfoFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "current_index", label: "현재", sortable: true },
        { key: "total_item_count", label: "개수", sortable: true },
        { key: "unit_size_per_day", label: "단위", sortable: true },
        { key: "progress_ratio", label: "진행률", sortable: true },
        { key: "due_date", label: "마감일", sortable: true },
      ],
      progressInfoSortBy: "progress_ratio",
      progressInfoSortDesc: true,
      progressInfolist: [],
      listUrlInfoFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "count", label: "개수", sortable: true },
      ],
      listUrlInfoSortBy: "count",
      listUrlInfoSortDesc: true,
      listUrlInfolist: [],
      elementInfoFields: [
        { key: "element_name", label: "엘리먼트", sortable: true },
        { key: "count", label: "개수", sortable: true },
      ],
      elementInfoSortBy: "count",
      elementInfoSortDesc: true,
      elementInfolist: [],
      htmlFileSizeFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_path", label: "파일 경로", sortable: true },
        { key: "size", label: "크기", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileSizeSortBy: "size",
      htmlFileSizeSortDesc: true,
      htmlFileSizelist: [],
      htmlFileWithoutImageTagFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_path", label: "파일 경로", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileWithoutImageTagSortBy: "feed_title",
      htmlFileWithoutImageTagSortDesc: true,
      htmlFileWithoutImageTaglist: [],
      htmlFileWithManyImageTagFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_path", label: "파일 경로", sortable: true },
        { key: "num_img_tags", label: "이미지 태그 수", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileWithManyImageTagSortBy: "num_img_tags",
      htmlFileWithManyImageTagSortDesc: true,
      htmlFileWithManyImageTaglist: [],
      htmlFileWithImageNotFoundFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_path", label: "파일 경로", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileWithImageNotFoundSortBy: "feed_title",
      htmlFileWithImageNotFoundSortDesc: true,
      htmlFileWithImageNotFoundlist: [],
      publicFeedInfoFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "size", label: "크기", sortable: true },
        { key: "num_items", label: "아이템 수", sortable: true },
        { key: "upload_date", label: "업로드일", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      publicFeedInfoSortBy: "size",
      publicFeedInfoSortDesc: true,
      publicFeedInfolist: [],
    };
  },
  methods: {
    showStatusInfoDeleteButton: function (data) {
      return data.item["feed_title"] === "" && data.item["public_html"] === "O";
    },
    getApiUrlPath: function () {
      return process.env.VUE_APP_API_URL;
    },
    removePublicFeed(feedName) {
      const path = this.getApiUrlPath() + `/public_feeds/${feedName}`;
      axios
        .delete(path)
        .then((res) => {
          if (res.data.status === "failure") {
            this.$bvModal.msgBoxOk(
              "피드 삭제 중에 오류가 발생하였습니다. " + res.data.message
            );
          }
        })
        .catch((error) => {
          this.$bvModal.msgBoxOk(
            "피드 삭제 요청 중에 오류가 발생하였습니다. " + error
          );
        });
    },
    statusInfoDeleteClicked(data) {
      console.log(`statusInfoDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
        .msgBoxConfirm("정말로 실행하시겠습니까?")
        .then((value) => {
          if (value) {
            const feedName = data.item["feed_name"];

            this.removePublicFeed(feedName);
            this.statusInfolist = this.statusInfolist.filter(
              (item) => item !== data.item
            );
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    publicFeedInfoDeleteClicked(data) {
      console.log(`publicFeedInfoDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
        .msgBoxConfirm("정말로 실행하시겠습니까?")
        .then((value) => {
          if (value) {
            const feedName = data.item["feed_name"];
            this.removePublicFeed(feedName);
            this.publicFeedInfolist = this.publicFeedInfolist.filter(
              (item) => item !== data.item
            );
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    removeHtmlFile(filePath) {
      const parts = filePath.split("/");
      const groupName = parts[0];
      const feedName = parts[1];
      const htmlFileName = parts[3];
      const path =
        this.getApiUrlPath() +
        `/groups/${groupName}/feeds/${feedName}/htmls/${htmlFileName}`;
      axios
        .delete(path)
        .then((res) => {
          if (res.data.status === "failure") {
            this.$bvModal.msgBoxOk(
              "실행 중에 오류가 발생하였습니다. " + res.data.message
            );
          } else {
            //
          }
        })
        .catch((error) => {
          this.$bvModal.msgBoxOk(
            "실행 요청 중에 오류가 발생하였습니다. " + error
          );
        });
      return true;
    },
    imageWithoutImageTagDeleteClicked(data) {
      console.log(`imageWithoutImageTagDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
        .msgBoxConfirm("정말로 실행하시겠습니까?")
        .then((value) => {
          if (value) {
            this.removeHtmlFile(data.item["file_path"]);
            this.htmlFileWithoutImageTaglist =
              this.htmlFileWithoutImageTaglist.filter(
                (item) => item !== data.item
              );
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    imageWithManyImageTagDeleteClicked(data) {
      console.log(`imageWithManyImageTagDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
        .msgBoxConfirm("정말로 실행하시겠습니까?")
        .then((value) => {
          if (value) {
            this.removeHtmlFile(data.item["file_path"]);
            this.htmlFileWithManyImageTaglist =
              this.htmlFileWithManyImageTaglist.filter(
                (item) => item !== data.item
              );
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    imageNotFoundDeleteClicked(data) {
      console.log(`imageNotFoundDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
        .msgBoxConfirm("정말로 실행하시겠습니까?")
        .then((value) => {
          if (value) {
            this.removeHtmlFile(data.item["file_path"]);
            this.htmlFileWithImageNotFoundlist =
              this.htmlFileWithImageNotFoundlist.filter(
                (item) => item !== data.item
              );
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    htmlFileSizeDeleteClicked(data) {
      console.log(`htmlFileSizeDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
        .msgBoxConfirm("정말로 실행하시겠습니까?")
        .then((value) => {
          if (value) {
            this.removeHtmlFile(data.item["file_path"]);
            this.htmlFileSizelist = this.htmlFileSizelist.filter(
              (item) => item !== data.item
            );
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    getManagementLink(feedTitle, groupName, feedName) {
      return feedTitle
        ? `<a href="/management/${groupName}/${feedName}">${feedTitle}</a>`
        : "";
    },
    getShortDate(date) {
      let d = moment(date);
      if (!d.isValid()) {
        return "";
      }
      return d.format("YY-MM-DD");
    },
    getProblems() {
      // Initialize all table data as empty arrays for safety
      this.statusInfolist = [];
      this.progressInfolist = [];
      this.listUrlInfolist = [];
      this.elementInfolist = [];
      this.htmlFileSizelist = [];
      this.htmlFileWithoutImageTaglist = [];
      this.htmlFileWithManyImageTaglist = [];
      this.htmlFileWithImageNotFoundlist = [];
      this.publicFeedInfolist = [];
      
      // Feed status info
      const pathStatusInfo = this.getApiUrlPath() + "/problems/status_info";
      axios
        .get(pathStatusInfo)
        .then((resStatusInfo) => {
          if (resStatusInfo.data.status === "failure") {
            console.log(resStatusInfo.data.message);
            this.statusInfolist = [];
          } else {
            // Ensure result is an array
            const result = Array.isArray(resStatusInfo.data["result"]) 
              ? resStatusInfo.data["result"] 
              : [];
            
            // transformation
            this.statusInfolist = _.map(result, (o) => {
              o["feed_title"] = this.getManagementLink(
                o["feed_title"],
                o["group_name"],
                o["feed_name"]
              );
              o["http_request"] = o["http_request"] ? "O" : "X";
              o["public_html"] = o["public_html"] ? "O" : "X";
              o["feedmaker"] = o["feedmaker"] ? "O" : "X";
              o["update_date"] = this.getShortDate(o["update_date"]);
              o["upload_date"] = this.getShortDate(o["upload_date"]);
              o["access_date"] = this.getShortDate(o["access_date"]);
              o["view_date"] = this.getShortDate(o["view_date"]);
              o["action"] = "Delete";
              return o;
            });
            console.log(this.statusInfolist);
          }
        })
        .catch((error) => {
          console.error(error);
          this.statusInfolist = [];
        });

      // Progressive feed progress info
      const pathProgressInfo = this.getApiUrlPath() + "/problems/progress_info";
      axios
        .get(pathProgressInfo)
        .then((resProgressInfo) => {
          if (resProgressInfo.data.status === "failure") {
            console.log(resProgressInfo.data.message);
            this.progressInfolist = [];
          } else {
            // Ensure result is an array
            const result = Array.isArray(resProgressInfo.data["result"]) 
              ? resProgressInfo.data["result"] 
              : [];
            
            this.progressInfolist = _.map(result, (o) => {
              o["feed_title"] = this.getManagementLink(
                o["feed_title"],
                o["group_name"],
                o["feed_name"]
              );
              o["due_date"] = this.getShortDate(o["due_date"]);
              return o;
            });
          }
        })
        .catch((error) => {
          console.error(error);
          this.progressInfolist = [];
        });

      // Public feed info
      const pathPublicFeedInfo =
        this.getApiUrlPath() + "/problems/public_feed_info";
      axios
        .get(pathPublicFeedInfo)
        .then((resPublicFeedInfo) => {
          if (resPublicFeedInfo.data.status === "failure") {
            console.log(resPublicFeedInfo.data.message);
            this.publicFeedInfolist = [];
          } else {
            // Ensure result is an array
            const result = Array.isArray(resPublicFeedInfo.data["result"]) 
              ? resPublicFeedInfo.data["result"] 
              : [];
            
            // transformation & filtering
            let day2MonthAgo = new Date();
            day2MonthAgo.setTime(
              day2MonthAgo.getTime() - 2 * 30 * 24 * 60 * 60 * 1000
            ); // 2 months ago
            day2MonthAgo = day2MonthAgo.toISOString().substring(0, 12);
            this.publicFeedInfolist = _.filter(result, (o) => {
              return (
                o["upload_date"] < day2MonthAgo ||
                o["size"] < 4 * 1024 ||
                o["num_items"] < 5 ||
                o["num_items"] > 20
              );
            }).map((o) => {
              o["feed_title"] =
                this.getManagementLink(
                  o["feed_title"],
                  o["group_name"],
                  o["feed_name"]
                ) || o["feed_name"];
              if (o["file_size"] < 1024) {
                o["sizeIsDanger"] = true;
              } else if (o["file_size"] < 4 * 1024) {
                o["sizeIsWarning"] = true;
              }
              if (o["num_items"] < 5) {
                o["numItemsIsWarning"] = true;
              } else if (o["num_items"] > 20) {
                o["numItemsIsDanger"] = true;
              }
              o["upload_date"] = this.getShortDate(o["upload_date"]);
              o["action"] = "Delete";
              if (o["upload_date"] < day2MonthAgo) {
                o["uploadDateIsWarning"] = true;
              }
              return o;
            });
          }
        })
        .catch((error) => {
          console.error(error);
          this.publicFeedInfolist = [];
        });

      // HTML info
      const pathHtmlInfo = this.getApiUrlPath() + "/problems/html_info";
      axios
        .get(pathHtmlInfo)
        .then((resHtmlInfo) => {
          if (resHtmlInfo.data.status === "failure") {
            console.log(resHtmlInfo.data.message);
            this.htmlFileSizelist = [];
            this.htmlFileWithManyImageTaglist = [];
            this.htmlFileWithoutImageTaglist = [];
            this.htmlFileWithImageNotFoundlist = [];
          } else {
            // Ensure all result properties are arrays
            const htmlFileSizeMap = Array.isArray(resHtmlInfo.data["result"]["html_file_size_map"]) 
              ? resHtmlInfo.data["result"]["html_file_size_map"] 
              : [];
            const htmlFileWithManyImageTagMap = Array.isArray(resHtmlInfo.data["result"]["html_file_with_many_image_tag_map"]) 
              ? resHtmlInfo.data["result"]["html_file_with_many_image_tag_map"] 
              : [];
            const htmlFileWithoutImageTagMap = Array.isArray(resHtmlInfo.data["result"]["html_file_without_image_tag_map"]) 
              ? resHtmlInfo.data["result"]["html_file_without_image_tag_map"] 
              : [];
            const htmlFileImageNotFoundMap = Array.isArray(resHtmlInfo.data["result"]["html_file_image_not_found_map"]) 
              ? resHtmlInfo.data["result"]["html_file_image_not_found_map"] 
              : [];
            
            this.htmlFileSizelist = _.map(htmlFileSizeMap, (o) => {
              o["action"] = "Delete";
              return o;
            });
            this.htmlFileWithManyImageTaglist = _.map(htmlFileWithManyImageTagMap, (o) => {
              o["action"] = "Delete";
              return o;
            });
            this.htmlFileWithoutImageTaglist = _.map(htmlFileWithoutImageTagMap, (o) => {
              o["action"] = "Delete";
              return o;
            });
            this.htmlFileWithImageNotFoundlist = _.map(htmlFileImageNotFoundMap, (o) => {
              o["action"] = "Delete";
              return o;
            });
          }
        })
        .catch((error) => {
          console.error(error);
          this.htmlFileSizelist = [];
          this.htmlFileWithManyImageTaglist = [];
          this.htmlFileWithoutImageTaglist = [];
          this.htmlFileWithImageNotFoundlist = [];
        });

      // Element info
      const pathElementInfo = this.getApiUrlPath() + "/problems/element_info";
      axios
        .get(pathElementInfo)
        .then((resElementInfo) => {
          if (resElementInfo.data.status === "failure") {
            console.log(resElementInfo.data.message);
            this.elementInfolist = [];
          } else {
            // Ensure result is an array
            const result = Array.isArray(resElementInfo.data["result"]) 
              ? resElementInfo.data["result"] 
              : [];
            
            this.elementInfolist = _.map(result, (o) => {
              return o;
            });
          }
        })
        .catch((error) => {
          console.error(error);
          this.elementInfolist = [];
        });

      // List URL count info
      const listUrlInfo = this.getApiUrlPath() + "/problems/list_url_info";
      axios
        .get(listUrlInfo)
        .then((reslistUrlInfo) => {
          if (reslistUrlInfo.data.status === "failure") {
            console.log(reslistUrlInfo.data.message);
            this.listUrlInfolist = [];
          } else {
            // Ensure result is an array
            const result = Array.isArray(reslistUrlInfo.data["result"]) 
              ? reslistUrlInfo.data["result"] 
              : [];
            
            this.listUrlInfolist = _.map(result, (o) => {
              o["feed_title"] = this.getManagementLink(
                o["feed_title"],
                o["group_name"],
                o["feed_name"]
              );
              return o;
            });
          }
        })
        .catch((error) => {
          console.error(error);
          this.listUrlInfolist = [];
        });
    },
  },
  mounted: function () {
    // Initialize all table data as empty arrays for safety
    this.statusInfolist = [];
    this.progressInfolist = [];
    this.listUrlInfolist = [];
    this.elementInfolist = [];
    this.htmlFileSizelist = [];
    this.htmlFileWithoutImageTaglist = [];
    this.htmlFileWithManyImageTaglist = [];
    this.htmlFileWithImageNotFoundlist = [];
    this.publicFeedInfolist = [];
    
    if (this.$session.get("is_authorized")) {
      this.getProblems();
    } else {
      this.$router.push("/login");
    }
  },
};
</script>
