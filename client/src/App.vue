<script lang="ts">
import { isAxiosError } from 'axios';
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
    const activeTab = ref(route.path.includes("spectrogram") ? "spectrogram" : "recordings");
    const {
      nextShared,
      sharedList,
      sideTab,
      loadConfiguration,
      configuration,
      loadCurrentUser,
      loadFilterTags,
      spectrogramFilename,
    } = useState();
    const getShared = async () => {
      sharedList.value = (await getRecordings(true)).data.items;
    };
    if (oauthClient === undefined) {
      throw new Error('Must provide "oauthClient" into component.');
    }

    const loginText = ref("Login");
    const checkLogin = async () => {
      if (oauthClient.isLoggedIn) {
        loginText.value = "Logout";
        try {
          await loadConfiguration();
          await loadCurrentUser();
          if (sharedList.value.length === 0) {
            getShared();
          }
        } catch (e) {
          // The user is logged in , but a 401 response indicates that their
          // profile has not been verified by an admin.
          if (isAxiosError(e) && e.response?.status === 401) {
            router.push({ path: '/unverified', replace: true });
          } else {
            throw e;
          }
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
    onMounted(async () => {
      await checkLogin();
      loadFilterTags();
    });
    router.afterEach((guard) => {
      if (guard.path.includes("spectrogram")) {
        activeTab.value = "spectrogram";
      }
    });
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
      configuration,
      spectrogramFilename,
    };
  },
});
</script>

<template>
  <v-app id="app">
    <v-app-bar app>
      <v-row
        align="center"
        no-gutters
      >
        <v-col cols="auto">
          <v-tabs
            v-if="oauthClient.isLoggedIn && activeTab && !isNaBat"
            v-model="activeTab"
          >
            <v-tab
              to="/"
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
            <v-tab
              to="/help"
              value="help"
            >
              Help
            </v-tab>
          </v-tabs>
        </v-col>
        <v-col v-if="isNaBat">
          <h3 class="mx-3">
            NABat Spectrogram Viewer
          </h3>
        </v-col>
        <v-col
          v-if="containsSpectro && spectrogramFilename"
          class="app-bar-filename-col"
        >
          <v-tooltip>
            <template #activator="{ props: subProps }">
              <span
                v-bind="subProps"
                class="app-bar-filename text-body2"
                style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
              >
                {{ spectrogramFilename }}
              </span>
            </template>
            <span>{{ spectrogramFilename }}</span>
          </v-tooltip>
        </v-col>
        <v-col
          v-else
          class="app-bar-filename-col"
        />
        <v-col cols="auto">
          <v-tooltip
            v-if="(containsSpectro && nextShared !== false) && !configuration.mark_annotations_completed_enabled"
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
        </v-col>
        <v-col cols="auto">
          <v-row
            align="center"
            justify="end"
          >
            <help-system />
            <v-btn
              v-if="!isNaBat"
              @click="logInOrOut"
            >
              {{ loginText }}
            </v-btn>
          </v-row>
        </v-col>
      </v-row>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<style scoped>
.app-bar-filename-col {
  flex: 1 1 0;
  min-width: 0;
  display: flex;
  justify-content: flex-start;
  align-items: center;
  overflow: hidden;
}
.app-bar-filename {
  display: block;
  min-width: 0;
  width: 100%;
  text-align: left;
  font-weight: bold;
}
</style>
<style>
html {
  overflow-y: hidden;
}
</style>
