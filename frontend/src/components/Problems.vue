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
              :fields="status_info_fields"
              :items="status_info_list"
              :sort-by.sync="status_info_sort_by"
              :sort-desc.sync="status_info_sort_desc">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
            </template>
            <template #cell(action)="data">
              <font-awesome-icon
                  :icon="['far', 'trash-alt']"
                  @click="statusInfoDeleteClicked(data)"
                  v-if="data.item['feed_title'] === '' &&
                  (data.item['htaccess'] === 'O' || data.item['public_html'] === 'O')"/>
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
              :fields="progress_info_fields"
              :items="progress_info_list"
              :sort-by.sync="progress_info_sort_by"
              :sort-desc.sync="progress_info_sort_desc">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
            </template>
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
              :fields="public_feed_info_fields"
              :items="public_feed_info_list"
              :sort-by.sync="public_feed_info_sort_by"
              :sort-desc.sync="public_feed_info_sort_desc">
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="publicFeedInfoDeleteClicked(data)"/>
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
              :fields="html_file_size_fields"
              :items="html_file_size_list"
              :sort-by.sync="html_file_size_sort_by"
              :sort-desc.sync="html_file_size_sort_desc">
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
              :fields="html_file_without_image_tag_fields"
              :items="html_file_without_image_tag_list"
              :sort-by.sync="html_file_without_image_tag_sort_by"
              :sort-desc.sync="html_file_without_image_tag_sort_desc">
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
              :fields="html_file_with_many_image_tag_fields"
              :items="html_file_with_many_image_tag_list"
              :sort-by.sync="html_file_with_many_image_tag_sort_by"
              :sort-desc.sync="html_file_with_many_image_tag_sort_desc">
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
              :fields="html_file_with_image_not_found_fields"
              :items="html_file_with_image_not_found_list"
              :sort-by.sync="html_file_with_image_not_found_sort_by"
              :sort-desc.sync="html_file_with_image_not_found_sort_desc">
            <template #cell(action)="data">
              <font-awesome-icon :icon="['far', 'trash-alt']" @click="imageNotFoundDeleteClicked(data)"/>
            </template>
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">
          피드별 list_url element
          갯수
        </b-card-header>
        <b-card-body class="m-0 p-0">
          <b-table
              class="m-0 p-0"
              striped
              hover
              small
              :fields="list_url_info_fields"
              :items="list_url_info_list"
              :sort-by.sync="list_url_info_sort_by"
              :sort-desc.sync="list_url_info_sort_desc">
            <template #cell(feed_title)="data">
              <span v-html="data.value"></span>
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
              :fields="element_info_fields"
              :items="element_info_list"
              :sort-by.sync="element_info_sort_by"
              :sort-desc.sync="element_info_sort_desc">
          </b-table>
        </b-card-body>
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
</style>

<script>
import axios from 'axios';
import _ from 'lodash';

import {library} from '@fortawesome/fontawesome-svg-core'
import {faTrashAlt} from '@fortawesome/free-regular-svg-icons'
import {faTrash} from '@fortawesome/free-solid-svg-icons'
import {FontAwesomeIcon} from '@fortawesome/vue-fontawesome'

library.add(faTrash, faTrashAlt);

export default {
  name: 'Problems',
  components: {
    FontAwesomeIcon
  },
  data() {
    return {
      problems: {},

      status_info_fields: [
        {key: 'feed_title', sortable: true},
        {key: 'feed_alias', sortable: true},
        {key: 'feed_name', sortable: true},
        {key: 'http_request', sortable: true},
        {key: 'htaccess', sortable: true},
        {key: 'public_html', sortable: true},
        {key: 'feedmaker', sortable: true},
        {key: 'access_date', sortable: true},
        {key: 'view_date', sortable: true},
        {key: 'upload_date', sortable: true},
        {key: 'update_date', sortable: true},
        {key: 'action', sortable: false},
      ],
      status_info_sort_by: 'feed_alias',
      status_info_sort_desc: false,
      status_info_list: [],

      progress_info_fields: [
        {key: 'feed_title', sortable: true},
        {key: 'index', sortable: true},
        {key: 'count', sortable: true},
        {key: 'unit_size', sortable: true},
        {key: 'ratio', sortable: true},
        {key: 'due_date', sortable: true},
      ],
      progress_info_sort_by: 'ratio',
      progress_info_sort_desc: true,
      progress_info_list: [],

      public_feed_info_fields: [
        {key: 'feed_title', sortable: true},
        {key: 'size', sortable: true},
        {key: 'action', sortable: false},
      ],
      public_feed_info_sort_by: 'size',
      public_feed_info_sort_desc: false,
      public_feed_info_list: [],

      html_file_with_image_not_found_fields: [
        {key: 'file_name', sortable: true},
        {key: 'count', sortable: true},
        {key: 'action', sortable: false},
      ],
      html_file_with_image_not_found_sort_by: 'count',
      html_file_with_image_not_found_sort_desc: true,
      html_file_with_image_not_found_list: [],

      html_file_without_image_tag_fields: [
        {key: 'file_name', sortable: true},
        {key: 'count', sortable: true},
        {key: 'action', sortable: false},
      ],
      html_file_without_image_tag_sort_by: 'count',
      html_file_without_image_tag_sort_desc: true,
      html_file_without_image_tag_list: [],

      html_file_with_many_image_tag_fields: [
        {key: 'file_name', sortable: true},
        {key: 'count', sortable: true},
        {key: 'action', sortable: false},
      ],
      html_file_with_many_image_tag_sort_by: 'count',
      html_file_with_many_image_tag_sort_desc: true,
      html_file_with_many_image_tag_list: [],

      html_file_size_fields: [
        {key: 'file_name', sortable: true},
        {key: 'size', sortable: true},
        {key: 'action', sortable: false},
      ],
      html_file_size_sort_by: 'size',
      html_file_size_sort_desc: false,
      html_file_size_list: [],

      list_url_info_fields: [
        {key: 'feed_title', sortable: true},
        {key: 'count', sortable: true},
      ],
      list_url_info_sort_by: 'count',
      list_url_info_sort_desc: true,
      list_url_info_list: [],

      element_info_fields: [
        {key: 'element_name', sortable: true},
        {key: 'count', sortable: true},
      ],
      element_info_sort_by: 'count',
      element_info_sort_desc: true,
      element_info_list: [],
    }
  },
  methods: {
    getApiUrlPath() {
      let path_prefix = 'https://api.terzeron.com/fm';
      if (process.env.NODE_ENV === 'development') {
        path_prefix = 'http://localhost:5000';
      }
      return path_prefix;
    },
    removeAlias(groupName, feedName) {
      if (groupName === '') {
        groupName = '___';
      }
      const path = this.getApiUrlPath() + `/groups/${groupName}/feeds/${feedName}/alias`;
      axios
          .delete(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.$bvModal
                  .msgBoxOk('실행 중에 오류가 발생하였습니다. ' + res.data.message);
            }
          })
          .catch((error) => {
            this.$bvModal
                .msgBoxOk('실행 중에 오류가 발생하였습니다. ' + error);
          });
    },
    removePublicFeed(feedName) {
      const path = this.getApiUrlPath() + `/public_feeds/${feedName}`;
      axios
          .delete(path)
          .then((res) => {
            if (res.data.status === 'failure') {
              this.$bvModal
                  .msgBoxOk('실행 중에 오류가 발생하였습니다. ' + res.data.message);
            }
          })
          .catch((error) => {
            this.$bvModal
                .msgBoxOk('실행 중에 오류가 발생하였습니다. ' + error);
          })
    },
    statusInfoDeleteClicked(data) {
      console.log(`statusInfoDeleteClicked(${data})`);
      console.log(data.item);
      this.$bvModal
          .msgBoxConfirm('정말로 실행하시겠습니까?')
          .then((value) => {
            if (value) {
              const groupName = data.item['group_name'];
              const feedName = data.item['feed_name']

              this.removeAlias(groupName, feedName);
              this.removePublicFeed(feedName);
              this.status_info_list = _.without(this.status_info_list, data.item);
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
              this.public_feed_info_list = _.without(this.public_feed_info_list, data.item);
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    removeHtmlFile(file_path) {
      const parts = file_path.split('/');
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
                .msgBoxOk('실행 중에 오류가 발생하였습니다. ' + error);
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
              this.html_file_without_image_tag_list = _.without(this.html_file_without_image_tag_list, data.item);
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
              this.html_file_with_many_image_tag_list = _.without(this.html_file_with_many_image_tag_list, data.item);
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
              this.html_file_with_image_not_found_list = _.without(this.html_file_with_image_not_found_list, data.item);
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
              this.html_file_size_list = _.without(this.html_file_size_list, data.item);
            }
          })
          .catch((error) => {
            console.error(error);
          });
    },
    getManagementLink(feed_title, group_name, feed_name) {
      return feed_title ? `<a href="/management/${group_name}/${feed_name}">${feed_title}</a>` : '';
    },
    getProblems() {
      // 상태 정보
      const path_status_info = this.getApiUrlPath() + '/problems/status_info';
      axios.get(path_status_info)
          .then((res_status_info) => {
                if (res_status_info.data.status === 'failure') {
                  console.log(res_status_info.data.message);
                } else {
                  // transformation
                  this.status_info_list = _.map(res_status_info.data['result'], (o) => {
                    o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']);
                    o['http_request'] = o['http_request'] ? 'O' : 'X';
                    o['htaccess'] = o['htaccess'] ? 'O' : 'X';
                    o['public_html'] = o['public_html'] ? 'O' : 'X';
                    o['feedmaker'] = o['feedmaker'] ? 'O' : 'X';
                    o['action'] = '삭제';
                    return o;
                  });
                }

                // 점진적 피딩 진행률 정보
                const path_progress_info = this.getApiUrlPath() + '/problems/progress_info';
                axios.get(path_progress_info)
                    .then((res_progress_info) => {
                      if (res_progress_info.data.status === 'failure') {
                        console.log(res_progress_info.data.message);
                      } else {
                        this.progress_info_list = _.map(res_progress_info.data['result'], (o) => {
                          o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']);
                          return o;
                        });
                      }
                    })
                    .catch((error) => {
                      console.error(error);
                    });

                // 결과(public feed) 정보
                const path_public_feed_info = this.getApiUrlPath() + '/problems/public_feed_info';
                axios.get(path_public_feed_info)
                    .then((res_public_feed_info) => {
                      if (res_public_feed_info.data.status === 'failure') {
                        console.log(res_public_feed_info.data.message);
                      } else {
                        // transformation & filtering
                        this.public_feed_info_list = _.filter(res_public_feed_info.data['result'], (o) => {
                          return parseInt(o['size'], 10) < 4 * 1024;
                        }).map((o) => {
                          o['action'] = "삭제";
                          return o;
                        });
                      }
                    })
                    .catch((error) => {
                      console.error(error);
                    })

                // HTML 정보
                const path_html_info = this.getApiUrlPath() + '/problems/html_info';
                axios.get(path_html_info)
                    .then((res_html_info) => {
                      if (res_html_info.data.status === 'failure') {
                        console.log(res_html_info.data.message);
                      } else {
                        this.html_file_size_list = _.map(res_html_info.data['result']['html_file_size_list'], (o) => {
                          o['action'] = '삭제';
                          return o;
                        });
                        this.html_file_with_many_image_tag_list = _.map(res_html_info.data['result']['html_file_with_many_image_tag_list'], (o) => {
                          o['action'] = '삭제';
                          return o;
                        });
                        this.html_file_without_image_tag_list = _.map(res_html_info.data['result']['html_file_without_image_tag_list'], (o) => {
                          o['action'] = '삭제';
                          return o;
                        });
                        this.html_file_with_image_not_found_list = _.map(res_html_info.data['result']['html_file_image_not_found_list'], (o) => {
                          o['action'] = '삭제';
                          return o;
                        });

                        // element 정보
                        const path_element_info = this.getApiUrlPath() + '/problems/element_info';
                        axios.get(path_element_info)
                            .then((res_element_info) => {
                              if (res_element_info.data.status === 'failure') {
                                console.log(res_element_info.data.message);
                              } else {
                                this.list_url_info_list = _.map(res_element_info.data['result']['feed_name_list_url_count_list'], (o) => {
                                  o['feed_title'] = this.getManagementLink(o['feed_title'], o['group_name'], o['feed_name']);
                                  return o;
                                });
                                this.element_info_list = res_element_info.data['result']['element_name_count_list'];
                              }
                            })
                            .catch((error) => {
                              console.error(error);
                            })
                      }
                    })
                    .catch((error) => {
                      console.error(error);
                    });
              }
          )
          .catch((error) => {
            console.error(error);
          })
    }
  },
  created() {
    return this.getProblems();
  }
  ,
}
;
</script>
