<template>
  <b-container fluid>
    <b-row>
      <b-col cols="12" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          피드 상태
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0 text-break"
              striped
              hover
              small
              :fields="statusInfoFields"
              :items="statusInfolist">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
            </template>
            <template #cell(action)="data">
              <font-awesome-icon
                  :icon="['far', 'trash-alt']"
                  @click="statusInfoDeleteClicked(data)"
                  v-if="showStatusInfoDeleteButton(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="8" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          점진적 피딩 진행률
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0"
              striped
              hover
              small
              :fields="progressInfoFields"
              :items="progressInfolist"
              :sort-by.sync="progressInfoSortBy"
              :sort-desc.sync="progressInfoSortDesc">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
            </template>
            <template #cell(progress_ratio)="data">
              {{ data.value }}%
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          피드별 수집대상 URL 갯수
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0"
              striped
              hover
              small
              :fields="listUrlInfoFields"
              :items="listUrlInfolist"
              :sort-by.sync="listUrlInfoSortBy"
              :sort-desc.sync="listUrlInfoSortDesc">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          파일 크기가 너무 작은 HTML 파일
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0 text-break"
              striped
              hover
              small
              :fields="htmlFileSizeFields"
              :items="htmlFileSizelist"
              :sort-by.sync="htmlFileSizeSortBy"
              :sort-desc.sync="htmlFileSizeSortDesc">
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="htmlFileSizeDeleteClicked(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          이미지 태그가 없는 HTML 파일
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0 text-break"
              striped
              hover
              small
              :fields="htmlFileWithoutImageTagFields"
              :items="htmlFileWithoutImageTaglist"
              :sort-by.sync="htmlFileWithoutImageTagSortBy"
              :sort-desc.sync="htmlFileWithoutImageTagSortDesc">
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="imageWithoutImageTagDeleteClicked(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          이미지 태그가 많은 HTML 파일
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0 text-break"
              striped
              hover
              small
              :fields="htmlFileWithManyImageTagFields"
              :items="htmlFileWithManyImageTaglist"
              :sort-by.sync="htmlFileWithManyImageTagSortBy"
              :sort-desc.sync="htmlFileWithManyImageTagSortDesc">
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="imageWithManyImageTagDeleteClicked(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          이미지가 누락된 HTML 파일
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0 text-break"
              striped
              hover
              small
              :fields="htmlFileWithImageNotFoundFields"
              :items="htmlFileWithImageNotFoundlist"
              :sort-by.sync="htmlFileWithImageNotFoundSortBy"
              :sort-desc.sync="htmlFileWithImageNotFoundSortDesc">
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="imageNotFoundDeleteClicked(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          Element별 사용 횟수
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0"
              striped
              hover
              small
              :fields="elementInfoFields"
              :items="elementInfolist"
              :sort-by.sync="elementInfoSortBy"
              :sort-desc.sync="elementInfoSortDesc">
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          결과(public feed) 파일의 크기
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0"
              striped
              hover
              small
              :fields="publicFeedInfoFields"
              :items="publicFeedInfolist"
              :sort-by.sync="publicFeedInfoSortBy"
              :sort-desc.sync="publicFeedInfoSortDesc">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
            </template>
            <template #cell(size)="data">
              <span v-html="data.value" :class="{'text-danger': data.item.sizeIsDanger, 'text-warning': data.item.sizeIsWarning}"></span>
            </template>
            <template #cell(num_items)="data">
              <span v-html="data.value" :class="{'text-danger': data.item.numItemsIsDanger, 'text-warning': data.item.numItemsIsWarning}"></span>
            </template>
            <template #cell(upload_date)="data">
              <span v-html="data.value" :class="{'text-danger': data.item.uploadDateIsDanger, 'text-warning': data.item.uploadDateIsWarning}"></span>
            </template>
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="publicFeedInfoDeleteClicked(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>
    </b-row>

    <b-row>
      <b-col cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
      </b-col>
    </b-row>
  </b-container>
</template>

<style>
</style>

<script>
import axios from 'axios';
import _ from 'lodash';
import moment from 'moment';

import {library} from '@fortawesome/fontawesome-svg-core';
import {faTrashAlt} from '@fortawesome/free-regular-svg-icons';
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome';

library.add(faTrashAlt);

export default {
  name: 'Problems',
  components: {
    FontAwesomeIcon
  },
  computed: {
    adminEmail: function () {
      return process.env.VUE_APP_FACEBOOK_ADMIN_EMAIL;
    },
  },
  data: function () {
    return {
      problems: {},

      statusInfoFields: [
        {key: 'feed_title', label: '제목', sortable: true},
        {key: 'feed_name', label: '이름', sortable: true},
        {key: 'feedmaker', label: '생성', sortable: true},
        {key: 'public_html', label: '등록', sortable: true},
        {key: 'http_request', label: '요청', sortable: true},
        {key: 'update_date', label: '생성', sortable: true},
        {key: 'upload_date', label: '등록', sortable: true},
        {key: 'access_date', label: '요청', sortable: true},
        {key: 'view_date', label: '조회', sortable: true},
        {key: 'action', label: '작업', sortable: false},
      ],
      statusInfolist: [],

      progressInfoFields: [
        {key: 'feed_title', label: '제목', sortable: true},
        {key: 'current_index', label: '현재', sortable: true},
        {key: 'total_item_count', label: '갯수', sortable: true},
        {key: 'unit_size_per_day', label: '단위', sortable: true},
        {key: 'progress_ratio', label: '진행', sortable: true},
        {key: 'due_date', label: '예정', sortable: true},
      ],
      progressInfoSortBy: 'progress_ratio',
      progressInfoSortDesc: true,
      progressInfolist: [],

      publicFeedInfoFields: [
        {key: 'feed_title', label: '제목', sortable: true},
        {key: 'size', label: '크기', sortable: true},
        {key: 'num_items', label: '갯수', sortable: true},
        {key: 'upload_date', label: '등록', sortable: true},
        {key: 'action', label: '작업', sortable: false},
      ],
      publicFeedInfoSortBy: 'num_items',
      publicFeedInfoSortDesc: true,
      publicFeedInfolist: [],

      htmlFileWithImageNotFoundFields: [
        {key: 'file_name', label: '파일', sortable: true},
        {key: 'count', label: '갯수', sortable: true},
        {key: 'action', label: '작업', sortable: false},
      ],
      htmlFileWithImageNotFoundSortBy: 'count',
      htmlFileWithImageNotFoundSortDesc: true,
      htmlFileWithImageNotFoundlist: [],

      htmlFileWithoutImageTagFields: [
        {key: 'file_name', label: '파일', sortable: true},
        {key: 'count', label: '갯수', sortable: true},
        {key: 'action', label: '작업', sortable: false},
      ],
      htmlFileWithoutImageTagSortBy: 'count',
      htmlFileWithoutImageTagSortDesc: true,
      htmlFileWithoutImageTaglist: [],

      htmlFileWithManyImageTagFields: [
        {key: 'file_name', label: '파일', sortable: true},
        {key: 'count', label: '갯수', sortable: true},
        {key: 'action', label: '작업', sortable: false},
      ],
      htmlFileWithManyImageTagSortBy: 'count',
      htmlFileWithManyImageTagSortDesc: true,
      htmlFileWithManyImageTaglist: [],

      htmlFileSizeFields: [
        {key: 'file_name', label: '파일', sortable: true},
        {key: 'size', label: '크기', sortable: true},
        {key: 'action', label: '작업', sortable: false},
      ],
      htmlFileSizeSortBy: 'size',
      htmlFileSizeSortDesc: false,
      htmlFileSizelist: [],

      listUrlInfoFields: [
        {key: 'feed_title', label: '제목', sortable: true},
        {key: 'count', label: '갯수', sortable: true},
      ],
      listUrlInfoSortBy: 'count',
      listUrlInfoSortDesc: true,
      listUrlInfolist: [],

      elementInfoFields: [
        {key: 'element_name', label: '요소', sortable: true},
        {key: 'count', label: '갯수', sortable: true},
      ],
      elementInfoSortBy: 'count',
      elementInfoSortDesc: true,
      elementInfolist: [],
    }
  },
  methods: {
    showStatusInfoDeleteButton: function (data) {
      return data.item['feed_title'] === '' && data.item['public_html'] === 'O';
    },
    getApiUrlPath: function () {
      return process.env.VUE_APP_API_URL;
    },
    removePublicFeed(feedName) {
      const path = this.getApiUrlPath() + `/public_feeds/${feedName}`;
      axios
          .delete(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.$bvModal
                  .msgBoxOk('피드 삭제 중에 오류가 발생하였습니다. ' + res.data.message);
            }
          })
          .catch((error) => {
            this.$bvModal
                .msgBoxOk('피드 삭제 요청 중에 오류가 발생하였습니다. ' + error);
          })
    },
    statusInfoDeleteClicked(data) {
      console.log(`statusInfoDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              const feedName = data.item['feed_name']

              this.removePublicFeed(feedName);
              this.statusInfolist = this.statusInfolist.filter(item => item !== data.item);
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
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              const feedName = data.item['feed_name']
              this.removePublicFeed(feedName);
              this.publicFeedInfolist = this.publicFeedInfolist.filter(item => item !== data.item);
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeHtmlFile(filePath) {
      const parts = filePath.split('/');
      const groupName = parts[0];
      const feedName = parts[1];
      const htmlFileName = parts[3];
      const path = this.getApiUrlPath() + `/groups/${groupName}/feeds/${feedName}/htmls/${htmlFileName}`;
      axios
          .delete(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.$bvModal
                  .msgBoxOk('실행 중에 오류가 발생하였습니다. ' + res.data.message);
            } else {
              //
            }
          })
          .catch((error) => {
            this.$bvModal
                .msgBoxOk('실행 요청 중에 오류가 발생하였습니다. ' + error);
          })
      return true;
    },
    imageWithoutImageTagDeleteClicked(data) {
      console.log(`imageWithoutImageTagDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.removeHtmlFile(data.item['file_path']);
              this.htmlFileWithoutImageTaglist = this.htmlFileWithoutImageTaglist.filter(item => item !== data.item);
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
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.removeHtmlFile(data.item['file_path']);
              this.htmlFileWithManyImageTaglist = this.htmlFileWithManyImageTaglist.filter(item => item !== data.item);
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
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.removeHtmlFile(data.item['file_path']);
              this.htmlFileWithImageNotFoundlist = this.htmlFileWithImageNotFoundlist.filter(item => item !== data.item);
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
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              this.removeHtmlFile(data.item['file_path']);
              this.htmlFileSizelist = this.htmlFileSizelist.filter(item => item !== data.item);
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    getManagementLink(feedTitle, groupName, feedName) {
      return feedTitle ? `<a href="/management/${groupName}/${feedName}">${feedTitle}</a>` : '';
    },
    getShortDate(date) {
      let d = moment(date);
      if (!d.isValid()) {
        return "";
      }
      return d.format('YY-MM-DD');
    },
    getProblems() {
      // 상태 정보
      const pathStatusInfo = this.getApiUrlPath() + '/problems/status_info';
      axios.get(pathStatusInfo)
          .then((resStatusInfo) => {
            if (resStatusInfo.data.status === 'failure') {
              console.log(resStatusInfo.data.message);
            } else {
              // transformation
              this.statusInfolist = _.map(resStatusInfo.data['result'], o => {
                o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']);
                o['http_request'] = o['http_request'] ? 'O' : 'X';
                o['public_html'] = o['public_html'] ? 'O' : 'X';
                o['feedmaker'] = o['feedmaker'] ? 'O' : 'X';
                o['update_date'] = this.getShortDate(o['update_date']);
                o['upload_date'] = this.getShortDate(o['upload_date']);
                o['access_date'] = this.getShortDate(o['access_date']);
                o['view_date'] = this.getShortDate(o['view_date']);
                o['action'] = '삭제';
                return o;
              });
              console.log(this.statusInfolist);
            }
          })
          .catch((error) => {
            console.error(error);
          });

      // 점진적 피딩 진행률 정보
      const pathProgressInfo = this.getApiUrlPath() + '/problems/progress_info';
      axios.get(pathProgressInfo)
          .then((resProgressInfo) => {
            if (resProgressInfo.data.status === 'failure') {
              console.log(resProgressInfo.data.message);
            } else {
              this.progressInfolist = _.map(resProgressInfo.data['result'], o => {
                o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']);
                o['due_date'] = this.getShortDate(o['due_date']);
                return o;
              });
            }
          })
          .catch((error) => {
            console.error(error);
          });

      // 결과(public feed) 정보
      const pathPublicFeedInfo = this.getApiUrlPath() + '/problems/public_feed_info';
      axios.get(pathPublicFeedInfo)
          .then((resPublicFeedInfo) => {
            if (resPublicFeedInfo.data.status === 'failure') {
              console.log(resPublicFeedInfo.data.message);
            } else {
              // transformation & filtering
              let day2MonthAgo = new Date();
              day2MonthAgo.setTime(day2MonthAgo.getTime() - 2 * 30 * 24 * 60 * 60 * 1000); // 2 months ago
              day2MonthAgo = day2MonthAgo.toISOString().substring(0, 12);
              this.publicFeedInfolist = _.filter(resPublicFeedInfo.data['result'], o => {
                return o['upload_date'] < day2MonthAgo || o['size'] < 4 * 1024 || o['num_items'] < 5 || o['num_items'] > 20;
              }).map(o => {
                o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']) || o['feed_name'];
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
                o['upload_date'] = this.getShortDate(o['upload_date']);
                o['action'] = "삭제";
                if (o['upload_date'] < day2MonthAgo) {
                  o['uploadDateIsWarning'] = true;
                }
                return o;
              });
            }
          })
          .catch((error) => {
            console.error(error);
          })

      // HTML 정보
      const pathHtmlInfo = this.getApiUrlPath() + '/problems/html_info';
      axios.get(pathHtmlInfo)
          .then((resHtmlInfo) => {
            if (resHtmlInfo.data.status === 'failure') {
              console.log(resHtmlInfo.data.message);
            } else {
              this.htmlFileSizelist = _.map(resHtmlInfo.data['result']['html_file_size_map'], o => {
                o['action'] = '삭제';
                return o;
              });
              this.htmlFileWithManyImageTaglist = _.map(resHtmlInfo.data['result']['html_file_with_many_image_tag_map'], o => {
                o['action'] = '삭제';
                return o;
              });
              this.htmlFileWithoutImageTaglist = _.map(resHtmlInfo.data['result']['html_file_without_image_tag_map'], o => {
                o['action'] = '삭제';
                return o;
              });
              this.htmlFileWithImageNotFoundlist = _.map(resHtmlInfo.data['result']['html_file_image_not_found_map'], o => {
                o['action'] = '삭제';
                return o;
              });
            }
          })
          .catch((error) => {
            console.error(error);
          });

      // element 정보
      const pathElementInfo = this.getApiUrlPath() + '/problems/element_info';
      axios.get(pathElementInfo)
          .then((resElementInfo) => {
            if (resElementInfo.data.status === 'failure') {
              console.log(resElementInfo.data.message);
            } else {
              this.elementInfolist = _.map(resElementInfo.data['result'], o => {
                return o;
              })
            }
          })
          .catch((error) => {
            console.error(error);
          });

      // listUrlCount 정보
      const listUrlInfo = this.getApiUrlPath() + '/problems/list_url_info';
      axios.get(listUrlInfo)
          .then((reslistUrlInfo) => {
            if (reslistUrlInfo.data.status === 'failure') {
              console.log(reslistUrlInfo.data.message);
            } else {
              this.listUrlInfolist = _.map(reslistUrlInfo.data['result'], o => {
                o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']);
                return o;
              });
            }
          })
          .catch((error) => {
            console.error(error);
          });
    }
  },
  mounted: function () {
    if (this.$session.get('is_authorized')) {
      this.getProblems();
    } else {
      this.$router.push('/login');
    }
  },
};
</script>
