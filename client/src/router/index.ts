import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router';
import HomePage from '../views/HomePage.vue';
import Recordings from '../views/Recordings.vue';
import Spectrogram from '../views/Spectrogram.vue';
import Login from '../views/Login.vue';

import oauthClient from '../plugins/Oauth';
import Admin from '../views/Admin.vue';
import NABatAcousticBatch from '../views/NABatAcousticBatch.vue';
import NABatSpectrogram from '../views/NABatSpectrogram.vue';

function beforeEach(
  to: RouteLocationNormalized,
  _: RouteLocationNormalized,
  next: (route?: string) => void,
) {
  if (!oauthClient.isLoggedIn && to.name !== 'Login') {
    next('/login');
    return;
  }  if (oauthClient.isLoggedIn && to.name === 'Login') {
    next('/');
  }
  next();
}


function routerInit(){
  const router  = createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/',
        component: HomePage,
      },
      {
        path: '/login',
        name: 'Login',
        component: Login,
      },
      {
        path: '/recordings',
        component: Recordings,
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
        props: true,
      },

      {
        path: '/nabat/:batchId/',
        component: NABatAcousticBatch,
        props: (route) => ({
          batchId: parseInt(route.params.batchId as string, 10),
          apiToken: route.query.apiToken,
        }),
      },

    ],
  });
  router.beforeEach(beforeEach);
  return router;
}

export default routerInit;
