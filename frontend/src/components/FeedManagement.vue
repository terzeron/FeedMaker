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
            :key="group.name">

        </my-button>
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
            @click="feedNameButtonClicked(feed.name, index)"
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
            :mode="'form'"
            @json-change="onJsonChange"
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
              <my-button ref="saveButton" label="저장" @click="save"/>
            </b-input-group-append>
          </b-input-group>
        </b-col>

        <b-col cols="12" class="m-0">
          <my-button
              ref="runButton"
              label="실행"
              @click="run"
              v-if="showRunButton"/>
          <my-button
              ref="registerButton"
              label="Feeder 등록"
              @click="registerToFeeder"
              v-if="showRegisterButton"/>
          <my-button
              ref="removeListButton"
              label="리스트 삭제"
              @click="removeList"
              v-if="showRemoveListButton"/>
          <my-button
              ref="removeHtmlButton"
              label="HTML 삭제"
              @click="removeHtml"
              v-if="showRemoveHtmlButton"/>
          <my-button
              ref="toggleFeedButton"
              :label="feedStatusLabel"
              @click="toggleStatus('feed')"
              v-if="showToggleFeedButton"/>
          <my-button
              ref="removeFeedButton"
              label="피드 삭제"
              @click="removeFeed"
              v-if="showRemoveFeedButton"/>
        </b-col>

        <b-col cols="12" class="m-0">
          <my-button
              ref="saveSiteConfigButton"
              label="그룹 설정 저장"
              @click="saveSiteConfig"
              v-if="showSiteConfig"/>
          <my-button
              ref="toggleGroupButton"
              :label="groupStatusLabel"
              variant="success"
              @click="toggleStatus('group')"
              v-if="showToggleGroupButton"/>
          <my-button
              ref="removeGroupButton"
              label="그룹 삭제"
              variant="success"
              @click="removeGroup"
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
                  @click="renameAlias"/>
            </b-input-group-append>
            <b-input-group-append>
              <my-button
                  ref="removeAliasButton"
                  label="삭제"
                  @click="removeAlias"/>
            </b-input-group-append>          </b-input-group>
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

div.row {
  padding: 2px !important;
}

div.col-12 {
  padding: 2px !important;
}

div.row > div > button, div.row > div > div > button, div.input-group {
  margin: 2px 3px 3px 2px !important;
}

input.val-input {
  text-overflow: fade;
  border: 1px gray dotted !important;
  width: 400px !important;
}

input.key-input {
  text-overflow: fade;
  border: 1px gray dotted !important;
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

export default {
  name: 'FeedManagement',
  props: ['feed', 'group'],
  data() {
    return {
      alertMessage: '',

      showGroupList: true,
      showFeedList: false,
      showFeedListButton: false,

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
    groupStatusLabel() {
      return '그룹 ' + (this.groupStatus ? '비활성화' : '활성화');
    },
    title() {
      return this.jsonData.rss.title;
    }
  },
  components: {
    vueJsonEditor,
    MyButton
  },
  watch: {
    newFeedName: function (val) {
      console.log(`newFeedName is changed to ${val}`);
      this.jsonData.rss.link = 'https://terzeron.com/' + val + '.xml';
    },
    alias: function (val) {
      console.log(`alias is changed to ${val}`);
    }
  },
  methods: {
    onJsonChange: function (val) {
      console.log(`jsonData is changed to ${val}`);
      console.log(`Object.keys(jsonData)=${Object.keys(this.jsonData)}`);
    },
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
      this.$refs[ref].doShowSpinner = true;
      this.$refs[ref].doShowCheck = false;
    },
    endButton(ref) {
      this.$refs[ref].doShowSpinner = false;
      this.$refs[ref].doShowCheck = true;
    },
    resetButton(ref) {
      this.$refs[ref].doShowSpinner = false;
      this.$refs[ref].doShowCheck = false;
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

    groupListButtonClicked() {
      console.log(`groupListButtonClicked()`);
      this.showGroupList = true;
      this.showFeedList = false;
      this.showFeedListButton = false;
      this.hideAllRelatedToGroup();
      this.hideAllRelatedToSiteConfig();

      this.getGroups();
    },
    getGroups() {
      console.log(`getGroups()`);
      const path = this.getApiUrlPath() + '/groups';
      axios
          .get(path)
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
      const path = this.getApiUrlPath() + `/groups/${groupName}/feeds`;
      axios
          .get(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.feeds = res.data.feeds;
              console.log(`feeds.length=${this.feeds.length}`);
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
    feedNameButtonClicked(feedName, index) {
      console.log(`feedNameButtonClicked(${feedName}, ${index})`);
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
        this.getFeedInfo(feedName);
      }
    },
    getFeedInfo(feedName) {
      console.log(`getFeedInfo(${feedName})`);
      const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}`;
      axios
          .get(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.jsonData = res.data.configuration;
              console.log(`jsonData is set to ...`);
              console.log(this.jsonData);
              console.log(`Object.keys(this.jsonData)=${Object.keys(this.jsonData)}`);
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
      const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/site_config`;
      axios
          .get(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
            } else {
              this.jsonData = res.data.configuration;
              console.log(`jsonData is set to ...`);
              console.log(this.jsonData);
              console.log(`Object.keys(this.jsonData)=${Object.keys(this.jsonData)}`);
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
              const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/site_config`;
              axios
                  .put(path, postData)
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
              const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}`;
              axios
                  .post(path, postData)
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
      const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}/run`;
      axios
          .post(path)
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
      let path = '';
      if (target === 'feed') {
        path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/toggle`;
      } else {
        path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/toggle`;
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
              console.log(path);
              axios
                  .put(path)
                  .then((res) => {
                    if (res.data.status === 'failure') {
                      this.alert(res.data.message);
                    } else {
                      if (target === 'feed') {
                        this.newFeedName = res.data['new_name'];
                        console.log(`newFeedName is set to ${this.newFeedName}`);
                        this.getFeedListByGroup(this.selectedGroupName);
                        this.showFeedList = true;
                        this.hideAllRelatedToFeed();
                      } else {
                        this.selectedGroupName = res.data['new_name'];
                        console.log(`selectedFeedName is set to ${this.selectedFeedName}`);
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
              const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/list`;
              axios
                  .delete(path)
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
              const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/html`;
              axios
                  .delete(path)
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
              const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}`;
              axios
                  .delete(path)
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
              const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}`;
              axios
                  .delete(path)
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
      const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${feedName}/alias`;
      console.log(`getAlias() ${path}`)
      axios
          .get(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.alert(res.data.message);
              this.alias = '';
            } else {
              this.alias = res.data.alias;
              this.showAliasInput = true;
            }
            console.log(`alias is set to ${this.alias}`);
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeAlias: function () {
      console.log(`removeAlias()`);
      let feedName = this.getCleanFeedName(this.selectedFeedName);
      this.startButton('removeAliasButton');
      const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${feedName}/alias`;

      axios
          .delete(path)
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
      const path = this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/rename/${alias}`;
      console.log(`renameAlias() ${path}`)
      axios
          .put(path)
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
    return this.getGroups();
  },
};
</script>
