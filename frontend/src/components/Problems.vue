<template>
    <b-container fluid>
        <b-row>
            <b-col cols="12">
                <vue-simple-markdown :source="source"></vue-simple-markdown>
            </b-col>
        </b-row>
    </b-container>
</template>

<style>
 div.vue-simple-markdown { white-space: normal !important; }
 div.markdown-body > * { margin-top: 5px !important; margin-bottom: 5px !important; line-height: 1.2; }
 div.markdown-body > h1 { font-size: 1.3em; padding-bottom: 0.1em; margin-block-start: 0.3em; margin-block-end: 0.3em; }
 div.markdown-body > h2 { font-size: 1.2em; padding-bottom: 0.1em; margin-block-start: 0.3em; margin-block-end: 0.3em; }
 div.markdown-body > h3 { font-size: 1.1em; }
 div.markdown-body > h4 { font-size: 1.0em; }
 div.markdown-body > h5 { font-size: 1.0em; }
 div.markdown-body li { font-size: 0.9em; }
</style>

<script>
 import axios from 'axios';
 
 export default {
     name: 'Problems',
     data() {
         return {
             source: '### No result'
         }
     },
     components: {
     },
     methods: {
         getApiUrlPath() {
             var path_prefix = 'https://api.terzeron.com/fm';
             if (process.env.NODE_ENV === 'development') {
                 path_prefix = 'http://localhost:5000/fm';
             }
             return path_prefix;
         },
         getProblems() {
             const path = this.getApiUrlPath() + '/problems';
             axios.get(path)
                  .then((res) => {
                      this.source = res.data.problems;
                  })
                  .catch((error) => {
                      console.error(error);
                  });
         }
     },
     created() {
         return this.getProblems();
     },
 };
</script>
