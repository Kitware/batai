import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router';
import HelpPage from '../views/HelpPage.vue';
import Recordings from '../views/Recordings.vue';
import Spectrogram from '../views/Spectrogram.vue';
import Login from '../views/Login.vue';

import oauthClient from '../plugins/Oauth';
import Admin from '../views/Admin.vue';
import NABatRecording from '../views/NABat/NABatRecording.vue';
import NABatSpectrogram from '../views/NABat/NABatSpectrogram.vue';

function beforeEach(
  to: RouteLocationNormalized,
  _: RouteLocationNormalized,
  next: (route?: string) => void,
) {
  if (to.path.startsWith('/nabat/')) {
    next();
    return;
  }
  if (!oauthClient.isLoggedIn && to.name !== 'Login') {
    next('/login');
    return;
  }  if (oauthClient.isLoggedIn && to.name === 'Login') {
    next('/');
  }
  next();
}
const subpath = import.meta.env.VITE_APP_SUBPATH?.replace(/\/+$/, '');
const routerBase = subpath ? `/${subpath}/` : '/';


function routerInit(){
  const router  = createRouter({
    base: routerBase,
    history: createWebHistory(routerBase),
    routes: [
      {
        path: '/',
        component: Recordings,
      },
      {
        path: '/login',
        name: 'Login',
        component: Login,
      },
      {
        path: '/help',
        component: HelpPage,
      },
      {
        path: '/admin',
        component: Admin,
      },
      {
        path: '/recording/:id/spectrogram',
        component: Spectrogram,
        props: true,
      },
      {
        path: '/nabat/:id/spectrogram',
        component: NABatSpectrogram,
        props: (route) => ({
          id: route.params.id,
          apiToken: route.query.apiToken,
        }),
      },
      {
        path: '/nabat/:recordingId/',
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
