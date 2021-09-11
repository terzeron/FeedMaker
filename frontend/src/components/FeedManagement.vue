<template>
  <b-container fluid>
    <!-- 그룹과 피드 목록 제어 버튼 -->
    <b-row>
      <b-col cols="12" class="m-0">
        <my-button
            ref="groupListButton"
            label="그룹 목록"
            variant="success"
            @click="groupListButtonClicked"/>
        <my-button
            ref="feedListButton"
            :label="selectedGroupName + ' 그룹의 피드 목록'"
            @click="feedListButtonClicked"
            v-if="showFeedListButton"/>

        <b-input-group
            class="float-right p-1"
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
      <b-col id="search_result" cols="12" class="m-0" v-if="showSearchResult">
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
      <b-col id="group_list" cols="12" class="m-0" v-if="showGroupList">
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
      <b-col id="feed_list" ols="12" class="m-0" v-if="showFeedList">
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

    <!-- 설정 편집기 및 액션 영역 -->
    <b-row>
      <!-- 설정 편집기 영역 -->
      <b-col id="configuration" cols="12" lg="8" class="m-0">
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

      <!-- 액션 영역 -->
      <b-col id="actions" cols="12" lg="4" class="m-0">
        <b-col cols="12" class="m-0" :class="{'bg-secondary': !feedStatus}" v-if="showNewFeedNameInput">
          <my-button :label="title" variant="transparent"/>
          <my-button :label="selectedGroupName + '/' + selectedFeedName" variant="transparent" class="float-right"/>
        </b-col>

        <b-alert
            class="mb-0"
            variant="danger"
            dismissible
            v-if="showAlert">
          {{ alertMessage }}
        </b-alert>

        <b-col cols="12" class="m-0">
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

        <b-col cols="12" class="m-0">
          <my-button
              ref="runButton"
              label="실행"
              @click="run"
              :initial-icon="['fas', 'play']"
              :show-initial-icon="true"
              v-if="showRunButton"/>
          <my-button
              ref="registerButton"
              label="등록"
              @click="registerToFeeder"
              :initial-icon="['fas', 'rss']"
              :show-initial-icon="true"
              v-if="showRegisterButton"/>
          <my-button
              ref="removeListButton"
              label="리스트 삭제"
              @click="removeList"
              :initial-icon="['fas', 'eraser']"
              :show-initial-icon="true"
              v-if="showRemoveListButton"/>
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
              v-if="showRemoveFeedButton"/>
        </b-col>

        <b-col cols="12" class="m-0">
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

        <b-col cols="12" class="m-0">
          <b-input-group prepend="별명" class="m-0" v-if="showAliasInput">
            <b-form-input class="m-0" v-model="alias">
              {{ alias }}
            </b-form-input>
            <b-input-group-append>
              <my-button
                  ref="renameAliasButton"
                  label="변경"
                  @click="renameAlias"
                  :initial-icon="['fas', 'pen']"
                  :show-initial-icon="true"/>
            </b-input-group-append>
            <b-input-group-append>
              <my-button
                  ref="removeAliasButton"
                  label="삭제"
                  @click="removeAlias"
                  :initial-icon="['fas', 'eraser']"
                  :show-initial-icon="true"/>
            </b-input-group-append>
          </b-input-group>
        </b-col>
      </b-col>
    </b-row>

    <b-row>
      <b-col cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by terzeron@gmail.com
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
#group_list, #feed_list, #configuration, #actions {
  border: 1px lightgray solid;
  border-collapse: collapse;
  padding: 2px !important;
}

div.col-12 {
  padding: 2px !important;
}

div.row > div > button, div.row > div > div > button, div.input-group {
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
import vueJsonEditor from 'vue-json-editor'
import axios from 'axios';
import MyButton from './MyButton';
import {library} from '@fortawesome/fontawesome-svg-core';
import {faTrashAlt, faSave} from '@fortawesome/free-regular-svg-icons';
import {faSearch, faRss, faPlay, faToggleOn, faToggleOff, faEraser, faPen} from '@fortawesome/free-solid-svg-icons';

library.add(faTrashAlt, faSave, faSearch, faRss, faPlay, faToggleOn, faToggleOff, faEraser, faPen);

export default {
  name: 'FeedManagement',
  components: {
    vueJsonEditor,
    MyButton
  },
  props: ['feed', 'group'],
  data() {
    return {
      alertMessage: '',

      showGroupList: true,
      showFeedList: false,
      showFeedListButton: false,
      showSearchResult: false,

      showEditor: false,

      showAlert: false,
      showRunButton: false,
      showRegisterButton: false,
      showRemoveListButton: false,
      showRemoveFeedButton: false,
      showRemoveGroupButton: false,
      showToggleFeedButton: false,
      showToggleGroupButton: false,
      showRemoveHtmlButton: false,
      showNewFeedNameInput: false,
      showAliasInput: false,
      showSiteConfig: false,

      activeGroupIndex: undefined,
      activeFeedIndex: undefined,

      groups: [],
      feeds: [],
      jsonData: {},
      selectedGroupName: '',
      selectedFeedName: '',
      newFeedName: '',
      alias: '',
      searchKeyword: ''
    };
  },
  computed: {
    feedStatus() {
      return this.selectedFeedName[0] !== '_';
    },
    groupStatus() {
      return this.selectedGroupName[0] !== '_';
    },
    feedStatusLabel() {
      return '피드 ' + (this.feedStatus ? '비활성화' : '활성화');
    },
    feedStatusIcon() {
      return 'toggle-' + (this.feedStatus ? 'off' : 'on');
    },
    groupStatusLabel() {
      return '그룹 ' + (this.groupStatus ? '비활성화' : '활성화');
    },
    groupStatusIcon() {
      return 'toggle-' + (this.feedStatus ? 'off' : 'on');
    },
    title() {
      return this.jsonData.rss.title;
    }
  },
  watch: {
    newFeedName: function (val) {
      this.jsonData.rss.link = 'https://terzeron.com/' + val + '.xml';
      this.alias = val;
    },
    jsonData: function () {
      this.determineNewFeedNameFromJsonRssLink();
      this.determineDescriptionFromTitle();
    }
  },
  methods: {
    getApiUrlPath() {
      let pathPrefix = 'https://api.terzeron.com/fm';
      if (process.env.NODE_ENV === 'development') {
        pathPrefix = 'http://localhost:5000';
      }
      return pathPrefix;
    },
    determineNewFeedNameFromJsonRssLink() {
      if ('rss' in this.jsonData && 'link' in this.jsonData.rss) {
        const re = /https:\/\/terzeron.com\/_?(.+)\.xml/;
        const matched = this.jsonData.rss.link.match(re);
        if (matched) {
          this.newFeedName = matched[1];
        }
      }
    },
    determineDescriptionFromTitle() {
      if ('rss' in this.jsonData && 'title' in this.jsonData.rss && 'description' in this.jsonData.rss) {
        this.jsonData.rss.description = this.jsonData.rss.title;
      }
    },
    setActiveGroup(index) {
      this.activeGroupIndex = index;
    },
    setActiveFeed(index) {
      this.activeFeedIndex = index;
    },
    alert(message) {
      this.alertMessage = message;
      this.showAlert = true;
    },
    clearAlert() {
      this.alertMessage = '';
      this.showAlert = false;
    },
    getCleanFeedName(feedName) {
      if (feedName[0] === '_') {
        return feedName.substring(1);
      }
      return feedName;
    },
    determineStatus(name) {
      return name[0] !== '_';
    },

    startButton(ref) {
      this.$refs[ref].doShowInitialIcon = false;
      this.$refs[ref].doShowSpinner = true;
    },
    endButton(ref) {
      this.$refs[ref].doShowInitialIcon = true;
      this.$refs[ref].doShowSpinner = false;
    },
    resetButton(ref) {
      this.$refs[ref].doShowInitialIcon = true;
      this.$refs[ref].doShowSpinner = false;
    },
    showAllRelatedToFeed() {
      this.showEditor = true;
      this.showNewFeedNameInput = true;
      this.showRunButton = true;
      this.showRegisterButton = true;
      this.showRemoveListButton = true;
      this.showRemoveHtmlButton = true;
      this.showToggleFeedButton = true;
      this.showRemoveFeedButton = true;
      this.showAliasInput = true;
    },
    hideAllRelatedToFeed() {
      this.showEditor = false;
      this.showNewFeedNameInput = false;
      this.showRunButton = false;
      this.showRegisterButton = false;
      this.showRemoveListButton = false;
      this.showRemoveHtmlButton = false;
      this.showToggleFeedButton = false;
      this.showRemoveFeedButton = false;
      this.showAliasInput = false;
      this.clearAlert();
    },
    showAllRelatedToGroup() {
      if (this.selectedGroupName) {
        this.showToggleGroupButton = true;
        this.showRemoveGroupButton = true;
      }
    },
    hideAllRelatedToGroup() {
      this.showToggleGroupButton = false;
      this.showRemoveGroupButton = false;
    },
    showAllRelatedToSiteConfig() {
      this.showEditor = true;
      this.showSiteConfig = true;
    },
    hideAllRelatedToSiteConfig() {
      this.showEditor = false;
      this.showSiteConfig = false;
    },

    search() {
      console.log(`search()`);
      this.showSearchResult = true;
      this.showGroupList = false;
      this.showFeedList = false;
      this.showFeedListButton = false;
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
    groupListButtonClicked() {
      console.log(`groupListButtonClicked()`);
      this.showGroupList = true;
      this.showFeedList = false;
      this.showFeedListButton = false;
      this.showSearchResult = false;
      this.hideAllRelatedToGroup();
      this.hideAllRelatedToSiteConfig();

      this.getGroups();
    },
    getGroups() {
      console.log(`getGroups()`);
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
    feedListButtonClicked() {
      console.log(`feedListButtonClicked()`);
      this.showGroupList = false;
      this.showFeedList = true;
      this.hideAllRelatedToSiteConfig();

      this.getFeedListByGroup(this.selectedGroupName);
    },
    groupNameButtonClicked(groupName, index) {
      console.log(`groupNameButtonClicked(${groupName}, ${index})`);
      if (index) {
        this.setActiveGroup(index);
      }
      this.selectedGroupName = groupName;

      // show and hide
      this.showGroupList = false;
      this.showFeedList = true;
      this.showFeedListButton = true;
      this.hideAllRelatedToSiteConfig();

      this.getFeedListByGroup(groupName);
    },
    getFeedListByGroup(groupName) {
      console.log(`getFeedListByGroup(${groupName})`);
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
    searchResultFeedNameButtonClicked(groupName, feedName, index) {
      console.log(`searchResultFeedNameButtonClicked(${groupName}, ${feedName}, ${index})`);
      if (index) {
        this.setActiveFeed(index);
      }
      this.selectedGroupName = groupName;
      this.selectedFeedName = feedName;

      // show and hide
      this.showFeedList = false;
      this.showFeedListButton = false;

      this.getFeedInfo(groupName, feedName);
    },
    feedNameButtonClicked(groupName, feedName, index) {
      console.log(`feedNameButtonClicked(${groupName}, ${feedName}, ${index})`);
      if (index) {
        this.setActiveFeed(index);
      }
      this.selectedFeedName = feedName;

      // show and hide
      this.showFeedList = false;
      this.showFeedListButton = true;

      if (feedName === 'site_config.json') {
        this.getSiteConfig();
      } else {
        this.getFeedInfo(groupName, feedName);
      }
    },
    getFeedInfo(groupName, feedName) {
      console.log(`getFeedInfo(${groupName}, ${feedName})`);
      const url = this.getApiUrlPath() + `/groups/${groupName}/feeds/${feedName}`;
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.jsonData = res.data.configuration;
              this.determineNewFeedNameFromJsonRssLink();
              if (Object.keys(this.jsonData).length >= 3) {
                this.showAllRelatedToFeed();
              } else {
                this.hideAllRelatedToFeed();
              }
              this.hideAllRelatedToGroup();
              this.getAlias();
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    getSiteConfig() {
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
    saveSiteConfig() {
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
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            this.startButton('saveButton');
            if (value) {
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
                    this.endButton('saveButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('saveButton');
                  });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    run: function () {
      console.log(`run()`);
      this.startButton('runButton');
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}/run`;
      const postData = {alias: this.alias};
      axios
          .post(url, postData)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            }
            this.endButton('runButton');
          })
          .catch((error) => {
            console.error(error);
            this.resetButton('runButton');
          });
    },
    registerToFeeder: function () {
      console.log(`registerToFeeder()`);
      const feeder_link = 'https://www.inoreader.com/feed/' + encodeURIComponent(`https://terzeron.com/${this.newFeedName}.xml`);
      window.open(feeder_link);
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
                        this.getFeedListByGroup(this.selectedGroupName);
                        this.showFeedList = true;
                        this.hideAllRelatedToFeed();
                      } else {
                        this.selectedGroupName = res.data['new_name'];
                        this.getGroups();
                        this.showGroupList = true;
                        this.showFeedList = false
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
    removeList: function () {
      console.log(`removeList()`);
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.startButton('removeListButton');
              const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/list`;
              axios
                  .delete(url)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    }
                    this.endButton('removeListButton');
                  })
                  .catch((error) => {
                    console.error(error);
                    this.resetButton('removeListButton');
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
                      this.getFeedListByGroup(this.selectedGroupName);
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
    getAlias: function () {
      console.log(`getAlias()`);
      let feedName = this.getCleanFeedName(this.selectedFeedName);
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${feedName}/alias`;
      axios
          .get(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
              this.alias = '';
            } else {
              this.alias = res.data.alias;
              this.showAliasInput = true;
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeAlias: function () {
      console.log(`removeAlias()`);
      let feedName = this.getCleanFeedName(this.selectedFeedName);
      this.startButton('removeAliasButton');
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${feedName}/alias`;

      axios
          .delete(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            }
            this.endButton('removeAliasButton');
          })
          .catch((error) => {
            console.error(error);
            this.resetButton('removeAliasButton');
          });
    },
    renameAlias: function () {
      console.log(`renameAlias(${this.alias})`);
      let alias = this.getCleanFeedName(this.alias);
      this.startButton('renameAliasButton');
      const url = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/rename/${alias}`;
      axios
          .put(url)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            }
            this.endButton('renameAliasButton');
          })
          .catch((error) => {
            console.error(error);
            this.resetButton('renameAliasButton');
          });
    },
  },
  created() {
    if (this.$route.params['group'] && this.$route.params['feed']) {
      this.selectedGroupName = this.$route.params['group'];
      this.selectedFeedName = this.$route.params['feed'];
      return this.feedNameButtonClicked(this.selectedGroupName, this.selectedFeedName);
    } else {
      return this.getGroups();
    }
  },
};
</script>
