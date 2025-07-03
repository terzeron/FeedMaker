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
          <div
            v-if="sortedStatusInfolist && Array.isArray(sortedStatusInfolist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in statusInfoFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && statusInfoSortBy === field.key && !statusInfoSortDesc,
                      'sort-desc': field.sortable && statusInfoSortBy === field.key && statusInfoSortDesc
                    }"
                    @click="field.sortable ? sortTable('statusInfo', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="statusInfoSortBy === field.key">
                        {{ statusInfoSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedStatusInfolist"
                  :key="index"
                >
                  <td v-for="field in statusInfoFields" :key="field.key" :data-label="field.label">
                    <span
                      v-if="field.key === 'feed_title'"
                      v-html="item[field.key]"
                    ></span>
                    <span v-else-if="field.key === 'action'">
                      <font-awesome-icon
                        :icon="['far', 'trash-alt']"
                        @click="statusInfoDeleteClicked({ item: item })"
                        v-if="showStatusInfoDeleteButton({ item: item })"
                      />
                    </span>
                    <span v-else-if="['update_date','upload_date','access_date','view_date'].includes(field.key)" class="date-cell">{{ item[field.key] }}</span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedProgressInfolist && Array.isArray(sortedProgressInfolist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in progressInfoFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && progressInfoSortBy === field.key && !progressInfoSortDesc,
                      'sort-desc': field.sortable && progressInfoSortBy === field.key && progressInfoSortDesc
                    }"
                    @click="field.sortable ? sortTable('progressInfo', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="progressInfoSortBy === field.key">
                        {{ progressInfoSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedProgressInfolist"
                  :key="index"
                >
                  <td v-for="field in progressInfoFields" :key="field.key">
                    <span
                      v-if="field.key === 'feed_title'"
                      v-html="item[field.key]"
                    ></span>
                    <span v-else-if="field.key === 'progress_ratio'"
                      >{{ item[field.key] }}%</span
                    >
                    <span v-else-if="field.key === 'due_date'" class="date-cell">{{ item[field.key] }}</span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedListUrlInfolist && Array.isArray(sortedListUrlInfolist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 no-action-col"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in listUrlInfoFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && listUrlInfoSortBy === field.key && !listUrlInfoSortDesc,
                      'sort-desc': field.sortable && listUrlInfoSortBy === field.key && listUrlInfoSortDesc
                    }"
                    @click="field.sortable ? sortTable('listUrlInfo', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="listUrlInfoSortBy === field.key">
                        {{ listUrlInfoSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in sortedListUrlInfolist" :key="index">
                  <td v-for="field in listUrlInfoFields" :key="field.key">
                    <span
                      v-if="field.key === 'feed_title'"
                      v-html="item[field.key]"
                    ></span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedHtmlFileSizelist && Array.isArray(sortedHtmlFileSizelist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in htmlFileSizeFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && htmlFileSizeSortBy === field.key && !htmlFileSizeSortDesc,
                      'sort-desc': field.sortable && htmlFileSizeSortBy === field.key && htmlFileSizeSortDesc
                    }"
                    @click="field.sortable ? sortTable('htmlFileSize', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="htmlFileSizeSortBy === field.key">
                        {{ htmlFileSizeSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedHtmlFileSizelist"
                  :key="index"
                >
                  <td v-for="field in htmlFileSizeFields" :key="field.key">
                    <span v-if="field.key === 'feed_title'" class="feed-title-ellipsis" :title="item[field.key]">
                      <a :href="`/management/${item.feed_dir_path.split('/')[0]}/${item.feed_dir_path.split('/')[1]}`">
                        {{ item[field.key] }}
                      </a>
                    </span>
                    <span v-else-if="field.key === 'action'">
                      <font-awesome-icon
                        :icon="['far', 'trash-alt']"
                        @click="htmlFileSizeDeleteClicked({ item: item })"
                      />
                    </span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedHtmlFileWithoutImageTaglist && Array.isArray(sortedHtmlFileWithoutImageTaglist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in htmlFileWithoutImageTagFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && htmlFileWithoutImageTagSortBy === field.key && !htmlFileWithoutImageTagSortDesc,
                      'sort-desc': field.sortable && htmlFileWithoutImageTagSortBy === field.key && htmlFileWithoutImageTagSortDesc
                    }"
                    @click="field.sortable ? sortTable('htmlFileWithoutImageTag', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="htmlFileWithoutImageTagSortBy === field.key">
                        {{ htmlFileWithoutImageTagSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedHtmlFileWithoutImageTaglist"
                  :key="index"
                >
                  <td
                    v-for="field in htmlFileWithoutImageTagFields"
                    :key="field.key"
                  >
                    <span v-if="field.key === 'feed_title'" class="feed-title-ellipsis" :title="item[field.key]">
                      <a :href="`/management/${item.feed_dir_path.split('/')[0]}/${item.feed_dir_path.split('/')[1]}`">
                        {{ item[field.key] }}
                      </a>
                    </span>
                    <span v-else-if="field.key === 'action'">
                      <font-awesome-icon
                        :icon="['far', 'trash-alt']"
                        @click="
                          imageWithoutImageTagDeleteClicked({ item: item })
                        "
                      />
                    </span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedHtmlFileWithManyImageTaglist && Array.isArray(sortedHtmlFileWithManyImageTaglist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in htmlFileWithManyImageTagFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && htmlFileWithManyImageTagSortBy === field.key && !htmlFileWithManyImageTagSortDesc,
                      'sort-desc': field.sortable && htmlFileWithManyImageTagSortBy === field.key && htmlFileWithManyImageTagSortDesc
                    }"
                    @click="field.sortable ? sortTable('htmlFileWithManyImageTag', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="htmlFileWithManyImageTagSortBy === field.key">
                        {{ htmlFileWithManyImageTagSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedHtmlFileWithManyImageTaglist"
                  :key="index"
                >
                  <td
                    v-for="field in htmlFileWithManyImageTagFields"
                    :key="field.key"
                  >
                    <span v-if="field.key === 'feed_title'" class="feed-title-ellipsis" :title="item[field.key]">
                      <a :href="`/management/${item.feed_dir_path.split('/')[0]}/${item.feed_dir_path.split('/')[1]}`">
                        {{ item[field.key] }}
                      </a>
                    </span>
                    <span v-else-if="field.key === 'action'">
                      <font-awesome-icon
                        :icon="['far', 'trash-alt']"
                        @click="
                          imageWithManyImageTagDeleteClicked({ item: item })
                        "
                      />
                    </span>
                    <span v-else-if="field.key === 'count'">
                      {{ item[field.key] || 'N/A' }}
                    </span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedHtmlFileWithImageNotFoundlist && Array.isArray(sortedHtmlFileWithImageNotFoundlist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 text-break"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in htmlFileWithImageNotFoundFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && htmlFileWithImageNotFoundSortBy === field.key && !htmlFileWithImageNotFoundSortDesc,
                      'sort-desc': field.sortable && htmlFileWithImageNotFoundSortBy === field.key && htmlFileWithImageNotFoundSortDesc
                    }"
                    @click="field.sortable ? sortTable('htmlFileWithImageNotFound', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="htmlFileWithImageNotFoundSortBy === field.key">
                        {{ htmlFileWithImageNotFoundSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedHtmlFileWithImageNotFoundlist"
                  :key="index"
                >
                  <td
                    v-for="field in htmlFileWithImageNotFoundFields"
                    :key="field.key"
                  >
                    <span v-if="field.key === 'feed_title'" class="feed-title-ellipsis" :title="item[field.key]">
                      <a :href="`/management/${item.feed_dir_path.split('/')[0]}/${item.feed_dir_path.split('/')[1]}`">
                        {{ item[field.key] }}
                      </a>
                    </span>
                    <span v-else-if="field.key === 'action'">
                      <font-awesome-icon
                        :icon="['far', 'trash-alt']"
                        @click="imageNotFoundDeleteClicked({ item: item })"
                      />
                    </span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
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
          <div
            v-if="sortedElementInfolist && Array.isArray(sortedElementInfolist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0 no-action-col"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in elementInfoFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && elementInfoSortBy === field.key && !elementInfoSortDesc,
                      'sort-desc': field.sortable && elementInfoSortBy === field.key && elementInfoSortDesc
                    }"
                    @click="field.sortable ? sortTable('elementInfo', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="elementInfoSortBy === field.key">
                        {{ elementInfoSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
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
          </div>
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
          <div
            v-if="sortedPublicFeedInfolist && Array.isArray(sortedPublicFeedInfolist)"
            class="table-responsive"
          >
            <table
              class="table table-striped table-hover table-sm table-bordered m-0 p-0"
            >
              <thead>
                <tr>
                  <th
                    v-for="field in publicFeedInfoFields"
                    :key="field.key"
                    :class="{
                      sortable: field.sortable,
                      'sort-asc': field.sortable && publicFeedInfoSortBy === field.key && !publicFeedInfoSortDesc,
                      'sort-desc': field.sortable && publicFeedInfoSortBy === field.key && publicFeedInfoSortDesc
                    }"
                    @click="field.sortable ? sortTable('publicFeedInfo', field.key) : null"
                  >
                    {{ field.label }}
                    <span v-if="field.sortable" class="sort-icon">
                      <span v-if="publicFeedInfoSortBy === field.key">
                        {{ publicFeedInfoSortDesc ? '↓' : '↑' }}
                      </span>
                      <span v-else>↕</span>
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="(item, index) in sortedPublicFeedInfolist"
                  :key="index"
                >
                  <td v-for="field in publicFeedInfoFields" :key="field.key">
                    <span
                      v-if="field.key === 'feed_title'"
                      class="feed-title-ellipsis"
                      :title="item[field.key]"
                    >
                      <a :href="`/management/${item.group_name}/${item.feed_name}`">
                        {{ item[field.key] }}
                      </a>
                    </span>
                    <span
                      v-else-if="field.key === 'size'"
                      :class="{
                        'text-danger': item.sizeIsDanger,
                        'text-warning': item.sizeIsWarning,
                      }"
                    >
                      {{ item.size_formatted }}
                    </span>
                    <span
                      v-else-if="field.key === 'num_items'"
                      :class="{
                        'text-danger': item.numItemsIsDanger,
                        'text-warning': item.numItemsIsWarning,
                      }"
                      v-html="item[field.key]"
                    ></span>
                    <span
                      v-else-if="field.key === 'upload_date'"
                      class="date-cell"
                      :class="{'text-danger': item.uploadDateIsDanger, 'text-warning': item.uploadDateIsWarning}"
                      v-html="item[field.key]"
                    ></span>
                    <span v-else-if="field.key === 'action'">
                      <font-awesome-icon
                        :icon="['far', 'trash-alt']"
                        @click="publicFeedInfoDeleteClicked({ item: item })"
                      />
                    </span>
                    <span v-else>{{ item[field.key] }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="text-center p-3">
            <p class="text-muted">데이터를 불러오는 중...</p>
          </div>
        </BCardBody>
      </BCol>
    </BRow>

    <BRow>
      <BCol cols="12" class="mx-auto text-center mt-5 mb-3">
        Feed Manager by {{ adminEmail }}
        <div class="text-muted small mt-1">v{{ appVersion }}</div>
      </BCol>
    </BRow>
  </BContainer>
</template>

<style>
/* 테이블 스타일링 개선 */
.table-responsive {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.table {
  margin-bottom: 0;
}

/* Bootstrap 기본 테이블 스타일 완전 덮어쓰기 - 더 강력한 선택자 */
.table td,
.table th,
.table > tbody > tr > td,
.table > tbody > tr > th,
.table > thead > tr > td,
.table > thead > tr > th,
.table > tfoot > tr > td,
.table > tfoot > tr > th {
  padding: 0.0625rem 0.125rem !important;
  margin: 0 !important;
}

/* 테이블 헤딩 스타일 완전 덮어쓰기 */
.table thead th,
.table > thead > tr > th,
.table-responsive .table thead th,
.table-responsive .table > thead > tr > th {
  background-color: white !important;
  color: #000 !important;
  border-bottom: 2px solid #495057 !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.5px !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 10 !important;
  padding: 0.375rem 0.125rem !important;
  margin: 0 !important;
  border-top: none !important;
  border-left: none !important;
  border-right: none !important;
  line-height: 1.3 !important;
  height: auto !important;
  min-height: 0 !important;
}

/* col-lg-4와 col-lg-8 테이블 헤딩 높이 조정 */
.col-lg-4 .table thead th,
.col-lg-4 .table > thead > tr > th,
.col-lg-8 .table thead th,
.col-lg-8 .table > thead > tr > th {
  padding: 0.375rem 0.125rem !important;
  line-height: 1.3 !important;
  height: auto !important;
  min-height: 0 !important;
  font-size: 0.95rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}

/* 모든 테이블 헤딩 일관성 유지 */
.table thead th,
.table > thead > tr > th {
  padding: 0.375rem 0.125rem !important;
  line-height: 1.3 !important;
  height: auto !important;
  min-height: 0 !important;
  font-size: 0.875rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}

.table tbody tr:hover {
  background-color: #e9ecef;
  transition: background-color 0.2s ease;
}

.table td {
  vertical-align: middle;
  border-color: #dee2e6;
  padding: 0.0625rem 0.125rem !important;
  margin: 0 !important;
}

/* 정렬 가능한 헤더 스타일 */
.table th.sortable,
.table > thead > tr > th.sortable {
  cursor: pointer;
  position: relative;
  background-color: white !important;
  color: #000 !important;
}

.table th.sortable:hover,
.table > thead > tr > th.sortable:hover {
  background-color: #f8f9fa !important;
}

.table th.sortable::after,
.table > thead > tr > th.sortable::after {
  content: "↕";
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.5;
  font-size: 0.75rem;
  color: #000;
  z-index: 1;
}

/* 정렬 아이콘 숨김 - CSS ::after만 사용 */
.sort-icon {
  display: none !important;
}

.sort-icon span {
  display: none !important;
}

/* 정렬 중인 헤더 스타일 통일 */
.table th.sortable.sort-asc::after,
.table > thead > tr > th.sortable.sort-asc::after {
  content: "↑";
  opacity: 1;
  color: #000;
}

.table th.sortable.sort-desc::after,
.table > thead > tr > th.sortable.sort-desc::after {
  content: "↓";
  opacity: 1;
  color: #000;
}

/* 아이콘 스타일링 */
.font-awesome-icon {
  cursor: pointer;
  color: #dc3545;
  transition: color 0.2s ease;
}

.font-awesome-icon:hover {
  color: #c82333;
}

/* 텍스트 색상 클래스 */
.text-danger {
  color: #dc3545 !important;
}

.text-warning {
  color: #ffc107 !important;
}

.text-muted {
  color: #6c757d !important;
}

/* 카드 헤더 스타일 복구 */
.card-header {
  background-color: #495057 !important;
  color: white !important;
  font-weight: 600;
  border-bottom: 1px solid #343a40;
}

/* 테이블 헤딩 스타일 복구 */
.table thead th,
.table > thead > tr > th,
.table-responsive .table thead th,
.table-responsive .table > thead > tr > th {
  background-color: white !important;
  color: #000 !important;
  border-bottom: 2px solid #495057 !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  font-size: 0.95rem !important;
  letter-spacing: 0.5px !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 10 !important;
  padding: 0.375rem 0.125rem !important;
  margin: 0 !important;
  border-top: none !important;
  border-left: none !important;
  border-right: none !important;
  line-height: 1.3 !important;
  height: auto !important;
  min-height: 0 !important;
}

/* col-lg-4와 col-lg-8 테이블 헤딩 높이 조정 */
.col-lg-4 .table thead th,
.col-lg-4 .table > thead > tr > th,
.col-lg-8 .table thead th,
.col-lg-8 .table > thead > tr > th {
  padding: 0.375rem 0.125rem !important;
  line-height: 1.3 !important;
  height: auto !important;
  min-height: 0 !important;
  font-size: 0.95rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}

/* 모든 테이블 헤딩 일관성 유지 */
.table thead th,
.table > thead > tr > th {
  padding: 0.375rem 0.125rem !important;
  line-height: 1.3 !important;
  height: auto !important;
  min-height: 0 !important;
  font-size: 0.875rem !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.5px !important;
}

.table tbody tr:hover {
  background-color: #e9ecef;
  transition: background-color 0.2s ease;
}

.table td {
  vertical-align: middle;
  border-color: #dee2e6;
  padding: 0.0625rem 0.125rem !important;
  margin: 0 !important;
}

/* 정렬 가능한 헤더 스타일 */
.table th.sortable,
.table > thead > tr > th.sortable {
  cursor: pointer;
  position: relative;
  background-color: white !important;
  color: #000 !important;
}

.table th.sortable:hover,
.table > thead > tr > th.sortable:hover {
  background-color: #f8f9fa !important;
}

.table th.sortable::after,
.table > thead > tr > th.sortable::after {
  content: "↕";
  position: absolute;
  right: 6px;
  top: 50%;
  transform: translateY(-50%);
  opacity: 0.5;
  font-size: 0.75rem;
  color: #000;
  z-index: 1;
}

/* 정렬 아이콘 숨김 - CSS ::after만 사용 */
.sort-icon {
  display: none !important;
}

.sort-icon span {
  display: none !important;
}

/* 정렬 중인 헤더 스타일 통일 */
.table th.sortable.sort-asc::after,
.table > thead > tr > th.sortable.sort-asc::after {
  content: "↑";
  opacity: 1;
  color: #000;
}

.table th.sortable.sort-desc::after,
.table > thead > tr > th.sortable.sort-desc::after {
  content: "↓";
  opacity: 1;
  color: #000;
}

/* 피드 제목 ellipsis 스타일 */
.feed-title-ellipsis {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feed-title-ellipsis a {
  color: #007bff;
  text-decoration: underline;
}

.feed-title-ellipsis a:hover {
  color: #0056b3;
  text-decoration: underline;
}

/* 모든 테이블의 첫 번째 필드 말줄임 처리 */
.table td:first-child {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table th:first-child {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-12:first-child .table td:first-child {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-12:first-child .table th:first-child {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-12:first-child .table td:first-child span,
.col-12:first-child .table td:first-child a {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 테이블 너비 제한 및 스크롤 방지 */
.table {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  table-layout: fixed;
}

.table td,
.table th {
  word-wrap: break-word;
  overflow: visible;
}

/* 테이블 컨테이너 너비 제한 */
.table-responsive {
  max-width: 100%;
  overflow-x: hidden;
}

/* 피드 상태 테이블은 제외 (첫 번째 col-12) */
.col-12:first-child .table td:first-child {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-12:first-child .table th:first-child {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-12:first-child .table td:first-child span,
.col-12:first-child .table td:first-child a {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* col-lg-4 테이블 컨테이너 최대 폭 제한 */
.col-lg-4 .table-responsive {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

/* 날짜 셀만 폰트 작게 */
.date-cell {
  font-size: 0.75em;
  color: #666;
}
</style>

<script>
import axios from "axios";
import { getApiUrlPath } from "../utils/api";
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
    appVersion: function () {
      return process.env.VUE_APP_VERSION || 'dev';
    },
    // Computed properties for sorted data with stronger safety checks
    sortedStatusInfolist: function () {
      // Ensure data is always an array and contains valid objects
      let data = this.statusInfolist;
      if (!data) {
        data = [];
      } else if (!Array.isArray(data)) {
        data = [];
      } else {
        // Filter out any non-object items
        data = data.filter(item => item && typeof item === 'object');
      }
      return this.sortData(data, this.statusInfoSortBy, this.statusInfoSortDesc);
    },
    sortedProgressInfolist: function () {
      const data = Array.isArray(this.progressInfolist) ? this.progressInfolist : [];
      return this.sortData(data, this.progressInfoSortBy, this.progressInfoSortDesc);
    },
    sortedListUrlInfolist: function () {
      const data = Array.isArray(this.listUrlInfolist) ? this.listUrlInfolist : [];
      return this.sortData(data, this.listUrlInfoSortBy, this.listUrlInfoSortDesc);
    },
    sortedElementInfolist: function () {
      const data = Array.isArray(this.elementInfolist) ? this.elementInfolist : [];
      return this.sortData(data, this.elementInfoSortBy, this.elementInfoSortDesc);
    },
    sortedHtmlFileSizelist: function () {
      const data = Array.isArray(this.htmlFileSizelist) ? this.htmlFileSizelist : [];
      return this.sortData(data, this.htmlFileSizeSortBy, this.htmlFileSizeSortDesc);
    },
    sortedHtmlFileWithoutImageTaglist: function () {
      const data = Array.isArray(this.htmlFileWithoutImageTaglist)
        ? this.htmlFileWithoutImageTaglist
        : [];
      return this.sortData(data, this.htmlFileWithoutImageTagSortBy, this.htmlFileWithoutImageTagSortDesc);
    },
    sortedHtmlFileWithManyImageTaglist: function () {
      const data = Array.isArray(this.htmlFileWithManyImageTaglist)
        ? this.htmlFileWithManyImageTaglist
        : [];
      return this.sortData(data, this.htmlFileWithManyImageTagSortBy, this.htmlFileWithManyImageTagSortDesc);
    },
    sortedHtmlFileWithImageNotFoundlist: function () {
      const data = Array.isArray(this.htmlFileWithImageNotFoundlist)
        ? this.htmlFileWithImageNotFoundlist
        : [];
      return this.sortData(data, this.htmlFileWithImageNotFoundSortBy, this.htmlFileWithImageNotFoundSortDesc);
    },
    sortedPublicFeedInfolist: function () {
      const data = Array.isArray(this.publicFeedInfolist)
        ? this.publicFeedInfolist
        : [];
      return this.sortData(data, this.publicFeedInfoSortBy, this.publicFeedInfoSortDesc);
    },
  },
  data: function () {
    return {
      problems: {},
      statusInfoFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "feed_name", label: "이름", sortable: true },
        { key: "feedmaker", label: "생성", sortable: true },
        { key: "public_html", label: "등록", sortable: true },
        { key: "http_request", label: "요청", sortable: true },
        { key: "update_date", label: "생성일", sortable: true },
        { key: "upload_date", label: "등록일", sortable: true },
        { key: "access_date", label: "요청일", sortable: true },
        { key: "view_date", label: "조회일", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      statusInfolist: [],
      statusInfoSortBy: "feed_title",
      statusInfoSortDesc: false,
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
        { key: "file_name", label: "파일 이름", sortable: true },
        { key: "size", label: "크기", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileSizeSortBy: "size",
      htmlFileSizeSortDesc: true,
      htmlFileSizelist: [],
      htmlFileWithoutImageTagFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_name", label: "파일 이름", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileWithoutImageTagSortBy: "feed_title",
      htmlFileWithoutImageTagSortDesc: true,
      htmlFileWithoutImageTaglist: [],
      htmlFileWithManyImageTagFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_name", label: "파일 이름", sortable: true },
        { key: "count", label: "개수", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileWithManyImageTagSortBy: "count",
      htmlFileWithManyImageTagSortDesc: true,
      htmlFileWithManyImageTaglist: [],
      htmlFileWithImageNotFoundFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "file_name", label: "파일 이름", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      htmlFileWithImageNotFoundSortBy: "feed_title",
      htmlFileWithImageNotFoundSortDesc: true,
      htmlFileWithImageNotFoundlist: [],
      publicFeedInfoFields: [
        { key: "feed_title", label: "제목", sortable: true },
        { key: "size", label: "크기", sortable: true },
        { key: "num_items", label: "개수", sortable: true },
        { key: "upload_date", label: "업로드일", sortable: true },
        { key: "action", label: "작업", sortable: false },
      ],
      publicFeedInfoSortBy: "size",
      publicFeedInfoSortDesc: true,
      publicFeedInfolist: [],
    };
  },
  methods: {
    sortTable: function (tableType, fieldKey) {
      // 현재 정렬 상태 확인 및 토글
      const currentSortBy = this[`${tableType}SortBy`];
      const currentSortDesc = this[`${tableType}SortDesc`];

      if (currentSortBy === fieldKey) {
        // 같은 필드 클릭 시 정렬 방향 토글
        this[`${tableType}SortDesc`] = !currentSortDesc;
      } else {
        // 다른 필드 클릭 시 해당 필드로 정렬하고 오름차순으로 설정
        this[`${tableType}SortBy`] = fieldKey;
        this[`${tableType}SortDesc`] = false;
      }
    },
    sortData: function (data, sortBy, sortDesc) {
      if (!data || data.length === 0 || !sortBy) {
        return data;
      }

      return _.orderBy(data, [sortBy], [sortDesc ? 'desc' : 'asc']);
    },
    showStatusInfoDeleteButton: function (data) {
      return data.item["feed_title"] === "" && data.item["public_html"] === "O";
    },
    removePublicFeed(feedName) {
      const path = getApiUrlPath() + `/public_feeds/${feedName}`;
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
        getApiUrlPath() +
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
    formatFileSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
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
      const pathStatusInfo = getApiUrlPath() + "/problems/status_info";
      axios
        .get(pathStatusInfo)
        .then((resStatusInfo) => {
          if (resStatusInfo.data.status === "failure") {
            this.statusInfolist = [];
          } else {
            // Convert object to array if result is an object
            let result = resStatusInfo.data["result"];
            if (
              result &&
              typeof result === "object" &&
              !Array.isArray(result)
            ) {
              result = Object.values(result);
            } else if (!Array.isArray(result)) {
              result = [];
            }

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
          }
        })
        .catch((error) => {
          console.error(error);
          this.statusInfolist = [];
        });

      // Progressive feed progress info
      const pathProgressInfo = getApiUrlPath() + "/problems/progress_info";
      axios
        .get(pathProgressInfo)
        .then((resProgressInfo) => {
          if (resProgressInfo.data.status === "failure") {
            this.progressInfolist = [];
          } else {
            // Convert object to array if result is an object
            let result = resProgressInfo.data["result"];
            if (
              result &&
              typeof result === "object" &&
              !Array.isArray(result)
            ) {
              result = Object.values(result);
            } else if (!Array.isArray(result)) {
              result = [];
            }

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
        getApiUrlPath() + "/problems/public_feed_info";
      axios
        .get(pathPublicFeedInfo)
        .then((resPublicFeedInfo) => {
          if (resPublicFeedInfo.data.status === "failure") {
            this.publicFeedInfolist = [];
          } else {
            // Convert object to array if result is an object
            let result = resPublicFeedInfo.data["result"];
            if (
              result &&
              typeof result === "object" &&
              !Array.isArray(result)
            ) {
              result = Object.values(result);
            } else if (!Array.isArray(result)) {
              result = [];
            }

            // transformation & filtering
            let day2MonthAgo = new Date();
            day2MonthAgo.setTime(
              day2MonthAgo.getTime() - 2 * 30 * 24 * 60 * 60 * 1000
            ); // 2 months ago
            day2MonthAgo = day2MonthAgo.toISOString().substring(0, 12);
            this.publicFeedInfolist = _.filter(result, (o) => {
              return (
                o["upload_date"] < day2MonthAgo ||
                o["file_size"] < 4 * 1024 ||
                o["num_items"] < 5 ||
                o["num_items"] > 20
              );
            }).map((o) => {
              // Keep feed_title as plain text, don't convert to HTML link
              if (!o["feed_title"]) {
                o["feed_title"] = o["feed_name"];
              }
              // Map file_size to size field for display
              o["size"] = o["file_size"];
              // Add formatted size for display while keeping original for sorting
              o["size_formatted"] = this.formatFileSize(o["file_size"]);
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
      const pathHtmlInfo = getApiUrlPath() + "/problems/html_info";
      axios
        .get(pathHtmlInfo)
        .then((resHtmlInfo) => {
          if (resHtmlInfo.data.status === "failure") {
            this.htmlFileSizelist = [];
            this.htmlFileWithManyImageTaglist = [];
            this.htmlFileWithoutImageTaglist = [];
            this.htmlFileWithImageNotFoundlist = [];
          } else {
            // Convert object properties to arrays if they are objects
            const result = resHtmlInfo.data["result"];
            const htmlFileSizeMap =
              result &&
              result["html_file_size_map"] &&
              typeof result["html_file_size_map"] === "object" &&
              !Array.isArray(result["html_file_size_map"])
                ? Object.values(result["html_file_size_map"])
                : Array.isArray(result["html_file_size_map"])
                ? result["html_file_size_map"]
                : [];
            const htmlFileWithManyImageTagMap =
              result &&
              result["html_file_with_many_image_tag_map"] &&
              typeof result["html_file_with_many_image_tag_map"] === "object" &&
              !Array.isArray(result["html_file_with_many_image_tag_map"])
                ? Object.values(result["html_file_with_many_image_tag_map"])
                : Array.isArray(result["html_file_with_many_image_tag_map"])
                ? result["html_file_with_many_image_tag_map"]
                : [];


            const htmlFileWithoutImageTagMap =
              result &&
              result["html_file_without_image_tag_map"] &&
              typeof result["html_file_without_image_tag_map"] === "object" &&
              !Array.isArray(result["html_file_without_image_tag_map"])
                ? Object.values(result["html_file_without_image_tag_map"])
                : Array.isArray(result["html_file_without_image_tag_map"])
                ? result["html_file_without_image_tag_map"]
                : [];
            const htmlFileImageNotFoundMap =
              result &&
              result["html_file_image_not_found_map"] &&
              typeof result["html_file_image_not_found_map"] === "object" &&
              !Array.isArray(result["html_file_image_not_found_map"])
                ? Object.values(result["html_file_image_not_found_map"])
                : Array.isArray(result["html_file_image_not_found_map"])
                ? result["html_file_image_not_found_map"]
                : [];

            this.htmlFileSizelist = _.map(htmlFileSizeMap, (o) => {
              o["action"] = "Delete";
              // Keep feed_title as plain text, don't convert to HTML link
              if (!o["feed_title"]) {
                const feedDirParts = o["feed_dir_path"] ? o["feed_dir_path"].split("/") : [];
                if (feedDirParts.length >= 2) {
                  o["feed_title"] = feedDirParts[1]; // Use feed_name as fallback
                }
              }
              // Extract file name from file_path
              if (o["file_path"]) {
                const pathParts = o["file_path"].split("/");
                o["file_name"] = pathParts[pathParts.length - 1];
              }
              return o;
            });
            this.htmlFileWithManyImageTaglist = _.map(
              htmlFileWithManyImageTagMap,
              (o) => {
                o["action"] = "Delete";
                // Keep feed_title as plain text, don't convert to HTML link
                if (!o["feed_title"]) {
                  const feedDirParts = o["feed_dir_path"] ? o["feed_dir_path"].split("/") : [];
                  if (feedDirParts.length >= 2) {
                    o["feed_title"] = feedDirParts[1]; // Use feed_name as fallback
                  }
                }
                // Extract file name from file_path
                if (o["file_path"]) {
                  const pathParts = o["file_path"].split("/");
                  o["file_name"] = pathParts[pathParts.length - 1];
                }

                return o;
              }
            );
            this.htmlFileWithoutImageTaglist = _.map(
              htmlFileWithoutImageTagMap,
              (o) => {
                o["action"] = "Delete";
                // Keep feed_title as plain text, don't convert to HTML link
                if (!o["feed_title"]) {
                  const feedDirParts = o["feed_dir_path"] ? o["feed_dir_path"].split("/") : [];
                  if (feedDirParts.length >= 2) {
                    o["feed_title"] = feedDirParts[1]; // Use feed_name as fallback
                  }
                }
                // Extract file name from file_path
                if (o["file_path"]) {
                  const pathParts = o["file_path"].split("/");
                  o["file_name"] = pathParts[pathParts.length - 1];
                }
                return o;
              }
            );
            this.htmlFileWithImageNotFoundlist = _.map(
              htmlFileImageNotFoundMap,
              (o) => {
                o["action"] = "Delete";
                // Keep feed_title as plain text, don't convert to HTML link
                if (!o["feed_title"]) {
                  const feedDirParts = o["feed_dir_path"] ? o["feed_dir_path"].split("/") : [];
                  if (feedDirParts.length >= 2) {
                    o["feed_title"] = feedDirParts[1]; // Use feed_name as fallback
                  }
                }
                // Extract file name from file_path
                if (o["file_path"]) {
                  const pathParts = o["file_path"].split("/");
                  o["file_name"] = pathParts[pathParts.length - 1];
                }
                return o;
              }
            );
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
      const pathElementInfo = getApiUrlPath() + "/problems/element_info";
      axios
        .get(pathElementInfo)
        .then((resElementInfo) => {
          if (resElementInfo.data.status === "failure") {
            this.elementInfolist = [];
          } else {
            // Convert object to array if result is an object
            let result = resElementInfo.data["result"];
            if (
              result &&
              typeof result === "object" &&
              !Array.isArray(result)
            ) {
              result = Object.values(result);
            } else if (!Array.isArray(result)) {
              result = [];
            }

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
      const listUrlInfo = getApiUrlPath() + "/problems/list_url_info";
      axios
        .get(listUrlInfo)
        .then((reslistUrlInfo) => {
          if (reslistUrlInfo.data.status === "failure") {
            this.listUrlInfolist = [];
          } else {
            // Convert object to array if result is an object
            let result = reslistUrlInfo.data["result"];
            if (
              result &&
              typeof result === "object" &&
              !Array.isArray(result)
            ) {
              result = Object.values(result);
            } else if (!Array.isArray(result)) {
              result = [];
            }

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

<style>
/* 피드 제목 ellipsis 스타일 */
.feed-title-ellipsis {
  display: inline-block;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.feed-title-ellipsis a {
  color: #007bff;
  text-decoration: underline;
}

.feed-title-ellipsis a:hover {
  color: #0056b3;
  text-decoration: underline;
}

/* 테이블 너비 제한 및 스크롤 방지 */
.table {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  table-layout: fixed;
}

.table td,
.table th {
  word-wrap: break-word;
  overflow: visible;
}

/* 테이블 컨테이너 너비 제한 */
.table-responsive {
  max-width: 100%;
  overflow-x: hidden;
}

/* col-lg-4 테이블 컨테이너 최대 폭 제한 */
.col-lg-4 .table-responsive {
  max-width: 100% !important;
  overflow-x: hidden !important;
}

/* 날짜 셀만 폰트 작게 */
.date-cell {
  font-size: 0.75em;
  color: #666;
}

</style>
