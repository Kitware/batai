<script setup lang="ts">
import { ref, Ref, watch } from 'vue';
import { ScaleOrdinal } from 'd3';
import useState from '@use/useState';

const props = defineProps<{
  colorScale: ScaleOrdinal<string, string, never>,
  otherUsers: string[],
  userEmails: string[],
}>();
const { createColorScale, setSelectedUsers } = useState();

const colorScale = props.colorScale ?? createColorScale(props.userEmails);

const selectedUsers: Ref<string[]> = ref([]);

const deleteChip = (item: string) => {
  const newSelectedUsers = selectedUsers.value.filter((user: string) => user !== item);
  selectedUsers.value = newSelectedUsers;
  setSelectedUsers(selectedUsers.value);
};

watch(selectedUsers, () => {
  setSelectedUsers(selectedUsers.value);
});
</script>

<template>
  <v-dialog max-width="500">
    <template #activator="{ props: modalProps }">
      <v-tooltip>
        <template #activator="{ props: tooltipProps }">
          <v-icon
            v-bind="{ ...modalProps, ...tooltipProps }"
            class="mr-3 mt-3"
            size="25"
            :color="selectedUsers.length === 0 ? '' : 'blue'"
          >
            mdi-account-group
          </v-icon>
        </template>
        Select users to display their annotations
      </v-tooltip>
    </template>
    <template #default="{ isActive }">
      <v-card>
        <v-card-title>
          Other Users
        </v-card-title>
        <v-card-text>
          <v-select
            v-model="selectedUsers"
            :items="otherUsers"
            density="compact"
            label="Other Users"
            multiple
            single-line
            clearable
            variant="outlined"
            closable-chips
            hide-details
          >
            <template #selection="{ item }">
              <v-chip
                closable
                size="x-small"
                :color="colorScale(item.value)"
                text-color="gray"
                @click:close="deleteChip(item.value)"
              >
                {{ item.value.replace(/@.*/, "") }}
              </v-chip>
            </template>
          </v-select>
        </v-card-text>
        <v-card-actions>
          <v-btn
            text="Close"
            @click="isActive.value = false"
          />
        </v-card-actions>
      </v-card>
    </template>
  </v-dialog>
</template>
