<script lang="ts">
import { defineComponent, inject, computed, ref } from 'vue';
import OAuthClient from '@girder/oauth-client';

export default defineComponent({
  setup() {
    const oauthClient = inject<OAuthClient>('oauthClient');
    if (oauthClient === undefined) {
      throw new Error('Must provide "oauthClient" into component.');
    }

    const loginText = computed(() => (oauthClient.isLoggedIn ? 'Logout' : 'Login'));
    const logInOrOut = () => {
      if (oauthClient.isLoggedIn) {
        oauthClient.logout();
      } else {
        oauthClient.redirectToLogin();
      }
    };
    const activeTab = ref('recordings');
    return { oauthClient, loginText, logInOrOut, activeTab };
  },
});
</script>

<template>
  <v-app id="app">
    <v-app-bar app>
      <v-tabs
        fixed-tabs
        :model-value="activeTab"
      >
        <v-tab
          to="/"
          value="home"
        >
          Home
        </v-tab>
        <v-tab
          to="/recordings"
          value="recordings"
        >
          Recordings
        </v-tab>
      </v-tabs>
      <v-spacer />
      <v-btn
        @click="logInOrOut"
      >
        {{ loginText }}
      </v-btn>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
