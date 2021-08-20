<template>
  <b-container fluid>
    <b-row>
      <b-col cols="2" lg="1" class="m-0 p-0">
        <b-card header="그룹 목록">
          <b-list-group vertical>
            <b-list-group-item
              class="p-1 text-truncate text-left"
              v-for="group in groups" :key="group"
              v-on:click="getFeeds(group)">
              {{ group }}
            </b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="2" lg="2" class="m-0 p-0">
        <b-card header="피드 목록">
          <b-list-group vertical>
            <b-list-group-item
              v-for="feed in feeds"
              :key="feed.name"
              v-on:click="getFeedInfo(group, feed.name)"
              class="p-1 text-truncate text-left">
              {{ feed.title }}
            </b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="8" lg="9" class="m-0 p-0">
        <b-card header="설정" header-tag="header">
          <JsonEditor
            class="p-1"
            :options="{
              confirmText: 'confirm',
              cancelText: 'cancel',
            }"
            :objData="jsonData"
            v-model="jsonData"
            v-on:change="onEditorChange"
            v-if="showEditor">
          </JsonEditor>
        </b-card>

        <b-card class="aling-left text-left" v-if="showJsonText">
          <pre class="text-left m-0 p-2">{{ beautifiedJson }}</pre>
        </b-card>

        <b-row>
          <b-col cols="12">
            <b-alert v-model="showAlert" class="mb-0" variant="danger" dismissible>{{ alertMessage }}</b-alert>
          </b-col>
        </b-row>

        <b-card class="aling-left text-left" v-if="showActions">
          <b-row class="align-left pt-2" v-if="showActions">
            <b-col cols="12" class="mb-2">
              <b-input-group prepend="새 피드" class="col-7">
                <b-form-input v-model="newFeedName">
                  {{ newFeedName }}
                </b-form-input>
                <b-input-group-append>
                  <b-button v-on:click="save" :disabled="!saveButtonEnabled">
                    저장
                    <b-spinner small label="saving..." v-if="showSaveSpinner"></b-spinner>
                  </b-button>
                </b-input-group-append>

                <b-button class="ml-1" v-on:click="run" :disabled="!runButtonEnabled">
                  실행
                  <b-spinner small label="running..." v-if="showRunSpinner"></b-spinner>
                </b-button>
                <b-button class="ml-1" v-on:click="registerToFeeder" :disabled="!registerButtonEnabled">
                  Feeder 등록
                </b-button>
              </b-input-group>
            </b-col>

            <b-col cols="12" class="mb-2">
              <b-col cols="6" class="mb-2">
                <b-button v-on:click="removeList">리스트 삭제</b-button>
                <b-button v-on:click="removeHtml">HTML 삭제</b-button>
                <b-button v-on:click="removeFeed">피드 삭제</b-button>
                <b-button v-on:click="enable" v-if="showEditor">피드 {{ feedStatus ? "비활성화" : "활성화" }}</b-button>
              </b-col>

              <b-input-group prepend="별명" class="col-5 mt-1">
                <b-form-input id="alias" v-model="alias">{{ alias }}</b-form-input>
                <b-input-group-append>
                  <b-button v-on:click="renameAlias">변경</b-button>
                </b-input-group-append>
              </b-input-group>
            </b-col>
          </b-row>
        </b-card>
      </b-col>
    </b-row>

    <b-row>
      <b-col cols="6" class="mx-auto text-center mt-5">
        Feed Manager by terzeron@gmail.com
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
#editor {
  text-align: left;
}

.card-header {
  padding: 3px 5px;
  text-align: left;
}

.card-body {
  padding: 0;
  text-align: left;
}

.list-group {
  border-top: 0;
  border-left: 0;
  border-right: 0;
}

input.val-input {
  border: 1px gray dotted !important;
  width: 400px !important;
}

input.key-input {
  border: 1px gray dotted !important;
  width: 200px !important;
}

div.card-body > div.block_content {
  margin-left: 0;
  margin-right: 5px;
}

div.card-body > div.block_content > div > div.block {
  margin-left: initial;
}

#status {
  border: 0;
}
</style>

<script>

import axios from 'axios';
import beautify from 'json-beautify';

export default {
  name: 'FeedManagement',
  props: ['feed', 'group'],
  data() {
    return {
      alertMessage: '',
      showAlert: false,
      showEditor: false,
      showJsonText: false,
      showActions: true,
      showSaveSpinner: false,
      showRunSpinner: false,
      saveButtonEnabled: true,
      runButtonEnabled: true,
      registerButtonEnabled: true,
      groups: [],
      feeds: [],
      jsonData: {},
      selectedGroupName: '',
      selectedFeedName: '',
      alias: '',
      feedStatus: false,
    };
  },
  computed: {
    beautifiedJson: function () {
      return String(beautify(this.jsonData, null, 2));
    },
    newFeedName: function () {
      if (this.jsonData && this.jsonData.rss && this.jsonData.rss.link) {
        const url = new URL(this.jsonData.rss.link).pathname;
        return url.substring(1).split('.')[0];
      }
      return '';
    },
  },
  components: {},
  methods: {
    onEditorChange() {
      this.runButtonEnabled = true;
    },
    getApiUrlPath() {
      let pathPrefix = 'https://api.terzeron.com/fm';
      if (process.env.NODE_ENV === 'development') {
        pathPrefix = 'http://localhost:5000/fm';
      }
      return pathPrefix;
    },
    getGroups() {
      console.log(`getGroups()`);
      const path = this.getApiUrlPath() + '/groups';
      axios
        .get(path)
        .then((res) => {
          this.alertMessage = res.data.message;
          this.showAlert = res.data.status === 'failure';
          this.groups = res.data.groups;
        })
        .catch((error) => {
          console.error(error);
        });
    },
    getFeeds(groupName) {
      console.log(`getFeeds(${groupName})`);
      this.selectedGroupName = groupName;
      const path =
        this.getApiUrlPath() + `/groups/${this.selectedGroupName}/feeds`;
      axios
        .get(path)
        .then((res) => {
          this.alertMessage = res.data.message;
          this.showAlert = res.data.status === 'failure';
          this.feeds = res.data.feeds;
        })
        .catch((error) => {
          console.error(error);
        });
    },
    getFeedInfo(groupName, feedName) {
      this.selectedFeedName = feedName;
      if (feedName[0] === '_') {
        this.feedStatus = false;
      } else {
        this.feedStatus = true;
      }
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}`;
      axios
        .get(path)
        .then((res) => {
          this.alertMessage = res.data.message;
          this.showAlert = res.data.status === 'failure';
          this.jsonData = res.data.configuration;
          this.showEditor = true;
          this.showJsonText = true;
          this.showActions = true;
        })
        .catch((error) => {
          console.error(error);
        });
    },
    save: function () {
      console.log(`save()`);
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}`;
      this.$bvModal
        .msgBoxConfirm('정말로 실행하시겠습니까?')
        .then(() => {
          this.showSaveSpinner = true;
          const postData = {configuration: this.jsonData};
          axios
            .post(path, postData)
            .then((res) => {
              this.alertMessage = res.data.message;
              if (res.data.status === 'failure') {
                this.showAlert = true;
              } else {
                this.selectedFeedName = this.newFeedName;
              }
              this.showSaveSpinner = false;
              this.saveButtonEnabled = false;
              this.runButtonEnabled = true;
            })
            .catch((error) => {
              console.error(error);
            });
        })
        .catch((error) => {
          console.error(error);
        });
    },
    run: function () {
      console.log(`run()`);
      this.runButtonEnabled = false;
      this.showRunSpinner = true;
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.newFeedName}/run`;
      axios
        .post(path)
        .then((res) => {
          this.alertMessage = res.data.message;
          this.showAlert = res.data.status === 'failure';
          this.showRunSpinner = false;
          this.runButtonEnabled = true;
          this.registerButtonEnabled = true;
        })
        .catch((error) => {
          console.error(error);
        });
    },
    registerToFeeder: function () {
      console.log(`registerToFeeder()`);
      this.registerButtonEnabled = false;
      const feeder_link =
        'https://www.inoreader.com/feed/' +
        encodeURIComponent(`https://terzeron.com/${this.newFeedName}.xml`);
      window.open(feeder_link);
    },
    enable: function () {
      console.log(`enable()`);
      let action = 'enable';
      if (this.feedStatus) {
        action = 'disable';
      }
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/${action}`;
      this.$bvModal
        .msgBoxConfirm('정말로 실행하시겠습니까?')
        .then(() => {
          axios
            .put(path)
            .then((res) => {
              this.alertMessage = res.data.message;
              this.showAlert = res.data.status === 'failure';
              this.feedStatus = !this.feedStatus;
              this.getFeeds(this.selectedGroupName);
            })
            .catch((error) => {
              console.error(error);
            });
        })
        .catch((error) => {
          console.error(error);
        });
    },
    removeList: function () {
      console.log(`removeList()`);
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/list`;
      this.$bvModal
        .msgBoxConfirm('정말로 실행하시겠습니까?')
        .then(() => {
          axios
            .delete(path)
            .then((res) => {
              this.alertMessage = res.data.message;
              this.showAlert = res.data.status === 'failure';
              console.log(res);
            })
            .catch((error) => {
              console.error(error);
            });
        })
        .catch((error) => {
          console.error(error);
        });
    },
    removeHtml: function () {
      console.log(`removeHtml()`);
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/html`;
      this.$bvModal
        .msgBoxConfirm('정말로 실행하시겠습니까?')
        .then(() => {
          axios
            .delete(path)
            .then((res) => {
              this.alertMessage = res.data.message;
              this.showAlert = res.data.status === 'failure';
              console.log(res);
            })
            .catch((error) => {
              console.error(error);
            });
        })
        .catch((error) => {
          console.error(error);
        });
    },
    removeFeed: function () {
      console.log(`removeFeed()`);
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}`;
      this.$bvModal
        .msgBoxConfirm('정말로 실행하시겠습니까?')
        .then(() => {
          axios
            .delete(path)
            .then((res) => {
              this.alertMessage = res.data.message;
              this.showAlert = res.data.status === 'failure';
              this.showEditor = false;
              this.showJsonText = false;
              this.getFeeds(this.selectedGroupName);
              this.getGroups();
            })
            .catch((error) => {
              console.error(error);
            });
        })
        .catch((error) => {
          console.error(error);
        });
    },
    renameAlias: function () {
      console.log(`renameAlias(${this.alias})`);
      const path =
        this.getApiUrlPath() +
        `/groups/${this.selectedGroupName}/feeds/${this.selectedFeedName}/rename/${this.alias}`;
      console.log(path);
      axios
        .put(path)
        .then((res) => {
          this.alertMessage = res.data.message;
          this.showAlert = res.data.status === 'failure';
        })
        .catch((error) => {
          console.error(error);
        });
    }
  },
  created() {
    return this.getGroups();
  },
};
</script>
