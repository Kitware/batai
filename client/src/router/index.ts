import {
  createRouter,
  createWebHistory,
  type RouteLocationNormalized,
} from "vue-router";
import HelpPage from "../views/HelpPage.vue";
import Recordings from "../views/Recordings.vue";
import Spectrogram from "../views/Spectrogram.vue";
import Login from "../views/Login.vue";
import Unverified from "../views/Unverified.vue";

import oauthClient from "../plugins/Oauth";
import Admin from "../views/Admin.vue";
import NABatRecording from "../views/NABat/NABatRecording.vue";
import NABatSpectrogram from "../views/NABat/NABatSpectrogram.vue";

function beforeEach(
  to: RouteLocationNormalized,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _: RouteLocationNormalized,
) {
  // Allow navigation by returning nothing (equivalent to next())
  if (to.path.startsWith("/nabat/")) {
    return;
  }

  // Redirect by returning the path string (equivalent to next('/login'))
  if (!oauthClient.isLoggedIn && to.name !== "Login") {
    return "/login";
  }

  if (oauthClient.isLoggedIn && to.name === "Login") {
    return "/";
  }

  // Explicitly return for clarity, though returning nothing also works
  return;
}
const subpath = import.meta.env.VITE_SUBPATH?.replace(/\/+$/, "");
const routerBase = subpath ? `/${subpath}/` : "/";

function routerInit() {
  const router = createRouter({
    history: createWebHistory(routerBase),
    routes: [
      {
        path: "/",
        component: Recordings,
      },
      {
        path: "/login",
        name: "Login",
        component: Login,
      },
      {
        path: "/unverified",
        name: "Unverified",
        component: Unverified,
      },
      {
        path: "/help",
        component: HelpPage,
      },
      {
        path: "/admin",
        component: Admin,
      },
      {
        path: "/recording/:id/spectrogram",
        component: Spectrogram,
        props: true,
      },
      {
        path: "/nabat/:id/spectrogram",
        component: NABatSpectrogram,
        props: (route) => ({
          id: route.params.id,
          apiToken: route.query.apiToken,
        }),
      },
      {
        path: "/nabat/:recordingId/",
        component: NABatRecording,
        props: (route) => ({
          recordingId: parseInt(route.params.recordingId as string, 10),
          apiToken: route.query.apiToken,
          surveyEventId: parseInt(route.query.surveyEventId as string, 10),
        }),
      },
    ],
  });
  router.beforeEach(beforeEach);
  return router;
}

export default routerInit;
