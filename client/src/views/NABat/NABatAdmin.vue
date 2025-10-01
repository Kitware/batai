<script lang="ts">
import { defineComponent, onMounted, ref, Ref, } from 'vue';
import useState from '@use/useState';
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

    const accessToken: Ref<string> = ref('');
    const refreshToken: Ref<string> = ref('');

    const { naBatSessionId, startNABatSession } = useState();

    onMounted(() => {
      const sessionId = localStorage.getItem('nabat_session_id');
      if (sessionId) {
        naBatSessionId.value = sessionId;
      }
    });

    return {
      tab,
      accessToken,
      refreshToken,
      startNABatSession,
      naBatSessionId,
    };
  },
});
</script>

<template>
  <v-card>
    <v-card
      class="my-4 ml-2"
      flat
    >
      <v-row>
        <v-col cols="6">
          <v-label>NABat Access Token</v-label>
          <v-text-field
            v-model="accessToken"
            density="compact"
            hide-details
            hint="NABat Access Token"
            persistent-hint
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col cols="6">
          <v-label>NABat Refresh Token</v-label>
          <v-text-field
            v-model="refreshToken"
            density="compact"
            hide-details
            hint="NABat Refresh Token"
            persistent-hint
          />
        </v-col>
      </v-row>
      <v-row>
        <v-col>
          <v-btn
            :disabled="!refreshToken || !accessToken"
            color="primary"
            @click="startNABatSession(accessToken, refreshToken)"
          >
            Create NABat Session
          </v-btn>
          <span v-if="naBatSessionId">{{ naBatSessionId }}</span>
        </v-col>
      </v-row>
    </v-card>
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

    <v-window
      id="admin-window"
      v-model="tab"
    >
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
</style>
