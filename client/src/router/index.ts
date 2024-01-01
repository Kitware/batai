import { createRouter, createWebHistory, RouteLocationNormalized } from 'vue-router';
import HomePage from '../views/HomePage.vue';
import Recordings from '../views/Recordings.vue';

// import oauthClient from '../plugins/Oauth';

function beforeEach(
  to: RouteLocationNormalized,
  _: RouteLocationNormalized,
  next: (route?: string) => void,
) {
  // if (!oauthClient.isLoggedIn && to.name !== '/') {
  //   next('/');
  // }
  // if (oauthClient.isLoggedIn && to.name === '/') {
  //   next('/');
  // }
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
        path: '/recordings',
        component: Recordings,
      },
    ],
  });
  router.beforeEach(beforeEach);
  return router;
}

export default routerInit;
