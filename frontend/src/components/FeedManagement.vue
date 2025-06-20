<template>
  <b-container fluid>
    <!-- 그룹과 피드 목록 제어 버튼 -->
    <b-row>
      <b-col cols="12" class="m-0 p-1">
        <span class="button_list">
        <my-button
            ref="grouplistButton"
            label="그룹 목록"
            variant="success"
            @click="grouplistButtonClicked"/>
        <my-button
            ref="feedlistButton"
            :label="selectedGroupName + ' 그룹의 피드 목록'"
            @click="feedlistButtonClicked"
            v-if="showFeedlistButton"/>
        </span>

        <b-input-group
            class="float-right m-0 p-1"
            style="width: 300px">
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
      <b-col id="search_result" cols="12" class="m-0 p-1 button_list" v-if="showSearchResult">
        <my-button
            ref="searchResultFeedButton"
            :label="feed['group_name'] + '/' + feed['feed_title']"
            variant="success"
            @click="searchResultFeedNameButtonClicked(feed['group_name'], feed['feed_name'], index)"
            :class="{'active': activeFeedIndex === index, 'bg-secondary': !determineStatus(feed['feed_name'])}"
            v-for="(feed, index) in feeds"
            :key="feed['group_name'] + '/' + feed['feed_name']"/>
      </b-col>
    </b-row>

    <!-- 그룹 목록 -->
    <b-row>
      <b-col id="group_list" cols="12" class="m-0 p-1 button_list" v-if="showGrouplist">
        <my-button
            ref="groupNameButton"
            :label="group.name + ' (' + group['num_feeds'] + ')'"
            variant="success"
            @click="groupNameButtonClicked(group.name, index)"
            :class="{'active': activeGroupIndex === index, 'bg-secondary': !determineStatus(group.name)}"
            v-for="(group, index) in groups"
            :key="group.name"/>
        <div class="p-2" v-if="!groups.length">
          그룹 목록 없음
        </div>
      </b-col>
    </b-row>

    <!-- 피드 목록 -->
    <b-row>
      <b-col
          id="feed_list"
          cols="12"
          class="m-0 p-1 button_list"
          v-if="showFeedlist">
        <my-button
            ref="feedNameButton"
            :label="feed.title"
            @click="feedNameButtonClicked(selectedGroupName, feed.name, index)"
            :class="{'active': activeFeedIndex === index, 'bg-secondary': !determineStatus(feed.name)}"
            v-for="(feed, index) in feeds"
            :key="feed.name"/>
        <div class="p-2" v-if="!feeds.length">
          피드 목록 없음
        </div>
      </b-col>
    </b-row>

    <!-- 설정 편집기 및 액션, 메타데이터 영역 -->
    <b-row>
      <!-- 설정 편집기 영역 -->
      <b-col
          id="configuration"
          cols="12"
          lg="8"
          class="m-0 p-1">
        <vue-json-editor
            :expandedOnStart="true"
            :mode="'tree'"
            v-model="jsonData"
            v-if="showEditor">
        </vue-json-editor>
        <div class="p-2" v-if="!showEditor">
          설정 파일 없음
        </div>
      </b-col>

      <!-- 정보, 메타데이터, 액션 영역 -->
      <b-col
          cols="12"
          lg="4"
          class="m-0 p-0">

        <!-- 정보 영역 -->
        <b-row
            id="feed_info"
            class="m-0 p-0"
            v-if="showNewFeedNameInput">
          <b-col
              cols="12"
              class="m-0 p-1"
              :class="{'bg-secondary': !feedStatus}">
            <div>{{ title }}</div>
            <div>{{ selectedGroupName + '/' + selectedFeedName }}</div>
          </b-col>
        </b-row>

        <!-- 메타데이터 영역 -->
        <b-row
            id="metadata"
            class="m-0 p-0"
            v-if="showFeedInfo">
          <b-col
              cols="12"
              class="m-0 p-1">
            <b-table-simple
                class="m-0 p-1 text-break"
                small>
              <b-thead head-variant="light" table-variant="light">
                <b-tr>
                  <b-th colspan="4">메타데이터</b-th>
                </b-tr>
              </b-thead>
              <b-tbody>
                <b-tr v-if="numCollectionUrls && totalItemCount">
                  <b-td>수집</b-td>
                  <b-td>{{ numCollectionUrls }} 개 페이지</b-td>
                  <b-td>{{ totalItemCount }} 개 피드</b-td>
                  <b-td>{{ collectDate }}</b-td>
                </b-tr>
                <b-tr v-if="numItemsInResult && sizeOfResultFileWithUnit">
                  <b-td>피드</b-td>
                  <b-td>{{ numItemsInResult }} 개 피드</b-td>
                  <b-td>{{ sizeOfResultFileWithUnit }}</b-td>
                  <b-td>{{ lastUploadDate }}</b-td>
                </b-tr>
                <b-tr v-if="totalItemCount >= 0 && currentIndex >=0 && unitSizePerDay >= 0">
                  <b-td>진행 상태</b-td>
                  <b-td colspan="2">
                    <b-progress :max="totalItemCount" show-progress height="1.5rem">
                      <b-progress-bar :value="currentIndex" variant="warning">
                        <div style="position: absolute; width: 100%; color: black; text-align: left; overflow: visible;">{{ currentIndex }} 번 / {{ totalItemCount }} 개 = {{ progressRatio }} %, {{ unitSizePerDay }} 개/일</div>
                      </b-progress-bar>
                    </b-progress>
                  </b-td>
                  <b-td>{{ feedCompletionDueDate }}</b-td>
                </b-tr>
              </b-tbody>
            </b-table-simple>
          </b-col>
        </b-row>

        <!-- 액션 영역 -->
        <b-row
            id="actions"
            class="m-0 p-0">
          <b-col
              cols="12"
              class="m-0 p-1"
              v-if="showAlert">
            <b-alert
                class="mb-0"
                variant="danger"
                dismissible
                v-if="showAlert">
              {{ alertMessage }}
            </b-alert>
          </b-col>

          <b-col
              cols="12"
              class="m-0 p-1">
            <b-input-group
                prepend="피드"
                class="m-0"
                v-if="showNewFeedNameInput">
              <b-form-input class="m-0" v-model="newFeedName">
                {{ newFeedName }}
              </b-form-input>
              <b-input-group-append>
                <my-button
                    ref="saveButton"
                    label="저장"
                    @click="save"
                    :initial-icon="['far', 'save']"
                    :show-initial-icon="true"/>
              </b-input-group-append>
            </b-input-group>
          </b-col>

          <b-col
              cols="12"
              class="m-0 p-1 button_list"
              v-if="showSiteConfig || showToggleGroupButton || showRemoveGroupButton">
            <my-button
                ref="saveSiteConfigButton"
                label="그룹 설정 저장"
                @click="saveSiteConfig"
                :initial-icon="['far', 'save']"
                :show-initial-icon="true"
                v-if="showSiteConfig"/>
            <my-button
                ref="toggleGroupButton"
                :label="groupStatusLabel"
                variant="success"
                @click="toggleStatus('group')"
                :initial-icon="['fas', groupStatusIcon]"
                :show-initial-icon="true"
                v-if="showToggleGroupButton"/>
            <my-button
                ref="removeGroupButton"
                label="그룹 삭제"
                variant="success"
                @click="removeGroup"
                :initial-icon="['far', 'trash-alt']"
                :show-initial-icon="true"
                v-if="showRemoveGroupButton"/>
          </b-col>

          <b-col
              cols="12"
              class="m-0 p-1 button_list">
            <my-button
                ref="runButton"
                label="실행"
                @click="run"
                :initial-icon="['fas', 'play']"
                :show-initial-icon="true"
                v-if="showRunButton"/>
            <my-button
                ref="removelistButton"
                label="리스트 삭제"
                @click="removelist"
                :initial-icon="['fas', 'eraser']"
                :show-initial-icon="true"
                v-if="showRemovelistButton"/>
            <my-button
                ref="removeHtmlButton"
                label="HTML 삭제"
                @click="removeHtml"
                :initial-icon="['fas', 'eraser']"
                :show-initial-icon="true"
                v-if="showRemoveHtmlButton"/>
            <my-button
                ref="toggleFeedButton"
                :label="feedStatusLabel"
                @click="toggleStatus('feed')"
                :initial-icon="['fas', feedStatusIcon]"
                :show-initial-icon="true"
                v-if="showToggleFeedButton"/>
            <my-button
                ref="removeFeedButton"
                label="피드 삭제"
                @click="removeFeed"
                :initial-icon="['far', 'trash-alt']"
                :show-initial-icon="true"
                variant="danger"
                v-if="showRemoveFeedButton"/>
          </b-col>

          <b-col
              cols="12"
              class="m-0 p-1 button_list">
            <my-button
                ref="viewRssButton"
                label="RSS"
                @click="viewRss"
                :initial-icon="['fas', 'rss']"
                :show-initial-icon="true"
                v-if="showViewRssButton"/>
            <my-button
                ref="registerButton"
                label="Inoreader"
                @click="registerToInoreader"
                :initial-icon="['fas', 'rss']"
                :show-initial-icon="true"
                v-if="showRegisterToInoreaderButton"/>
            <my-button
                ref="registerButton"
                label="Feedly"
                @click="registerToFeedly"
                :initial-icon="['fas', 'rss']"
                :show-initial-icon="true"
                v-if="showRegisterToFeedlyButton"/>
          </b-col>
        </b-row>
      </b-col>
    </b-row>

    <b-row>
      <b-col
          cols="12"
          class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
#group_list, #feed_list, #configuration, #feed_info, #metadata, #actions {
  border: 1px lightgray solid;
  border-collapse: collapse;
  padding: 2px !important;
}

.button_list button {
  margin: 2px 3px 3px 2px !important;
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
import vueJsonEditor from 'vue-json-editor';
import axios from 'axios';
import {library} from '@fortawesome/fontawesome-svg-core';
import {faTrashAlt, faSave} from '@fortawesome/free-regular-svg-icons';
import {faSearch, faRss, faPlay, faToggleOn, faToggleOff, faEraser, faPen, faEye} from '@fortawesome/free-solid-svg-icons';
import MyButton from './MyButton';

library.add(faTrashAlt, faSave, faSearch, faRss, faPlay, faToggleOn, faToggleOff, faEraser, faPen, faEye);

export default {
  name: 'FeedManagement',
  components: {
    vueJsonEditor,
    MyButton
  },
  props: ['feed', 'group'],
  data: function () {
    return {
      alertMessage: '',

      showGrouplist: true,
      showFeedlist: false,
      showFeedlistButton: false,
      showSearchResult: false,

      showEditor: false,

      showAlert: false,
      showRunButton: false,
      showViewRssButton: false,
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

      activeGroupIndex: undefined,
      activeFeedIndex: undefined,

      groups: [],
      feeds: [],
      jsonData: {},
      selectedGroupName: '',
      selectedFeedName: '',
      newFeedName: '',
      searchKeyword: '',

      numCollectionUrls: 0,
      collectDate: '-',
      urllistCount: 0,
      numItemsInResult: 0,
      sizeOfResultFile: 0,
      lastUploadDate: '-',
      currentIndex: 0,
      totalItemCount: 0,
      unitSizePerDay: 0,
      progressRatio: 0.0,
      feedCompletionDueDate: '-',

      checkRunningInterval: null,
    };
  },
  computed: {
    feedStatus: function () {
      return this.selectedFeedName[0] !== '_';
    },
    groupStatus: function () {
      return this.selectedGroupName[0] !== '_';
    },
    feedStatusLabel: function () {
      return '피드 ' + (this.feedStatus ? '비활성화' : '활성화');
    },
    feedStatusIcon: function () {
      return 'toggle-' + (this.feedStatus ? 'off' : 'on');
    },
    groupStatusLabel: function () {
      return '그룹 ' + (this.groupStatus ? '비활성화' : '활성화');
    },
    groupStatusIcon: function () {
      return 'toggle-' + (this.feedStatus ? 'off' : 'on');
    },
    title: function () {
      return this.jsonData.rss['title'];
    },
    rssUrl: function () {
      return `https://terzeron.com/${this.newFeedName}.xml`;
    },
    adminEmail: function () {
      return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
    },
    sizeOfResultFileWithUnit: function () {
      if (this.sizeOfResultFile > 1024 * 1024 * 1024) {
        return (this.sizeOfResultFile / 1024 / 1024 / 1024).toFixed(2) + ' GiB';
      } else if (this.sizeOfResultFile > 1024 * 1024) {
        return (this.sizeOfResultFile / 1024 / 1024).toFixed(2) + ' MiB';
      } else if (this.sizeOfResultFile > 1024) {
        return (this.sizeOfResultFile / 1024).toFixed(2) + ' KiB';
      } else {
        return this.sizeOfResultFile + ' B';
      }
    },
  },
  watch: {
    newFeedName: function (val) {
      this.jsonData.rss.link = 'https://terzeron.com/' + val + '.xml';
    },
    jsonData: function () {
      this.determineNewFeedNameFromJsonRssLink();
      this.determineDescriptionFromTitle();
    }
  },
  methods: {
    getApiUrlPath: function () {
      return process.env.VUE_APP_API_URL;
    },
    getShortDateStr: function(dateStr) {
      if (!dateStr) {
        return '';
      }
      return dateStr.split("T")[0];
    },
    determineNewFeedNameFromJsonRssLink: function () {
      if ('rss' in this.jsonData && 'link' in this.jsonData['rss']) {
        const re = /https:\/\/terzeron.com\/_?(.+)\.xml/;
        const matched = this.jsonData.rss.link.match(re);
        if (matched) {
          this.newFeedName = matched[1];
        }
      }
    },
    determineDescriptionFromTitle: function () {
      if ('rss' in this.jsonData && 'title' in this.jsonData.rss && 'description' in this.jsonData.rss) {
        this.jsonData.rss['description'] = this.jsonData.rss['title'];
      }
    },
    setActiveGroup: function (index) {
      this.activeGroupIndex = index;
    },
    setActiveFeed: function (index) {
      this.activeFeedIndex = index;
    },
    alert: function (message) {
      this.alertMessage = message;
      this.showAlert = true;
    },
    clearAlert: function () {
      this.alertMessage = '';
      this.showAlert = false;
    },
    determineStatus: function (name) {
      return name[0] !== '_';
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
      this.showFeedInfo = false
      this.clearAlert();
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
    },
    hideAllRelatedToSiteConfig: function () {
      this.showEditor = false;
      this.showSiteConfig = false;
    },

    search: function () {
      console.log(`search()`);
      this.showSearchResult = true;
      this.showGrouplist = false;
      this.showFeedlist = false;
      this.showFeedlistButton = false;
      this.hideAllRelatedToGroup();
      this.hideAllRelatedToFeed();

      const url = this.getApiUrlPath() + `/search/${this.searchKeyword}`;
      axios
          .get(url)
          .then((res) => {
                if (res.data.status === 'failure') {
                  this.alert(res.data.message);
                } else {
                  this.feeds = res.data.feeds;
                }
              }
          )
          .catch((error) => {
            console.error(error);
          })
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
      const url = this.getApiUrlPath() + '/groups';
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.groups = res.data.groups;
              this.feeds = [];
              this.activeFeedIndex = undefined;
              this.activeGroupIndex = undefined;
              this.selectedFeedName = '';
              this.selectedGroupName = '';
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
      const url = this.getApiUrlPath() + `/groups/${groupName}/feeds`;
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.feeds = res.data.feeds;
              this.activeFeedIndex = undefined;
              this.selectedFeedName = '';

              this.hideAllRelatedToFeed();
              this.showAllRelatedToGroup();
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    searchResultFeedNameButtonClicked: function (groupName, feedName, index) {
      console.log(`searchResultFeedNameButtonClicked(${groupName}, ${feedName}, ${index})`);
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

      if (feedName === 'site_config.json') {
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
        this.lastUploadDate = this.getShortDateStr(publicFeedInfo["upload_date"]);
      }
    },
    setProgressInfo: function (progressInfo) {
      this.currentIndex = progressInfo["current_index"];
      this.totalItemCount = progressInfo["total_item_count"];
      this.unitSizePerDay = progressInfo["unit_size_per_day"];
      this.progressRatio = progressInfo["progress_ratio"];
      if (progressInfo["due_date"]) {
        this.feedCompletionDueDate = this.getShortDateStr(progressInfo["due_date"]);
      }
    },
    getFeedInfo: function (groupName, feedName) {
      console.log(`getFeedInfo(${groupName}, ${feedName})`);
      const url = this.getApiUrlPath() + `/groups/${groupName}/feeds/${feedName}`;
      if (this.checkRunningInterval) {
        clearInterval(this.checkRunningInterval);
      }
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              const feed_info = res.data["feed_info"];
              this.jsonData = feed_info["config"];

              this.setCollectionInfo(feed_info["collection_info"], feed_info["config"]["collection"]["list_url_list"].length);
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
              this.checkRunningInterval = () => {
                  this.checkRunning(); setInterval(() => { this.checkRunning(); }, 3000);
              };
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    getSiteConfig: function () {
      console.log(`getSiteConfig()`);
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/site_config`;
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
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
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            this.startButton('saveSiteConfigButton');
            if (value) {
              const postData = this.jsonData;
              const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/site_config`;
              axios
                  .put(url, postData)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    }
                    this.endButton('saveSiteConfigButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('saveSiteConfigButton');
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    save: function () {
      console.log(`save()`);
      this.startButton('saveButton');
      const postData = {configuration: this.jsonData};
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}`;
      axios
          .post(url, postData)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.selectedFeedName = this.newFeedName;
              console.log(`selectedFeedName is set to ${this.selectedFeedName}`);
            }
            this.getFeedInfo(this.selectedGroupName, this.newFeedName);
            this.endButton('saveButton');
          })
          .catch((error) => {
            console.error(error);
            this.resetButton('saveButton');
          });
    },
    run: function () {
      console.log(`run()`);
      this.startButton('runButton');
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}/run`;
      const postData = {};
      axios
          .post(url, postData)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            }
            this.getFeedInfo(this.selectedGroupName, this.newFeedName);
            this.endButton('runButton');
          })
          .catch((error) => {
            console.error(error);
            this.resetButton('runButton');
          });
    },
    viewRss() {
      console.log(`viewRss()`);
      window.open(this.rssUrl);
    },
    registerToInoreader: function () {
      console.log(`registerToInoreader()`);
      const feederLink = 'https://www.inoreader.com/feed/' + encodeURIComponent(this.rssUrl);
      window.open(feederLink);
    },
    registerToFeedly: function () {
      console.log(`registerToFeedly()`);
      const feederLink = 'https://feedly.com/i/discover/sources/search/feed/' + encodeURIComponent(this.rssUrl);
      window.open(feederLink);
    },
    toggleStatus: function (target) {
      console.log(`toggleStatus(${target})`);
      let url = '';
      if (target === 'feed') {
        url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/toggle`;
      } else {
        url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/toggle`;
      }

      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              if (target === 'feed') {
                this.startButton('toggleFeedButton');
              } else {
                this.startButton('toggleGroupButton');
              }
              axios
                  .put(url)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    } else {
                      if (target === 'feed') {
                        this.newFeedName = res.data['new_name'];
                        this.getFeedlistByGroup(this.selectedGroupName);
                        this.showFeedlist = true;
                        this.hideAllRelatedToFeed();
                      } else {
                        this.selectedGroupName = res.data['new_name'];
                        this.getGroups();
                        this.showGrouplist = true;
                        this.showFeedlist = false
                        this.hideAllRelatedToFeed();
                        this.hideAllRelatedToGroup();
                      }
                    }
                    if (target === 'feed') {
                      this.endButton('toggleFeedButton');
                    } else {
                      this.endButton('toggleGroupButton');
                    }
                  })
                  .catch((error) => {
                    console.error(error);
                    if (target === 'feed') {
                      this.resetButton('toggleFeedButton');
                    } else {
                      this.resetButton('toggleGroupButton');
                    }
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removelist: function () {
      console.log(`removelist()`);
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.startButton('removelistButton');
              const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/list`;
              axios
                  .delete(url)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    }
                    this.endButton('removelistButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('removelistButton');
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeHtml: function () {
      console.log(`removeHtml()`);
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.startButton('removeHtmlButton');
              const url = this.getApiUrlPath() +
                  `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/htmls`;
              axios
                  .delete(url)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    }
                    this.endButton('removeHtmlButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('removeHtmlButton');
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeFeed: function () {
      console.log(`removeFeed()`);
      if (!this.selectedFeedName) {
        this.alert('피드가 선택되지 않았습니다.');
        return;
      }
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.startButton('removeFeedButton');
              const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}`;
              axios
                  .delete(url)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    } else {
                      this.getFeedlistByGroup(this.selectedGroupName);
                    }
                    this.showEditor = false;
                    this.endButton('removeFeedButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('removeFeedButton');
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeGroup: function () {
      console.log(`removeGroup()`);
      if (!this.selectedGroupName) {
        this.alert('그룹이 선택되지 않았습니다.');
        return;
      }
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.startButton('removeGroupButton');
              const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}`;
              axios
                  .delete(url)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    } else {
                      this.getGroups();
                    }
                    this.showEditor = false;
                    this.endButton('removeGroupButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('removeGroupButton');
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    checkRunning: function () {
      //console.log(`checkRunning()`);
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/check_running`;
      console.log(url);
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
              this.resetButton('runButton');
              if (this.checkRunningInterval) {
                clearInterval(this.checkRunningInterval);
              }
            } else {
              if (res.data.running_status) {
                this.startButton('runButton');
              } else {
                this.endButton('runButton');
              }
            }
          })
          .catch((error) => {
            console.error(error);
            this.resetButton('runButton');
          });
    },
  },
  mounted: function () {
    if (this.$session.get('is_authorized')) {
      if (this.$route.params['group'] && this.$route.params['feed']) {
        this.selectedGroupName = this.$route.params['group'];
        this.selectedFeedName = this.$route.params['feed'];
        return this.feedNameButtonClicked(this.selectedGroupName, this.selectedFeedName);
      } else {
        return this.getGroups();
      }
    } else {
      this.$router.push('/login');
    }
  },
  beforeUnmount: function () {
    if (this.checkRunningInterval) {
      clearInterval(this.checkRunningInterval);
    }
  },
  beforeDestroy() {
    if (this.checkRunningInterval) {
      clearInterval(this.checkRunningInterval);
    }
  },
};
</script>
