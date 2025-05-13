<script lang="ts">
import { defineComponent, ref, Ref, } from 'vue';
import NABatAdminUpdateSpecies from '@components/NABat/NABatAdminUpdateSpecies.vue';
import NABatAdminBrowser from '@components/NABat/NABatAdminBrowser.vue';

export default defineComponent({
  name: 'NABatAdmin',
  components: {
    NABatAdminUpdateSpecies,
    NABatAdminBrowser,
  },
  setup() {
    // Reactive state for the settings
    const tab: Ref<'browser' | 'species'> = ref('browser');

    return {
      tab,
    };
  },
});
</script>

<template>
  <v-card>
    <v-tabs
      v-model="tab"
      class="ma-auto"
    >
      <v-tab
        value="browser"
        size="small"
      >
        Recording Browser
      </v-tab>
      <v-tab
        value="species"
        size="small"
      >
        Update Species
      </v-tab>
    </v-tabs>

    <v-window v-model="tab" id="admin-window">
      <v-window-item value="browser">
        <v-card-title>Admin Recording Browser</v-card-title>
        <v-card-text>
          <NABatAdminBrowser />
        </v-card-text>
      </v-window-item>
      <v-window-item value="species">
        <NABatAdminUpdateSpecies />
      </v-window-item>
    </v-window>
  </v-card>
</template>
<style scoped>
/* Add optional styling */
.v-container {
  margin-top: 20px;
}
.admin-window {
  max-height: 70vh;
  overflow-y: auto;
}
</style>
