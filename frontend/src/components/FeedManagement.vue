<template>
  <BContainer fluid>
    <!-- Group and Feed List Control Buttons -->
    <BRow>
      <BCol cols="12" class="m-0 p-1">
        <span class="button_list">
          <my-button
            ref="grouplistButton"
            label="그룹 목록"
            variant="success"
            @click="grouplistButtonClicked"
          />
          <my-button
            ref="feedlistButton"
            :label="selectedGroupName + ' 그룹 피드 목록'"
            @click="feedlistButtonClicked"
            v-if="showFeedlistButton"
          />
        </span>

        <BInputGroup class="float-right m-0 p-1" style="width: 300px">
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
      <BCol
        id="search_result"
        cols="12"
        class="m-0 p-1 button_list"
        v-if="showSearchResult"
      >
        <my-button
          ref="searchResultFeedButton"
          :label="feed['group_name'] + '/' + feed['feed_title']"
          variant="success"
          @click="
            searchResultFeedNameButtonClicked(
              feed['group_name'],
              feed['feed_name'],
              index
            )
          "
          :class="{
            active: activeFeedIndex === index,
            'bg-secondary': !determineStatus(feed),
          }"
          v-for="(feed, index) in feeds"
          :key="feed['group_name'] + '/' + feed['feed_name']"
        />
      </BCol>
    </BRow>

    <!-- Group List -->
    <BRow>
      <BCol
        id="group_list"
        cols="12"
        class="m-0 p-1 button_list"
        v-if="showGrouplist"
      >
        <my-button
          ref="groupNameButton"
          :label="group.name + ' (' + group['num_feeds'] + ')'"
          variant="success"
          @click="groupNameButtonClicked(group.name, index)"
          :class="{
            active: activeGroupIndex === index,
            'bg-secondary': !determineStatus(group),
          }"
          v-for="(group, index) in groups"
          :key="group.name"
        />
        <div class="p-2" v-if="!groups || !groups.length">그룹 목록 없음</div>
      </BCol>
    </BRow>

    <!-- Feed List -->
    <BRow>
      <BCol
        id="feed_list"
        cols="12"
        class="m-0 p-1 button_list"
        v-if="showFeedlist"
      >
        <my-button
          ref="feedNameButton"
          :label="feed.title"
          @click="feedNameButtonClicked(selectedGroupName, feed.name, index)"
          :class="{
            active: activeFeedIndex === index,
            'bg-secondary': !determineStatus(feed),
          }"
          v-for="(feed, index) in feeds"
          :key="feed.name"
        />
        <div class="p-2" v-if="!feeds || !feeds.length">피드 목록 없음</div>
      </BCol>
    </BRow>

    <!-- Configuration Editor and Action, Metadata Area -->
    <BRow>
      <!-- Configuration Editor Area -->
      <BCol id="configuration" cols="12" lg="8" class="m-0 p-1">
        <div ref="jsonEditorContainer" v-if="showEditor"></div>
        <div class="p-2" v-if="!showEditor">설정 파일 없음</div>
      </BCol>

      <!-- Info, Metadata, Action Area -->
      <BCol cols="12" lg="4" class="m-0 p-0">
        <!-- Info Area -->
        <BRow id="feed_info" class="m-0 p-0" v-if="showNewFeedNameInput">
          <BCol
            cols="12"
            class="m-0 p-1"
            :class="{ 'bg-secondary': !feedStatus }"
          >
            <div>{{ title }}</div>
            <div>{{ selectedGroupName + "/" + selectedFeedName }}</div>
          </BCol>
        </BRow>

        <!-- Metadata Area -->
        <BRow id="metadata" class="m-0 p-0" v-if="showFeedInfo">
          <BCol cols="12" class="m-0 p-0">
            <div class="table-responsive">
              <BTableSimple
                class="m-0 text-break table-hover"
                small
                striped
                style="margin: 0 !important; padding: 0 !important; width: 100% !important;"
              >
                <BThead head-variant="secondary" table-variant="light">
                  <BTr>
                    <BTh colspan="4" class="text-center">메타데이터</BTh>
                  </BTr>
                </BThead>
                <BTbody>
                  <BTr v-if="numCollectionUrls && totalItemCount">
                    <BTd class="fw-bold">수집</BTd>
                    <BTd>{{ numCollectionUrls }} 페이지</BTd>
                    <BTd>{{ totalItemCount }} 피드</BTd>
                    <BTd>{{ collectDate }}</BTd>
                  </BTr>
                  <BTr v-if="numItemsInResult && sizeOfResultFileWithUnit">
                    <BTd class="fw-bold">피드</BTd>
                    <BTd>{{ numItemsInResult }} 피드</BTd>
                    <BTd>{{ sizeOfResultFileWithUnit }}</BTd>
                    <BTd>{{ lastUploadDate }}</BTd>
                  </BTr>
                  <BTr
                    v-if="
                      totalItemCount >= 0 &&
                      currentIndex >= 0 &&
                      unitSizePerDay >= 0
                    "
                  >
                    <BTd class="fw-bold">진행 상태</BTd>
                    <BTd colspan="2">
                      <BProgress
                        :max="totalItemCount"
                        show-progress
                        height="1.5rem"
                      >
                        <BProgressBar :value="currentIndex" variant="warning">
                          <div
                            style="
                              position: absolute;
                              width: 100%;
                              color: black;
                              text-align: left;
                              overflow: visible;
                            "
                          >
                            {{ currentIndex }} / {{ totalItemCount }} =
                            {{ progressRatio }} %, {{ unitSizePerDay }}/일
                          </div>
                        </BProgressBar>
                      </BProgress>
                    </BTd>
                    <BTd>{{ feedCompletionDueDate }}</BTd>
                  </BTr>
                </BTbody>
              </BTableSimple>
            </div>
          </BCol>
        </BRow>

        <!-- Action Area -->
        <BRow id="actions" class="m-0 p-0">
          <BCol cols="12" class="m-0 p-1">
            <BInputGroup prepend="피드" class="m-0" v-if="showNewFeedNameInput">
              <BFormInput class="m-0" v-model="newFeedName">
                {{ newFeedName }}
              </BFormInput>
              <BInputGroupText class="p-0">
                <my-button
                  ref="saveButton"
                  label="저장"
                  @click="save"
                  :initial-icon="['far', 'save']"
                  :show-initial-icon="true"
                  class="w-100 h-100"
                />
              </BInputGroupText>
            </BInputGroup>
          </BCol>

          <BCol
            cols="12"
            class="m-0 p-1 button_list"
            v-if="
              showSiteConfig || showToggleGroupButton || showRemoveGroupButton
            "
          >
            <my-button
              ref="saveSiteConfigButton"
              label="그룹 설정 저장"
              @click="saveSiteConfig"
              :initial-icon="['far', 'save']"
              :show-initial-icon="true"
              v-if="showSiteConfig"
            />
            <my-button
              ref="toggleGroupButton"
              :label="groupStatusLabel"
              variant="success"
              @click="toggleStatus('group')"
              :initial-icon="['fas', groupStatusIcon]"
              :show-initial-icon="true"
              v-if="showToggleGroupButton"
            />
            <my-button
              ref="removeGroupButton"
              label="그룹 삭제"
              variant="success"
              @click="removeGroup"
              :initial-icon="['far', 'trash-alt']"
              :show-initial-icon="true"
              v-if="showRemoveGroupButton"
            />
          </BCol>

          <BCol cols="12" class="m-0 p-1 button_list">
            <my-button
              ref="runButton"
              label="실행"
              @click="run"
              :initial-icon="['fas', 'play']"
              :show-initial-icon="true"
              v-if="showRunButton"
            />
            <my-button
              ref="removelistButton"
              label="목록 삭제"
              @click="removelist"
              :initial-icon="['fas', 'eraser']"
              :show-initial-icon="true"
              v-if="showRemovelistButton"
            />
            <my-button
              ref="removeHtmlButton"
              label="HTML 삭제"
              @click="removeHtml"
              :initial-icon="['fas', 'eraser']"
              :show-initial-icon="true"
              v-if="showRemoveHtmlButton"
            />
            <my-button
              ref="toggleFeedButton"
              :label="feedStatusLabel"
              @click="toggleStatus('feed')"
              :initial-icon="['fas', feedStatusIcon]"
              :show-initial-icon="true"
              v-if="showToggleFeedButton"
            />
            <my-button
              ref="removeFeedButton"
              label="피드 삭제"
              @click="removeFeed"
              :initial-icon="['far', 'trash-alt']"
              :show-initial-icon="true"
              variant="danger"
              v-if="showRemoveFeedButton"
            />
          </BCol>

          <BCol cols="12" class="m-0 p-1 button_list">
            <my-button
              ref="viewRssButton"
              label="RSS"
              @click="viewRss"
              :initial-icon="['fas', 'rss']"
              :show-initial-icon="true"
              v-if="showViewRssButton"
            />
            <my-button
              ref="registerButton"
              label="Inoreader"
              @click="registerToInoreader"
              :initial-icon="['fas', 'rss']"
              :show-initial-icon="true"
              v-if="showRegisterToInoreaderButton"
            />
            <my-button
              ref="registerButton"
              label="Feedly"
              @click="registerToFeedly"
              :initial-icon="['fas', 'rss']"
              :show-initial-icon="true"
              v-if="showRegisterToFeedlyButton"
            />
            <my-button
              ref="viewItemsOfRssButton"
              label="RSS 항목 보기"
              @click="getItemsOfRss"
              :initial-icon="['fas', 'rss']"
              :show-initial-icon="true"
              v-if="showViewRssButton"
              />
          </BCol>
        </BRow>

        <BRow id="titles_of_rss" class="m-0 p-0" v-if="showViewItemsOfRssList">
          <BCol cols="12" class="m-0 p-0">
            <div class="table-responsive">
              <BTableSimple
                class="m-0 text-break table-hover"
                small
                striped
                style="margin: 0 !important; padding: 0 !important; width: 100% !important;"
              >
                <BThead head-variant="secondary" table-variant="light">
                  <BTr>
                    <BTh colspan="4" class="text-center">RSS 아이템 제목</BTh>
                  </BTr>
                </BThead>
                <BTbody>
                  <!-- list of titles of rss -->
                  <BTr v-for="(title, index) in itemsOfRss" :key="index">
                    <BTd>{{ title }}</BTd>
                  </BTr>
                </BTbody>
              </BTableSimple>
            </div>
          </BCol>
        </BRow>

        <!-- Alert component -->
        <BRow v-if="showAlert">
          <BCol>
            <BAlert
              :variant="alertVariant"
              show
              dismissible
              @dismissed="clearAlert"
            >
              {{ alertMessage }}
            </BAlert>
          </BCol>
        </BRow>

      </BCol>
    </BRow>

    <BRow>
      <BCol cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
        <div class="text-muted small mt-1">v{{ appVersion }}</div>
      </BCol>
    </BRow>

    <!-- Confirmation Modal -->
    <BModal
      v-model="showConfirmModal"
      title="확인"
      ok-title="확인"
      cancel-title="취소"
      @ok="handleConfirmOk"
      @cancel="handleConfirmCancel"
    >
      <p>{{ confirmMessage }}</p>
    </BModal>
  </BContainer>
</template>

<style>
#group_list,
#feed_list,
#configuration,
#feed_info,
#metadata,
#actions {
  border: 1px lightgray solid;
  border-collapse: collapse;
  padding: 0 !important;
}

.button_list button {
  margin: 2px 3px 3px 2px !important;
  transition: all 0.2s ease-in-out;
}

/* Active 상태 버튼 스타일 (선택된 항목) */
.button_list button.active {
  background-color: #007bff !important;
  border-color: #0056b3 !important;
  color: white !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 4px rgba(0, 123, 255, 0.3) !important;
  transform: translateY(-1px) !important;
}

.button_list button.active:hover {
  background-color: #0056b3 !important;
  border-color: #004085 !important;
  box-shadow: 0 4px 8px rgba(0, 123, 255, 0.4) !important;
}

/* 비활성 상태 버튼 스타일 (비활성화된 피드/그룹) */
.button_list button.bg-secondary {
  background-color: #6c757d !important;
  border-color: #545b62 !important;
  color: #f8f9fa !important;
  opacity: 0.8 !important;
}

.button_list button.bg-secondary:hover {
  background-color: #545b62 !important;
  border-color: #4e555b !important;
  opacity: 1 !important;
}

/* 활성 상태 버튼 스타일 (활성화된 피드/그룹) */
.button_list button:not(.active):not(.bg-secondary) {
  background-color: #198754 !important;
  border-color: #146c43 !important;
  color: white !important;
  font-weight: 500 !important;
}

.button_list button:not(.active):not(.bg-secondary):hover {
  background-color: #146c43 !important;
  border-color: #0f5132 !important;
}

/* 활성 버튼 호버 효과 */
.button_list button:not(.active):not(.bg-secondary):hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 2px 4px rgba(25, 135, 84, 0.3) !important;
}


div.jsoneditor-field {
  padding: 5px;
}

div.jsoneditor-value {
  padding: 5px;
  border: 1px lightgray dotted;
}
</style>

<script>
import axios from "axios";
import { getApiUrlPath } from "../utils/api";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrashAlt, faSave } from "@fortawesome/free-regular-svg-icons";
import {
  faSearch,
  faRss,
  faPlay,
  faToggleOn,
  faToggleOff,
  faEraser,
  faPen,
  faEye,
} from "@fortawesome/free-solid-svg-icons";
import MyButton from "./MyButton";
import JSONEditor from "jsoneditor";
import "jsoneditor/dist/jsoneditor.css";


library.add(
  faTrashAlt,
  faSave,
  faSearch,
  faRss,
  faPlay,
  faToggleOn,
  faToggleOff,
  faEraser,
  faPen,
  faEye
);

export default {
  name: "FeedManagement",
  components: {
    MyButton,
  },
  props: {
    feed: {
      type: Object,
      default: () => ({})
    },
    group: {
      type: Object,
      default: () => ({})
    }
  },

  data: function () {
    return {
      showGrouplist: true,
      showFeedlist: false,
      showFeedlistButton: false,
      showSearchResult: false,

      showEditor: false,

      showAlert: false,
      alertMessage: "",
      alertVariant: "danger",
      showRunButton: false,
      showViewRssButton: false,
      showViewItemsOfRssList: false,
      showRegisterToInoreaderButton: false,
      showRegisterToFeedlyButton: false,
      showRemovelistButton: false,
      showRemoveFeedButton: false,
      showRemoveGroupButton: false,
      showToggleFeedButton: false,
      showToggleGroupButton: false,
      showRemoveHtmlButton: false,
      showNewFeedNameInput: false,
      showSiteConfig: false,
      showFeedInfo: false,
      itemsOfRss: [],

      activeGroupIndex: undefined,
      activeFeedIndex: undefined,

      groups: [],
      feeds: [],
      jsonData: {},
      selectedGroupName: "",
      selectedFeedName: "",
      newFeedName: "",
      searchKeyword: "",

      numCollectionUrls: 0,
      collectDate: "-",
      urllistCount: 0,
      numItemsInResult: 0,
      sizeOfResultFile: 0,
      lastUploadDate: "-",
      currentIndex: 0,
      totalItemCount: 0,
      unitSizePerDay: 0,
      progressRatio: 0.0,
      feedCompletionDueDate: "-",

      checkRunningInterval: null,
      jsonEditor: null,

      // Modal related data
      showConfirmModal: false,
      confirmMessage: "",
      pendingAction: null,
    };
  },
  computed: {
    feedStatus: function () {
      // 선택된 피드의 active 상태 확인
      const selectedFeed = this.feeds.find(feed => feed.name === this.selectedFeedName);
      return selectedFeed ? this.determineStatus(selectedFeed) : true;
    },
    groupStatus: function () {
      // 선택된 그룹의 active 상태 확인
      const selectedGroup = this.groups.find(group => group.name === this.selectedGroupName);
      return selectedGroup ? this.determineStatus(selectedGroup) : true;
    },
    feedStatusLabel: function () {
      return "피드 " + (this.feedStatus ? "비활성화" : "활성화");
    },
    feedStatusIcon: function () {
      return "toggle-" + (this.feedStatus ? "off" : "on");
    },
    groupStatusLabel: function () {
      return "그룹 " + (this.groupStatus ? "비활성화" : "활성화");
    },
    groupStatusIcon: function () {
      return "toggle-" + (this.feedStatus ? "off" : "on");
    },
    title: function () {
      return this.jsonData.rss["title"];
    },
    rssUrl: function () {
      return `https://terzeron.com/${this.newFeedName}.xml`;
    },
    adminEmail: function () {
      return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
    },
    appVersion: function () {
      return process.env.VUE_APP_VERSION || 'dev';
    },
    sizeOfResultFileWithUnit: function () {
      if (this.sizeOfResultFile > 1024 * 1024 * 1024) {
        return (this.sizeOfResultFile / 1024 / 1024 / 1024).toFixed(2) + " GiB";
      } else if (this.sizeOfResultFile > 1024 * 1024) {
        return (this.sizeOfResultFile / 1024 / 1024).toFixed(2) + " MiB";
      } else if (this.sizeOfResultFile > 1024) {
        return (this.sizeOfResultFile / 1024).toFixed(2) + " KiB";
      } else {
        return this.sizeOfResultFile + " B";
      }
    },
  },
  watch: {
    newFeedName: function (val) {
      this.jsonData.rss.link = "https://terzeron.com/" + val + ".xml";
    },
    jsonData: function () {
      this.determineNewFeedNameFromJsonRssLink();
      this.determineDescriptionFromTitle();
    },
  },
  methods: {
    getShortDateStr: function (dateStr) {
      if (!dateStr) {
        return "";
      }
      return dateStr.split("T")[0];
    },
    determineNewFeedNameFromJsonRssLink: function () {
      if ("rss" in this.jsonData && "link" in this.jsonData["rss"]) {
        const re = /https:\/\/terzeron.com\/_?(.+)\.xml/;
        const matched = this.jsonData.rss.link.match(re);
        if (matched) {
          this.newFeedName = matched[1];
        }
      }
    },
    determineDescriptionFromTitle: function () {
      if (
        "rss" in this.jsonData &&
        "title" in this.jsonData.rss &&
        "description" in this.jsonData.rss
      ) {
        this.jsonData.rss["description"] = this.jsonData.rss["title"];
      }
    },
    setActiveGroup: function (index) {
      this.activeGroupIndex = index;
    },
    setActiveFeed: function (index) {
      this.activeFeedIndex = index;
    },
    alert: function (message, variant = "danger") {
      this.alertMessage = message;
      this.alertVariant = variant;
      this.showAlert = true;
    },
    clearAlert: function () {
      this.showAlert = false;
      this.alertMessage = "";
      this.alertVariant = "danger";
    },
    openConfirmModal: function (message, action) {
      this.confirmMessage = message;
      this.pendingAction = action;
      this.showConfirmModal = true;
    },
    handleConfirmOk: function () {
      if (this.pendingAction) {
        this.pendingAction();
      }
      this.showConfirmModal = false;
      this.pendingAction = null;
    },
    handleConfirmCancel: function () {
      this.showConfirmModal = false;
      this.pendingAction = null;
    },
    determineStatus: function (item) {
      // item이 객체인 경우 (피드나 그룹 객체)
      if (typeof item === 'object' && item !== null) {
        return item.is_active !== false; // is_active가 명시적으로 false가 아니면 true
      }
      // item이 문자열인 경우 (이름만 전달된 경우, 하위 호환성)
      if (typeof item === 'string') {
        return item[0] !== "_";
      }
      return true; // 기본값
    },


    startButton: function (ref) {
      console.log("startButton called for:", ref);
      if (this.$refs[ref]) {
        console.log("Setting doShowInitialIcon to false, doShowSpinner to true");
        this.$refs[ref].doShowInitialIcon = false;
        this.$refs[ref].doShowSpinner = true;
      } else {
        console.error("Button ref not found:", ref);
      }
    },
    endButton: function (ref) {
      console.log("endButton called for:", ref);
      if (this.$refs[ref]) {
        console.log("Setting doShowInitialIcon to true, doShowSpinner to false");
        this.$refs[ref].doShowInitialIcon = true;
        this.$refs[ref].doShowSpinner = false;
      } else {
        console.error("Button ref not found:", ref);
      }
    },
    resetButton: function (ref) {
      console.log("resetButton called for:", ref);
      if (this.$refs[ref]) {
        console.log("Setting doShowInitialIcon to true, doShowSpinner to false");
        this.$refs[ref].doShowInitialIcon = true;
        this.$refs[ref].doShowSpinner = false;
      } else {
        console.error("Button ref not found:", ref);
      }
    },
    showAllRelatedToFeed: function () {
      this.showEditor = true;
      this.showNewFeedNameInput = true;
      this.showRunButton = true;
      this.showViewRssButton = true;
      this.showRegisterToInoreaderButton = true;
      this.showRegisterToFeedlyButton = true;
      this.showRemovelistButton = true;
      this.showRemoveHtmlButton = true;
      this.showToggleFeedButton = true;
      this.showRemoveFeedButton = true;
      this.showFeedInfo = true;
      this.initJsonEditor();
    },
    hideAllRelatedToFeed: function () {
      this.showEditor = false;
      this.showNewFeedNameInput = false;
      this.showRunButton = false;
      this.showViewRssButton = false;
      this.showRegisterToInoreaderButton = false;
      this.showRegisterToFeedlyButton = false;
      this.showRemovelistButton = false;
      this.showRemoveHtmlButton = false;
      this.showToggleFeedButton = false;
      this.showRemoveFeedButton = false;
      this.showFeedInfo = false;
      this.clearAlert();
      if (this.jsonEditor) {
        this.jsonEditor.destroy();
        this.jsonEditor = null;
      }
    },
    showAllRelatedToGroup: function () {
      if (this.selectedGroupName) {
        this.showToggleGroupButton = true;
        this.showRemoveGroupButton = true;
      }
    },
    hideAllRelatedToGroup: function () {
      this.showToggleGroupButton = false;
      this.showRemoveGroupButton = false;
    },
    showAllRelatedToSiteConfig: function () {
      this.showEditor = true;
      this.showSiteConfig = true;
      this.initJsonEditor();
    },
    hideAllRelatedToSiteConfig: function () {
      this.showEditor = false;
      this.showSiteConfig = false;
      if (this.jsonEditor) {
        this.jsonEditor.destroy();
        this.jsonEditor = null;
      }
    },

    search: function () {
      console.log(`search()`);
      this.showSearchResult = true;
      this.showGrouplist = false;
      this.showFeedlist = false;
      this.showFeedlistButton = false;
      this.hideAllRelatedToGroup();
      this.hideAllRelatedToFeed();

      const url = getApiUrlPath() + `/search/${this.searchKeyword}`;
      axios
        .get(url)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          } else {
            this.feeds = res.data.feeds;
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    grouplistButtonClicked: function () {
      console.log(`grouplistButtonClicked()`);
      this.showGrouplist = true;
      this.showFeedlist = false;
      this.showFeedlistButton = false;
      this.showSearchResult = false;
      this.hideAllRelatedToGroup();
      this.hideAllRelatedToSiteConfig();

      this.getGroups();
    },
    getGroups: function () {
      console.log(`getGroups()`);
      if (this.checkRunningInterval) {
        clearInterval(this.checkRunningInterval);
      }
      const url = getApiUrlPath() + "/groups";
      axios
        .get(url)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          } else {
            this.groups = res.data.groups || [];
            this.feeds = [];
            this.activeFeedIndex = undefined;
            this.activeGroupIndex = undefined;
            this.selectedFeedName = "";
            this.selectedGroupName = "";
            this.showRemoveFeedButton = false;
            this.showRemoveGroupButton = false;

            this.hideAllRelatedToFeed();
            this.showAllRelatedToGroup();
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    feedlistButtonClicked: function () {
      console.log(`feedlistButtonClicked()`);
      this.showGrouplist = false;
      this.showFeedlist = true;
      this.hideAllRelatedToSiteConfig();

      this.getFeedlistByGroup(this.selectedGroupName);
    },
    groupNameButtonClicked: function (groupName, index) {
      console.log(`groupNameButtonClicked(${groupName}, ${index})`);
      if (index) {
        this.setActiveGroup(index);
      }
      this.selectedGroupName = groupName;

      // show and hide
      this.showGrouplist = false;
      this.showFeedlist = true;
      this.showFeedlistButton = true;
      this.hideAllRelatedToSiteConfig();

      this.getFeedlistByGroup(groupName);
    },
    getFeedlistByGroup: function (groupName) {
      console.log(`getFeedlistByGroup(${groupName})`);
      if (this.checkRunningInterval) {
        clearInterval(this.checkRunningInterval);
      }
      const url = getApiUrlPath() + `/groups/${groupName}/feeds`;
      axios
        .get(url)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          } else {
            this.feeds = res.data.feeds || [];
            this.activeFeedIndex = undefined;
            this.selectedFeedName = "";

            this.hideAllRelatedToFeed();
            this.showAllRelatedToGroup();
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    searchResultFeedNameButtonClicked: function (groupName, feedName, index) {
      console.log(
        `searchResultFeedNameButtonClicked(${groupName}, ${feedName}, ${index})`
      );
      if (index) {
        this.setActiveFeed(index);
      }
      this.selectedGroupName = groupName;
      this.selectedFeedName = feedName;

      // show and hide
      this.showFeedlist = false;
      this.showFeedlistButton = false;

      this.getFeedInfo(groupName, feedName);
    },
    feedNameButtonClicked: function (groupName, feedName, index) {
      console.log(`feedNameButtonClicked(${groupName}, ${feedName}, ${index})`);
      if (index) {
        this.setActiveFeed(index);
      }
      this.selectedFeedName = feedName;

      // show and hide
      this.showFeedlist = false;
      this.showFeedlistButton = true;

      if (feedName === "site_config.json") {
        this.getSiteConfig();
      } else {
        this.getFeedInfo(groupName, feedName);
      }
    },
    setCollectionInfo: function (collectionInfo, list_url_list_count) {
      this.numCollectionUrls = list_url_list_count;
      this.collectDate = this.getShortDateStr(collectionInfo["collect_date"]);
      this.totalItemCount = collectionInfo["total_item_count"];
    },
    setPublicFeedInfo: function (publicFeedInfo) {
      this.numItemsInResult = publicFeedInfo["num_items"];
      this.sizeOfResultFile = publicFeedInfo["file_size"];
      if (publicFeedInfo["upload_date"]) {
        this.lastUploadDate = this.getShortDateStr(
          publicFeedInfo["upload_date"]
        );
      }
    },
    setProgressInfo: function (progressInfo) {
      this.currentIndex = progressInfo["current_index"];
      this.totalItemCount = progressInfo["total_item_count"];
      this.unitSizePerDay = progressInfo["unit_size_per_day"];
      this.progressRatio = progressInfo["progress_ratio"];
      if (progressInfo["due_date"]) {
        this.feedCompletionDueDate = this.getShortDateStr(
          progressInfo["due_date"]
        );
      }
    },
    getFeedInfo: function (groupName, feedName) {
      console.log(`getFeedInfo(${groupName}, ${feedName})`);
      const url =
        getApiUrlPath() + `/groups/${groupName}/feeds/${feedName}`;
      if (this.checkRunningInterval) {
        clearInterval(this.checkRunningInterval);
      }
      axios
        .get(url)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          } else {
            const feed_info = res.data["feed_info"];
            this.jsonData = feed_info["config"];

            this.setCollectionInfo(
              feed_info["collection_info"],
              feed_info["config"]["collection"]["list_url_list"].length
            );
            this.setPublicFeedInfo(feed_info["public_feed_info"]);
            this.setProgressInfo(feed_info["progress_info"]);
            this.determineNewFeedNameFromJsonRssLink();
            if (Object.keys(this.jsonData).length >= 3) {
              this.showAllRelatedToFeed();
            } else {
              this.hideAllRelatedToFeed();
            }
            this.hideAllRelatedToGroup();

            this.checkRunning();
            this.checkRunningInterval = setInterval(() => {
              this.checkRunning();
            }, 3000);
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    getSiteConfig: function () {
      console.log(`getSiteConfig()`);
      const url =
        getApiUrlPath() + `/groups/${this.selectedGroupName}/site_config`;
      axios
        .get(url)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          } else {
            this.jsonData = res.data.configuration;
            this.hideAllRelatedToFeed();
            this.hideAllRelatedToGroup();
            if (Object.keys(this.jsonData).length >= 2) {
              this.showAllRelatedToSiteConfig();
            }
          }
        })
        .catch((error) => {
          console.error(error);
        });
    },
    saveSiteConfig: function () {
      console.log(`saveSiteConfig()`);
      this.openConfirmModal("정말로 실행하시겠습니까?", () => {
        this.startButton("saveSiteConfigButton");
        const postData = this.jsonData;
        const url =
          getApiUrlPath() +
          `/groups/${this.selectedGroupName}/site_config`;
        axios
          .put(url, postData)
          .then((res) => {
            if (res.data.status === "failure") {
              this.alert(res.data.message);
            }
            this.endButton("saveSiteConfigButton");
          })
          .catch((error) => {
            console.error(error);
            this.resetButton("saveSiteConfigButton");
          });
      });
    },
    save: function () {
      console.log(`save()`);
      this.startButton("saveButton");
      const postData = { configuration: this.jsonData };
      const url =
        getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}`;
      axios
        .post(url, postData)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          } else {
            this.selectedFeedName = this.newFeedName;
            console.log(`selectedFeedName is set to ${this.selectedFeedName}`);
          }
          this.getFeedInfo(this.selectedGroupName, this.newFeedName);
          this.endButton("saveButton");
        })
        .catch((error) => {
          console.error(error);
          this.resetButton("saveButton");
        });
    },
    run: function () {
      console.log(`run()`);
      this.startButton("runButton");
      const url =
        getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}/run`;
      const postData = {};
      axios
        .post(url, postData)
        .then((res) => {
          if (res.data.status === "failure") {
            this.alert(res.data.message);
          }
          this.getFeedInfo(this.selectedGroupName, this.newFeedName);
          this.endButton("runButton");
        })
        .catch((error) => {
          console.error(error);
          this.resetButton("runButton");
        });
    },
    viewRss() {
      console.log(`viewRss()`);
      window.open(this.rssUrl);
    },
    registerToInoreader: function () {
      console.log(`registerToInoreader()`);
      const feederLink =
        "https://www.inoreader.com/search/feeds/" + encodeURIComponent(this.rssUrl);
      window.open(feederLink);
    },
    registerToFeedly: function () {
      console.log(`registerToFeedly()`);
      const feederLink =
        "https://feedly.com/i/discover/sources?query=feed/" +
        encodeURIComponent(this.rssUrl);
      window.open(feederLink);
    },
    toggleStatus: function (target) {
      console.log(`toggleStatus(${target})`);
      let url = "";
      if (target === "feed") {
        url =
          getApiUrlPath() +
          `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/toggle`;
      } else {
        url = getApiUrlPath() + `/groups/${this.selectedGroupName}/toggle`;
      }

      this.openConfirmModal("정말로 실행하시겠습니까?", () => {
        if (target === "feed") {
          this.startButton("toggleFeedButton");
        } else {
          this.startButton("toggleGroupButton");
        }
        axios
          .put(url)
          .then((res) => {
            if (res.data.status === "failure") {
              this.alert(res.data.message);
            } else {
              if (target === "feed") {
                this.newFeedName = res.data["new_name"];
                this.getFeedlistByGroup(this.selectedGroupName);
                this.showFeedlist = true;
                this.hideAllRelatedToFeed();
              } else {
                this.selectedGroupName = res.data["new_name"];
                this.getGroups();
                this.showGrouplist = true;
                this.showFeedlist = false;
                this.hideAllRelatedToFeed();
                this.hideAllRelatedToGroup();
              }
            }
            if (target === "feed") {
              this.endButton("toggleFeedButton");
            } else {
              this.endButton("toggleGroupButton");
            }
          })
          .catch((error) => {
            console.error(error);
            if (target === "feed") {
              this.resetButton("toggleFeedButton");
            } else {
              this.resetButton("toggleGroupButton");
            }
          });
      });
    },
    removelist: function () {
      console.log(`removelist()`);
      this.openConfirmModal("정말로 실행하시겠습니까?", () => {
        this.startButton("removelistButton");
        const url =
          getApiUrlPath() +
          `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/list`;
        axios
          .delete(url)
          .then((res) => {
            if (res.data.status === "failure") {
              this.alert(res.data.message);
            }
            this.endButton("removelistButton");
          })
          .catch((error) => {
            console.error(error);
            this.resetButton("removelistButton");
          });
      });
    },
    removeHtml: function () {
      console.log(`removeHtml()`);
      this.openConfirmModal("정말로 실행하시겠습니까?", () => {
        this.startButton("removeHtmlButton");
        const url =
          getApiUrlPath() +
          `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/htmls`;
        axios
          .delete(url)
          .then((res) => {
            if (res.data.status === "failure") {
              this.alert(res.data.message);
            }
            this.endButton("removeHtmlButton");
          })
          .catch((error) => {
            console.error(error);
            this.resetButton("removeHtmlButton");
          });
      });
    },
    removeFeed: function () {
      console.log(`removeFeed()`);
      if (!this.selectedFeedName) {
        this.alert("Feed is not selected");
        return;
      }

      this.openConfirmModal("정말로 실행하시겠습니까?", () => {
        this.startButton("removeFeedButton");
        const url =
          getApiUrlPath() +
          `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}`;
        axios
          .delete(url)
          .then((res) => {
            if (res.data.status === "failure") {
              this.alert(res.data.message);
            } else {
              this.getFeedlistByGroup(this.selectedGroupName);
            }
            this.showEditor = false;
            this.endButton("removeFeedButton");
          })
          .catch((error) => {
            console.error(error);
            this.resetButton("removeFeedButton");
          });
      });
    },
    removeGroup: function () {
      console.log(`removeGroup()`);
      if (!this.selectedGroupName) {
        this.alert("Group is not selected");
        return;
      }
      this.openConfirmModal("정말로 실행하시겠습니까?", () => {
        this.startButton("removeGroupButton");
        const url =
          getApiUrlPath() + `/groups/${this.selectedGroupName}`;
        axios
          .delete(url)
          .then((res) => {
            if (res.data.status === "failure") {
              this.alert(res.data.message);
            } else {
              this.getGroups();
            }
            this.showEditor = false;
            this.endButton("removeGroupButton");
          })
          .catch((error) => {
            console.error(error);
            this.resetButton("removeGroupButton");
          });
      });
    },
    getItemsOfRss: function () {
      console.log(`getItemsOfRss()`);
      const url =
        getApiUrlPath() + `/public_feeds/${this.selectedFeedName}/item_titles`;
      axios.get(url).then((res) => {
        console.log("getItemsOfRss response:", res.data);
        if (res.data.status === "success") {
          // 성공 시, 데이터가 있는지 확인하고 렌더링
          if (res.data.item_titles && res.data.item_titles.length > 0) {
            this.itemsOfRss = res.data.item_titles;
            this.showViewItemsOfRssList = true;
          } else {
            // 성공했지만 아이템이 없는 경우
            this.alert("피드 파일에 아이템이 없습니다.");
            this.itemsOfRss = [];
            this.showViewItemsOfRssList = false;
          }
        } else {
          // 'failure' status
          if (res.data.error_code) {
            if (res.data.error_code === 'FILE_NOT_FOUND') {
              this.alert("피드 파일이 존재하지 않습니다.");
            } else if (res.data.error_code === 'NO_ITEMS') {
              this.alert("피드 파일에 아이템이 없습니다.");
            } else {
              // Other specific errors like PARSE_ERROR
              this.alert(res.data.message || "알 수 없는 에러가 발생했습니다.");
            }
          } else {
            // Generic failure message
            this.alert(res.data.message || "데이터를 가져오는데 실패했습니다.");
          }
          this.itemsOfRss = [];
          this.showViewItemsOfRssList = false;
        }
      }).catch(error => {
        console.error("Error fetching RSS items:", error);
        this.alert("요청 처리 중 에러가 발생했습니다: " + (error.response ? error.response.status : error.message));
        this.itemsOfRss = [];
        this.showViewItemsOfRssList = false;
      });
    },
    checkRunning: function () {
      //console.log(`checkRunning()`);
      const url =
        getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/check_running`;
      console.log("checkRunning URL:", url);
      axios
        .get(url)
        .then((res) => {
          console.log("checkRunning response:", res.data);
          if (res.data.status === "failure") {
            this.alert(res.data.message);
            this.resetButton("runButton");
            if (this.checkRunningInterval) {
              clearInterval(this.checkRunningInterval);
            }
          } else {
            console.log("running_status:", res.data.running_status, "type:", typeof res.data.running_status);
            if (res.data.running_status === true) {
              console.log("Starting run button spinner");
              this.startButton("runButton");
            } else {
              console.log("Stopping run button spinner");
              this.endButton("runButton");
            }
          }
        })
        .catch((error) => {
          console.error("checkRunning error:", error);
          this.resetButton("runButton");
        });
    },
    initJsonEditor: function () {
      if (this.jsonEditor) {
        this.jsonEditor.destroy();
        this.jsonEditor = null;
      }

      this.$nextTick(() => {
        if (this.$refs.jsonEditorContainer) {
          this.jsonEditor = new JSONEditor(this.$refs.jsonEditorContainer, {
            mode: 'tree',
            modes: ['tree', 'code', 'text'],
            onChange: () => {
              try {
                this.jsonData = this.jsonEditor.get();
              } catch (e) {
                console.error('JSON 에디터 데이터 가져오기 실패:', e);
              }
            }
          });

          if (this.jsonData && Object.keys(this.jsonData).length > 0) {
            this.jsonEditor.set(this.jsonData);
            this.jsonEditor.expandAll();
          }
        }
      });
    },
    updateJsonEditor: function () {
      if (this.jsonEditor && this.jsonData) {
        this.jsonEditor.set(this.jsonData);
      }
    },
  },
  mounted: function () {
    // 안전한 초기화
    this.groups = this.groups || [];
    this.feeds = this.feeds || [];

    // Check session expiry before authorization check
    const sessionExpiry = localStorage.getItem("session_expiry");
    if (sessionExpiry && new Date().getTime() > parseInt(sessionExpiry)) {
      console.log("Session expired, redirecting to login");
      this.$session.clear();
      this.$router.push("/login");
      return;
    }

    if (this.$session.get("is_authorized")) {
      if (this.$route.params["group"] && this.$route.params["feed"]) {
        this.selectedGroupName = this.$route.params["group"];
        this.selectedFeedName = this.$route.params["feed"];
        return this.feedNameButtonClicked(
          this.selectedGroupName,
          this.selectedFeedName
        );
      } else {
        return this.getGroups();
      }
    } else {
      this.$router.push("/login");
    }
  },
  beforeUnmount: function () {
    if (this.checkRunningInterval) {
      clearInterval(this.checkRunningInterval);
    }
    if (this.jsonEditor) {
      this.jsonEditor.destroy();
      this.jsonEditor = null;
    }
  },
};
</script>
