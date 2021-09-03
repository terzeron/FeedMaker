<template>
  <b-container fluid>
    <b-row>
      <b-col cols="12">
        <b-card
            title="피드 상태"
            class="">
          <b-table
              striped
              hover
              responsive
              small
              :fields="status_info_fields"
              :items="status_info_list"
              :sort-by.sync="status_info_sort_by"
              :sort-desc.sync="status_info_sort_desc">
          </b-table>
        </b-card>
      </b-col>

      <b-col cols="12" lg="8">
        <b-card
            title="점진적 피딩 진행률"
            class="">
          <b-table
              striped
              hover
              responsive
              small
              :fields="progress_info_fields"
              :items="progress_info_list"
              :sort-by.sync="progress_info_sort_by"
              :sort-desc.sync="progress_info_sort_desc">
          </b-table>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="이미지가 누락된 HTML 파일"
            class="">
          <b-list-group
              v-for="info in html_file_with_image_not_found_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.count }}</b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="이미지 태그가 없는 HTML 파일"
            class="">
          <b-list-group
              v-for="info in html_file_without_image_tag_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.count }}</b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="이미지 태그가 많은 HTML 파일"
            class="">
          <b-list-group
              v-for="info in html_file_with_many_image_tag_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.count }}</b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="파일 크기가 너무 작은 HTML 파일"
            class="">
          <b-list-group
              v-for="info in html_file_size_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.size }}</b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="결과 파일의 크기"
            class="">
          <b-list-group
              v-for="info in public_feed_info_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.size }}</b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="피드별 list_url element 갯수"
            class="">
          <b-list-group
              v-for="info in feed_name_list_url_count_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.count }}</b-list-group-item>
          </b-list-group>
        </b-card>
      </b-col>

      <b-col cols="12" lg="4">
        <b-card
            title="element별 사용 횟수"
            class="">
          <b-list-group
              v-for="info in element_name_count_list"
              :key="info.name">
            <b-list-group-item>{{ info.name }} : {{ info.count }}</b-list-group-item>
          </b-list-group>
        </b-card>
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

      public_feed_info_list: [],
      access_info_list: [],
      html_file_size_list: [],
      html_file_with_many_image_tag_list: [],
      html_file_without_image_tag_list: [],
      html_file_with_image_not_found_list: [],
      feed_name_list_url_count_list: [],
      element_name_count_list: [],
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
            this.public_feed_info_list = res3.data['result'];
          })
          .catch((error) => {
            console.error(error);
          })

      const path4 = this.getApiUrlPath() + '/problems/element_info';
      axios.get(path4)
          .then((res4) => {
            this.feed_name_list_url_count_list = res4.data['result']['feed_name_list_url_count_list'];
            this.element_name_count_list = res4.data['result']['element_name_count_list'];
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
