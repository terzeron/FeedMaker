<template>
  <b-container fluid>
    <b-row>
      <b-col cols="12" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">피드 상태</b-card-header>
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="8" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">점진적 피딩 진행률
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">이미지가 누락된 HTML 파일
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">이미지 태그가 없는 HTML
          파일
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">이미지 태그가 많은 HTML 파일
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">파일 크기가 너무 작은 HTML 파일
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">결과(public feed) 파일의 크기
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">피드별 list_url element
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
          </b-table>
        </b-card-body>
      </b-col>

      <b-col cols="12" lg="4" class="m-0 p-0">
        <b-card-header header-bg-variant="dark" header-text-variant="white" header-tag="header">element별 사용 횟수
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

export default {
  name: 'Problems',
  data() {
    return {
      problems: {},
      progress_info_fields: [
        {key: 'title', sortable: true},
        {key: 'index', sortable: true},
        {key: 'count', sortable: true},
        {key: 'unit_size', sortable: true},
        {key: 'ratio', sortable: true},
        {key: 'due_date', sortable: true}
      ],
      progress_info_sort_by: 'ratio',
      progress_info_sort_desc: true,
      progress_info_list: [],

      status_info_fields: [
        {key: 'title', sortable: true},
        {key: 'alias', sortable: true},
        {key: 'name', sortable: true},
        {key: 'http_request', sortable: true},
        {key: 'htaccess', sortable: true},
        {key: 'public_html', sortable: true},
        {key: 'feedmaker', sortable: true},
        {key: 'access_date', sortable: true},
        {key: 'view_date', sortable: true},
        {key: 'upload_date', sortable: true},
        {key: 'update_date', sortable: true}
      ],
      status_info_sort_by: 'alias',
      status_info_sort_desc: false,
      status_info_list: [],

      html_file_with_image_not_found_fields: [
        {key: 'name', sortable: true},
        {key: 'count', sortable: true}
      ],
      html_file_with_image_not_found_sort_by: 'count',
      html_file_with_image_not_found_sort_desc: true,
      html_file_with_image_not_found_list: [],

      html_file_without_image_tag_fields: [
        {key: 'name', sortable: true},
        {key: 'count', sortable: true}
      ],
      html_file_without_image_tag_sort_by: 'count',
      html_file_without_image_tag_sort_desc: true,
      html_file_without_image_tag_list: [],

      html_file_with_many_image_tag_fields: [
        {key: 'name', sortable: true},
        {key: 'count', sortable: true}
      ],
      html_file_with_many_image_tag_sort_by: 'count',
      html_file_with_many_image_tag_sort_desc: true,
      html_file_with_many_image_tag_list: [],

      html_file_size_fields: [
        {key: 'name', sortable: true},
        {key: 'size', sortable: true}
      ],
      html_file_size_sort_by: 'size',
      html_file_size_sort_desc: false,
      html_file_size_list: [],

      public_feed_info_fields: [
        {key: 'name', sortable: true},
        {key: 'size', sortable: true}
      ],
      public_feed_info_sort_by: 'size',
      public_feed_info_sort_desc: false,
      public_feed_info_list: [],

      list_url_info_fields: [
        {key: 'name', sortable: true},
        {key: 'count', sortable: true}
      ],
      list_url_info_sort_by: 'count',
      list_url_info_sort_desc: true,
      list_url_info_list: [],

      element_info_fields: [
        {key: 'name', sortable: true},
        {key: 'count', sortable: true}
      ],
      element_info_sort_by: 'count',
      element_info_sort_desc: true,
      element_info_list: [],
    }
  },
  components: {},
  methods: {
    getApiUrlPath() {
      let path_prefix = 'https://api.terzeron.com/fm';
      if (process.env.NODE_ENV === 'development') {
        path_prefix = 'http://localhost:5000';
      }
      return path_prefix;
    },
    getProblems() {
      const path1 = this.getApiUrlPath() + '/problems/progress_info';
      axios.get(path1)
          .then((res1) => {
            if (res1.data.status === 'failure') {
              console.log(res1.data.message);
            } else {
              this.progress_info_list = res1.data['result'];
            }
          })
          .catch((error) => {
            console.error(error);
          });

      const path2 = this.getApiUrlPath() + '/problems/html_info';
      axios.get(path2)
          .then((res2) => {
            this.html_file_size_list = res2.data['result']['html_file_size_list'];
            this.html_file_with_many_image_tag_list = res2.data['result']['html_file_with_many_image_tag_list'];
            this.html_file_without_image_tag_list = res2.data['result']['html_file_without_image_tag_list'];
            this.html_file_with_image_not_found_list = res2.data['result']['html_file_image_not_found_list'];
          })
          .catch((error) => {
            console.error(error);
          });

      const path3 = this.getApiUrlPath() + '/problems/public_feed_info';
      axios.get(path3)
          .then((res3) => {
            this.public_feed_info_list = _.filter(res3.data['result'], function (o) {
              return parseInt(o['size'], 10) < 4 * 1024;
            });
          })
          .catch((error) => {
            console.error(error);
          })

      const path4 = this.getApiUrlPath() + '/problems/element_info';
      axios.get(path4)
          .then((res4) => {
            this.list_url_info_list = res4.data['result']['feed_name_list_url_count_list'];
            this.element_info_list = res4.data['result']['element_name_count_list'];
          })
          .catch((error) => {
            console.error(error);
          })

      const path5 = this.getApiUrlPath() + '/problems/status_info';
      axios.get(path5)
          .then((res5) => {
            this.status_info_list = res5.data['result'];

          })
          .catch((error) => {
            console.error(error);
          })
    }
  },
  created() {
    return this.getProblems();
  },
};
</script>
