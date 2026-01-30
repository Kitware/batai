import OauthClient from '@resonant/oauth-client';
import { ref } from 'vue';

const CLIENT_ID = 'HSJWFZ2cIpWQOvNyCXyStV9hiOd7DfWeBOCzo4pP';

const redirectUrl = new URL((import.meta.env.VITE_APP_LOGIN_REDIRECT || location.origin) as string);
const baseUrl = new URL(import.meta.env.VITE_APP_OAUTH_API_ROOT as string);
const oauthClient = new OauthClient(baseUrl, CLIENT_ID, { redirectUrl });

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
