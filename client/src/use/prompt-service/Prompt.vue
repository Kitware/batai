<script lang="ts">
import {
  ref, Ref, watch, nextTick, defineComponent,
} from 'vue';

export default defineComponent({
  name: 'Prompt',
  props: {},
  setup() {
    const show = ref(false);
    const title = ref('');
    const text: Ref<string | string[]> = ref('');
    const positiveButton = ref('Confirm');
    const negativeButton = ref('Cancel');
    const selected = ref('positive');
    const confirm = ref(false);
    const value: Ref<string | boolean | number| null> = ref(null);

    /**
     * Placeholder resolver function.  Wrapped in object so that
     * its reference isn't changed on reassign.
     */
    const functions = {
      resolve(val: boolean | number | string | null) {
        return val;
      },
    };

    const positive: Ref<HTMLFormElement | null> = ref(null);
    const negative: Ref<HTMLFormElement | null> = ref(null);
    const input: Ref<HTMLFormElement | null> = ref(null);

    async function clickPositive() {
      show.value = false;
        functions.resolve(value.value);
    }

    async function clickNegative() {
      show.value = false;
        functions.resolve(null);
    }

    async function select() {
      if (selected.value === 'positive') {
        clickPositive();
      } else {
        clickNegative();
      }
    }

    async function focusPositive() {
      if (positive.value) {
        selected.value = 'positive';
      }
    }

    async function focusNegative() {
      if (negative.value) {
        selected.value = 'negative';
      }
    }


    watch(show, async (val) => {
      if (!val) {
          functions.resolve(null);
      }
    });

    return {
      show,
      title,
      text,
      positiveButton,
      negativeButton,
      selected,
      confirm,
      functions,
      value,
      clickPositive,
      clickNegative,
      select,
      input,
      positive,
      negative,
      focusPositive,
      focusNegative,
    };
  },
});
</script>

<template>
  <v-dialog
    v-model="show"
    max-width="400"
  >
    <v-card>
      <v-card-title
        v-if="title"
        class="title"
      >
        {{ title }}
      </v-card-title>
      <v-card-text v-if="Array.isArray(text)">
        <div
          v-for="(item, key) in text"
          :key="key"
        >
          {{ item }}
        </div>
      </v-card-text>
      <v-card-text v-else>
        <p>{{ text }}</p>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn
          v-if="confirm && negativeButton && negativeButton.length"
          ref="negative"
          text
          @click="clickNegative"
        >
          {{ negativeButton }}
        </v-btn>
        <v-btn
          ref="positive"
          color="primary"
          text
          @click="clickPositive"
        >
          {{ positiveButton }}
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>
