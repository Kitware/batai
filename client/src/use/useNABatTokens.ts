import { readonly, ref } from "vue";
import { axiosInstance } from "../api/api";
import { NABAT_PATH_REGEX } from "../constants";

// Force setting of the tokens to happen with the exported setters
const _nabatApiToken = ref("");
const _nabatRefreshToken = ref("");

const nabatApiToken = readonly(_nabatApiToken);
const nabatRefreshToken = readonly(_nabatRefreshToken);

axiosInstance.interceptors.request.use((config) => {
  if (NABAT_PATH_REGEX.test(config.url ?? "") && nabatApiToken.value) {
    config.headers.Authorization = `Bearer ${nabatApiToken.value}`;
  }
  return config;
});

export default function useNABatTokens() {
  function setApiToken(token: string) {
    _nabatApiToken.value = token;
  }

  function setRefreshToken(token: string) {
    _nabatRefreshToken.value = token;
  }

  return {
    setApiToken,
    setRefreshToken,
    nabatApiToken,
    nabatRefreshToken,
  };
}
