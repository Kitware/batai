<script lang="ts">
import { defineComponent, inject, ref, onMounted } from "vue";
import OAuthClient from "@girder/oauth-client";
import { useRouter } from "vue-router";

export default defineComponent({
  setup() {
    const oauthClient = inject<OAuthClient>("oauthClient");
    const router = useRouter();
    if (oauthClient === undefined) {
      throw new Error('Must provide "oauthClient" into component.');
    }

    const loginText = ref('Login');
    const checkLogin = () => {
      if (oauthClient.isLoggedIn) {
        loginText.value = "Logout";
      } else {
        loginText.value = "Login";
      }
    };
    const logInOrOut = async () => {
      if (oauthClient.isLoggedIn) {
        await oauthClient.logout();
        localStorage.clear();
        router.push("Login");
        checkLogin();
      } else {
        oauthClient.redirectToLogin();
      }
    };
    onMounted(() => {
      checkLogin();
    });
    const activeTab = ref("recordings");
    return { oauthClient, loginText, logInOrOut, activeTab };
  },
});
</script>

<template>
  <v-app id="app">
    <v-app-bar app>
      <v-tabs
        v-if="oauthClient.isLoggedIn"
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
      <v-btn @click="logInOrOut">
        {{ loginText }}
      </v-btn>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>
