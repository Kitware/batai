import '@mdi/font/css/materialdesignicons.css';
import 'vuetify/styles';
import * as Sentry from '@sentry/vue';
import { createApp, } from 'vue';
import { createVuetify } from 'vuetify';

import App from './App.vue';
import oauthClient, { maybeRestoreLogin } from './plugins/Oauth';
import initRouter from './router';
import { axiosInstance } from './api/api';
import { installPrompt } from './use/prompt-service';

// This is only defined in the release build environment
const SENTRY_DSN = import.meta.env.VITE_APP_SENTRY_DSN as string | undefined;

const app = createApp(App);
const Vuetify = createVuetify({});

Sentry.init({
  app,
  dsn: SENTRY_DSN,
  sendDefaultPii: true,
});

maybeRestoreLogin().then(() => {
  /*
  The router must not be initialized until after the oauth flow is complete, because it
  stores the initial history state at the time of its construction, and we don't want it
  to capture that initial state until after we remove any OAuth response params from the URL.
  */
  const router = initRouter();

  Sentry.addIntegration(Sentry.browserTracingIntegration({ router }));

  app.use(router);
  app.use(Vuetify);
  app.provide('oauthClient', oauthClient);
  Object.assign(axiosInstance.defaults.headers.common, oauthClient.authHeaders);
  app.mount('#app');
  installPrompt(app);
});
