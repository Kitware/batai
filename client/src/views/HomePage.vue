<script lang="ts">
import { defineComponent, onMounted, ref } from 'vue';
import VueMarkdown from 'vue-markdown-render';
import axios from 'axios';
export default defineComponent({
  components: {
    VueMarkdown,
  },
  setup() {
    const source = ref('');
    const     fetchMarkdownContent = () => {
      const url = 'https://raw.githubusercontent.com/Kitware/batai/main/INSTRUCTIONS.md'; // Replace with your GitHub URL
      axios.get(url)
        .then(response => {
          source.value = response.data;
        })
        .catch(error => {
          console.error('Error fetching markdown content:', error);
        });
    };
    onMounted(() => fetchMarkdownContent());

    return { source };
  },
});
</script>

<template>
  <v-card>
    <v-card-title>
      Bat-AI
    </v-card-title>
    <v-card-text class="ma-5">
      <vue-markdown :source="source" />
    </v-card-text>
  </v-card>
</template>
