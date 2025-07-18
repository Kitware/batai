<script lang="ts">
import { defineComponent, inject, ref, onMounted, computed, watch } from "vue";
import OAuthClient from "@resonant/oauth-client";
import { useRoute, useRouter } from "vue-router";
import useState from "./use/useState";
import { getRecordings } from "./api/api";
import HelpSystem from "./components/HelpSystem.vue";

export default defineComponent({
  components: { HelpSystem },
  setup() {
    const oauthClient = inject<OAuthClient>("oauthClient");
    const router = useRouter();
    const route = useRoute();
    const { nextShared, sharedList, sideTab, loadConfiguration, configuration } = useState();
    const getShared = async () => {
      sharedList.value = (await getRecordings(true)).data;
    };
    if (oauthClient === undefined) {
      throw new Error('Must provide "oauthClient" into component.');
    }

    const loginText = ref("Login");
    const checkLogin = async () => {
      if (oauthClient.isLoggedIn) {
        loginText.value = "Logout";
        loadConfiguration();
        if (sharedList.value.length === 0) {
        getShared();
        }
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
    router.afterEach((guard) => {
      if (guard.path.includes("spectrogram")) {
        activeTab.value = "spectrogram";
      }
    });
    const activeTab = ref(route.path.includes("spectrogram") ? "spectrogram" : "recordings");
    const containsSpectro = computed(() => route.path.includes("spectrogram"));
    watch(containsSpectro, () => {
      if (route.path.includes("spectrogram")) {
        activeTab.value = "spectrogram";
      }
    });

    const isAdmin = computed(() => configuration.value.is_admin);
    const isNaBat = computed(() => (route.path.includes('nabat')));
    return {
      oauthClient,
      containsSpectro,
      loginText,
      logInOrOut,
      activeTab,
      nextShared,
      sideTab,
      isAdmin,
      isNaBat,
     };
  },
});
</script>

<template>
  <v-app id="app">
    <v-app-bar app>
      <v-tabs
        v-if="oauthClient.isLoggedIn && activeTab && !isNaBat"
        v-model="activeTab"
        fixed-tabs
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
        <v-tab
          v-show="containsSpectro"
          value="spectrogram"
        >
          Spectrogram
        </v-tab>
        <v-tab
          v-show="isAdmin"
          to="/admin"
          value="admin"
        >
          Admin
        </v-tab>
      </v-tabs>
      <h3
        v-if="isNaBat"
        class="mx-3"
      >
        NA Bat Spectrogram Viewer
      </h3>
      <v-spacer />
      <v-tooltip
        v-if="containsSpectro && nextShared !== false"
        bottom
      >
        <template #activator="{ props: subProps }">
          <v-btn
            v-bind="subProps"
            variant="outlined"
            :to="`/recording/${nextShared.id}/spectrogram`"
          >
            Next Shared<v-icon>mdi-chevron-right</v-icon>
          </v-btn>
        </template>
        <span v-if="nextShared">
          <div>
            <b>Name:</b><span>{{ nextShared.name }}</span>
          </div>
          <div>
            <b>Owner:</b><span>{{ nextShared.owner_username }}</span>
          </div>
        </span>
      </v-tooltip>
      <help-system />
      <v-btn
        v-if="!isNaBat"
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

<style >
html {
  overflow-y:hidden;
}
</style>
