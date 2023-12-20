import OauthClient from '@girder/oauth-client';
import { ref } from 'vue';

const redirectUrl = new URL((import.meta.env.VUE_APP_LOGIN_REDIRECT || location.origin) as string);
const baseUrl = new URL(import.meta.env.VUE_APP_OAUTH_API_ROOT as string);
const clientId = import.meta.env.VUE_APP_OAUTH_CLIENT_ID as string;
const oauthClient = new OauthClient(baseUrl, clientId, { redirectUrl });

export const loggedIn = ref(oauthClient.isLoggedIn);

export async function logout() {
  await oauthClient?.logout();
  loggedIn.value = false;
}

export async function maybeRestoreLogin() {
  await oauthClient.maybeRestoreLogin();
  loggedIn.value = oauthClient.isLoggedIn;
}

export default oauthClient;