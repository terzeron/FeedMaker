<template>
  <div class="container mt-4">
    <h1>BootstrapVueNext 기본 테스트</h1>
    
    <!-- 기본 버튼 테스트 -->
    <div class="mb-4">
      <h3>버튼 테스트</h3>
      <BButton variant="primary">Primary 버튼</BButton>
      <BButton variant="secondary" class="ms-2">Secondary 버튼</BButton>
      <BButton variant="success" class="ms-2">Success 버튼</BButton>
    </div>

    <!-- 기본 알림 테스트 -->
    <div class="mb-4">
      <h3>알림 테스트</h3>
      <BAlert variant="success" show>성공 알림입니다!</BAlert>
      <BAlert variant="warning" show>경고 알림입니다!</BAlert>
    </div>

    <!-- 기본 카드 테스트 -->
    <div class="mb-4">
      <h3>카드 테스트</h3>
      <BCard title="테스트 카드">
        <BCardText>이것은 BootstrapVueNext 카드입니다.</BCardText>
        <BButton variant="primary">카드 내 버튼</BButton>
      </BCard>
    </div>

    <!-- 기본 테이블 테스트 -->
    <div class="mb-4">
      <h3>테이블 테스트</h3>
      <BTable 
        v-if="Array.isArray(tableItems) && tableItems.length >= 0"
        :items="tableItems" 
        :fields="tableFields" 
        striped 
        bordered 
        hover
      ></BTable>
    </div>

    <!-- 기본 진행률 바 테스트 -->
    <div class="mb-4">
      <h3>진행률 바 테스트</h3>
      <BProgress :value="75" :max="100" show-progress></BProgress>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const tableFields = [
  { key: 'name', label: '이름' },
  { key: 'age', label: '나이' },
  { key: 'city', label: '도시' }
]

const tableItems = ref([
  { name: '홍길동', age: 30, city: '서울' },
  { name: '김철수', age: 25, city: '부산' },
  { name: '이영희', age: 28, city: '대구' }
])
</script> 