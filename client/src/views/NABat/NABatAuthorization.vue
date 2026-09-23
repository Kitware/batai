<script setup lang="ts">
import { onMounted, ref } from "vue";
import { postNABatAuth } from "@/api/NABatApi";
import useState from "@/use/useState";
import { useRouter } from "vue-router";

const { setNabatApiToken, setNabatRefreshToken } = useState();

const props = defineProps<{
  iss: string;
  code: string;
  recordingId: string;
  surveyEventId: string;
}>();

const router = useRouter();

const loading = ref(false);
const message = ref("");

async function initiateTokenExchange() {
  loading.value = true;
  try {
    const exchangeData = await postNABatAuth(
      props.recordingId,
      props.surveyEventId,
      props.iss,
      props.code,
    );
    if (exchangeData["access_token"] && exchangeData["refresh_token"]) {
      setNabatApiToken(exchangeData["access_token"]);
      setNabatRefreshToken(exchangeData["refresh_token"]);
      // Redirect to the nabat recording page
      router.push(
        `/nabat/${props.recordingId}/?surveyEventId=${props.surveyEventId}`,
      );
    }
  } catch {
    message.value = "Failed to authorize with NABat.";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => initiateTokenExchange());
</script>

<template>
  <v-card>
    <v-card-text>
      <v-row dense>
        <v-spacer />
        <v-col justify="center" cols="auto">
          <v-progress-circular
            v-if="loading"
            indeterminate
            :size="256"
            :width="30"
            color="primary"
          >
            Loading...
          </v-progress-circular>
          <v-banner v-else>
            <v-banner-text>{{ message }}</v-banner-text>
          </v-banner>
        </v-col>
        <v-spacer />
      </v-row>
    </v-card-text>
  </v-card>
</template>
