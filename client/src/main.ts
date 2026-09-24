import "@mdi/font/css/materialdesignicons.css";
import "maplibre-gl/dist/maplibre-gl.css";
import "vuetify/styles";
import * as Sentry from "@sentry/vue";
import { createApp } from "vue";
import { createVuetify } from "vuetify";

import App from "./App.vue";
import oauthClient, { maybeRestoreLogin } from "./plugins/Oauth";
import initRouter from "./router";
import { axiosInstance } from "./api/api";
import { installPrompt } from "./use/prompt-service";
import { NABAT_ENTRYPOINT_PATH_REGEX } from "./constants";

const app = createApp(App);
const Vuetify = createVuetify({
  theme: {
    themes: {
      light: {
        colors: {
          primary: "#1976d2",
          secondary: "#9c27b0",
          warning: "#fb8c00",
          golden: "#b8860b",
        },
      },
    },
  },
});

Sentry.init({
  app,
  // This is only defined in the release build environment
  dsn: import.meta.env.VITE_SENTRY_DSN,
  sendDefaultPii: true,
});

// The NABat recording entrypoint (Django's target for NABat's own Keycloak redirect) carries
// its own `code`/`state` query params, unrelated to this app's login. oauth-client's
// maybeRestoreLogin() strips those from the URL unconditionally, assuming they're its own
// callback, so skip it entirely on this one route - it doesn't rely on this app's OAuth anyway.
const isNabatRecordingEntrypoint = NABAT_ENTRYPOINT_PATH_REGEX.test(
  window.location.pathname,
);
const restoreLogin = isNabatRecordingEntrypoint
  ? Promise.resolve()
  : maybeRestoreLogin();

restoreLogin.then(() => {
  /*
  The router must not be initialized until after the oauth flow is complete, because it
  stores the initial history state at the time of its construction, and we don't want it
  to capture that initial state until after we remove any OAuth response params from the URL.
  */
  const router = initRouter();

  Sentry.addIntegration(Sentry.browserTracingIntegration({ router }));

  app.use(router);
  app.use(Vuetify);
  app.provide("oauthClient", oauthClient);
  Object.assign(axiosInstance.defaults.headers.common, oauthClient.authHeaders);
  app.mount("#app");
  installPrompt(app);
});
