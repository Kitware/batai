<script lang="ts">
import {
  computed,
  defineComponent,
  ref,
  type Ref,
  onMounted,
  watch,
  type PropType,
} from 'vue';
import { getRecordings, type Recording, type FileAnnotation, type RecordingListParams } from '../api/api';
import MapLocation from '@components/MapLocation.vue';
import RecordingInfoDisplay from '@components/RecordingInfoDisplay.vue';
import RecordingAnnotationSummary from '@components/RecordingAnnotationSummary.vue';
import useState from '@use/useState';

const SERVER_SORT_FIELDS: readonly string[] = ['id', 'name', 'created', 'modified', 'recorded_date', 'owner_username'];

export interface RecordingTableHeader {
  title: string;
  key: string;
  value: string;
  sortable?: boolean;
  valueFn?: (item: Recording) => boolean | string | number;
}

export default defineComponent({
  name: 'RecordingTable',
  components: {
    MapLocation,
    RecordingInfoDisplay,
    RecordingAnnotationSummary,
  },
  props: {
    variant: {
      type: String as PropType<'my' | 'shared'>,
      required: true,
    },
    tags: {
      type: Array as PropType<string[] | undefined>,
      default: undefined,
    },
    editRecording: {
      type: Function as PropType<(item: Recording) => void>,
      default: undefined,
    },
    openDeleteRecordingDialog: {
      type: Function as PropType<(recording: Recording) => void>,
      default: undefined,
    },
    /** When set, list requests include this WGS84 bbox [minLon, minLat, maxLon, maxLat]. */
    bboxFilter: {
      type: Array as unknown as PropType<[number, number, number, number] | null>,
      default: null,
    },
  },
  emits: ['update:tags'],
  setup(props, { emit, expose }) {
    const {
      configuration,
      showSubmittedRecordings,
      currentUser,
      currentRecordingId,
      recordingTagList,
      filterTags,
      sharedFilterTags,
      saveFilterTags,
      recordingList,
      sharedList,
    } = useState();

    const sortBy: Ref<{ key: string; order: 'asc' | 'desc' }[]> = ref([{ key: 'created', order: 'desc' }]);
    const loading = ref(false);
    const totalCount = ref(0);
    let intervalRef: number | null = null;

    const filterTagsModel = computed({
      get: () => {
        if (props.tags !== undefined) return props.tags;
        return props.variant === 'my' ? filterTags.value : sharedFilterTags.value;
      },
      set: (v: string[]) => {
        if (props.tags !== undefined) {
          emit('update:tags', v);
          return;
        }
        if (props.variant === 'my') filterTags.value = v;
        else sharedFilterTags.value = v;
      },
    });

    const items = computed(() => (props.variant === 'my' ? recordingList.value : sharedList.value));

    const recordingTagOptions = computed(() =>
      recordingTagList.value.filter(Boolean)
    );

    const defaultColumnVisibilityMy: Record<string, boolean> = {
      name: true,
      annotation: true,
      owner_username: true,
      tag_text: true,
      recorded_date: true,
      public: true,
      grts_cell_id: true,
      comments: true,
      userAnnotations: true,
      edit: true,
      submitted: true,
      submittedLabel: true,
      userMadeAnnotations: true,
    };

    const defaultColumnVisibilityShared: Record<string, boolean> = {
      name: true,
      annotation: true,
      owner_username: false,
      tag_text: true,
      recorded_date: true,
      public: false,
      grts_cell_id: true,
      comments: true,
      userAnnotations: true,
      edit: true,
      submitted: true,
      submittedLabel: true,
      userMadeAnnotations: false,
    };
    function getStorageKey(variant: 'my' | 'shared'): string {
      const user = currentUser.value || 'anonymous';
      return `recordingTableColumns_${variant}_${user}`;
    }

    function loadColumnVisibility(variant: 'my' | 'shared'): Record<string, boolean> {
      const base = variant === 'my' ? defaultColumnVisibilityMy : defaultColumnVisibilityShared;
      if (typeof window === 'undefined') {
        return { ...base };
      }
      try {
        const raw = window.localStorage.getItem(getStorageKey(variant));
        if (!raw) {
          return { ...base };
        }
        const parsed = JSON.parse(raw) as Record<string, boolean>;
        return { ...base, ...parsed };
      } catch {
        return { ...base };
      }
    }

    const columnVisibilityMy = ref<Record<string, boolean>>(loadColumnVisibility('my'));
    const columnVisibilityShared = ref<Record<string, boolean>>(loadColumnVisibility('shared'));

    const baseHeadersMy: RecordingTableHeader[] = [
      { title: 'Name', key: 'name', value: 'name', sortable: SERVER_SORT_FIELDS.includes('name') },
      { title: 'Annotation', key: 'annotation', value: 'annotation', sortable: SERVER_SORT_FIELDS.includes('annotation') },
      { title: 'Owner', key: 'owner_username', value: 'owner_username', sortable: SERVER_SORT_FIELDS.includes('owner_username') },
      { title: 'Tags', key: 'tag_text', value: 'tag_text', sortable: SERVER_SORT_FIELDS.includes('tag_text') },
      { title: 'Recorded Date', key: 'recorded_date', value: 'recorded_date', sortable: SERVER_SORT_FIELDS.includes('recorded_date') },
      { title: 'Public', key: 'public', value: 'public', sortable: SERVER_SORT_FIELDS.includes('public') },
      { title: 'GRTS CellId', key: 'grts_cell_id', value: 'grts_cell_id', sortable: SERVER_SORT_FIELDS.includes('grts_cell_id') },
      { title: 'Details', key: 'comments', value: 'comments', sortable: SERVER_SORT_FIELDS.includes('comments') },
      { title: 'User Pulse Annotations', key: 'userAnnotations', value: 'userAnnotations', sortable: SERVER_SORT_FIELDS.includes('userAnnotations') },
      { title: 'Edit', key: 'edit', value: 'edit', sortable: false },
    ];

    const baseHeadersShared: RecordingTableHeader[] = [
      { title: 'Name', key: 'name', value: 'name', sortable: SERVER_SORT_FIELDS.includes('name') },
      { title: 'Annotation', key: 'annotation', value: 'annotation', sortable: SERVER_SORT_FIELDS.includes('annotation') },
      { title: 'Owner', key: 'owner_username', value: 'owner_username', sortable: SERVER_SORT_FIELDS.includes('owner_username') },
      { title: 'Tags', key: 'tag_text', value: 'tag_text', sortable: SERVER_SORT_FIELDS.includes('tag_text') },
      { title: 'Recorded Date', key: 'recorded_date', value: 'recorded_date', sortable: SERVER_SORT_FIELDS.includes('recorded_date') },
      { title: 'Public', key: 'public', value: 'public', sortable: SERVER_SORT_FIELDS.includes('public') },
      { title: 'GRTS CellId', key: 'grts_cell_id', value: 'grts_cell_id', sortable: SERVER_SORT_FIELDS.includes('grts_cell_id') },
      { title: 'Details', key: 'comments', value: 'comments', sortable: SERVER_SORT_FIELDS.includes('comments') },
      { title: 'Annotated by Me', key: 'userMadeAnnotations', value: 'userMadeAnnotations', sortable: SERVER_SORT_FIELDS.includes('userMadeAnnotations') },
    ];

    const ORDER_MY = ['name', 'tag_text', 'grts_cell_id', 'submitted', 'recorded_date', 'owner_username', 'public', 'edit'];
    const ORDER_SHARED = ['name', 'tag_text', 'grts_cell_id', 'submitted', 'recorded_date', 'public', 'userMadeAnnotations', 'owner_username'];

    function getActiveColumnVisibility(): Record<string, boolean> {
      return props.variant === 'my' ? columnVisibilityMy.value : columnVisibilityShared.value;
    }

    function isColumnVisible(key: string): boolean {
      if (key === 'name' || key === 'edit') {
        return true;
      }
      const visibility = getActiveColumnVisibility();
      if (key in visibility) return visibility[key];
      return true;
    }

    function saveColumnVisibility(variant: 'my' | 'shared') {
      if (typeof window === 'undefined') {
        return;
      }
      const key = getStorageKey(variant);
      const visibility = variant === 'my' ? columnVisibilityMy.value : columnVisibilityShared.value;
      try {
        window.localStorage.setItem(key, JSON.stringify(visibility));
      } catch {
        // ignore storage errors
      }
    }

    function setColumnVisible(key: string, value: boolean) {
      if (key === 'name' || key === 'edit') {
        return;
      }
      const targetRef = props.variant === 'my' ? columnVisibilityMy : columnVisibilityShared;
      targetRef.value = { ...targetRef.value, [key]: value };
      saveColumnVisibility(props.variant);
    }

    const rawHeaders = computed((): RecordingTableHeader[] => {
      const base = props.variant === 'my' ? baseHeadersMy : baseHeadersShared;
      let h = [...base];
      if (configuration.value.mark_annotations_completed_enabled) {
        h = h.filter((x) => !['comments', 'details', 'annotation', 'userAnnotations'].includes(x.key));
        h.push({ title: 'Submission Status', key: 'submitted', value: 'submitted' });
        if (showSubmittedRecordings.value) {
          h.push({ title: 'My Submitted Label', key: 'submittedLabel', value: 'submittedLabel' });
        }
      }
      const order = props.variant === 'my' ? ORDER_MY : ORDER_SHARED;
      h.sort((a, b) => {
        const ia = order.indexOf(a.key);
        const ib = order.indexOf(b.key);
        if (ia === -1 && ib === -1) return 0;
        if (ia === -1) return 1;
        if (ib === -1) return -1;
        return ia - ib;
      });
      return h;
    });

    const headers = computed((): RecordingTableHeader[] => rawHeaders.value.filter((header) => isColumnVisible(header.key)));

    function buildParams(options: { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }): RecordingListParams {
      const sortByFirst = options.sortBy?.[0];
      const sortKey = (sortByFirst?.key && (SERVER_SORT_FIELDS as readonly string[]).includes(sortByFirst.key))
        ? sortByFirst.key
        : 'created';
      const sort_direction = sortByFirst?.order === 'asc' ? 'asc' : 'desc';
      const tags = filterTagsModel.value;
      const params: RecordingListParams = {
        page: options.page,
        limit: options.itemsPerPage,
        sort_by: sortKey as RecordingListParams['sort_by'],
        sort_direction,
        tags: tags.length ? tags : undefined,
        exclude_submitted: configuration.value.mark_annotations_completed_enabled && !showSubmittedRecordings.value ? true : undefined,
      };
      if (props.variant === 'shared') {
        params.public = true;
      }
      const bf = props.bboxFilter;
      if (bf && bf.length === 4 && bf.every((n) => Number.isFinite(n))) {
        params.bbox = bf;
      }
      return params;
    }

    const lastOptions = ref<{ page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }>({ page: 1, itemsPerPage: 20 });

    async function fetchRecordings(options: { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] }) {
      const opts = { ...options, sortBy: options.sortBy ?? sortBy.value };
      lastOptions.value = opts;
      loading.value = true;
      try {
        const res = await getRecordings(props.variant === 'shared', buildParams(opts));
        const list = res.data.items;
        const count = res.data.count;
        if (props.variant === 'my') {
          recordingList.value = list;
          let missingSpectro = false;
          for (let i = 0; i < list.length; i += 1) {
            if (!list[i].hasSpectrogram) {
              missingSpectro = true;
              break;
            }
          }
          if (missingSpectro && intervalRef === null) {
            intervalRef = setInterval(() => fetchRecordings(lastOptions.value), 5000);
          } else if (!missingSpectro && intervalRef !== null) {
            clearInterval(intervalRef);
            intervalRef = null;
          }
        } else {
          sharedList.value = list;
        }
        totalCount.value = count;
      } finally {
        loading.value = false;
      }
    }

    function getItemLocation(item: Recording): { x: number; y: number } | undefined {
      if (configuration.value.mark_annotations_completed_enabled) {
        return undefined;
      }
      if (item.recording_location) {
        return {
          x: item.recording_location.coordinates[0],
          y: item.recording_location.coordinates[1],
        };
      }
      return undefined;
    }

    function getRowProps(data: { item: Recording }) {
      return { class: { 'current-recording-row': data.item?.id === currentRecordingId.value } };
    }

    function currentUserSubmissionStatus(recording: Recording): number {
      const userAnnotations = recording.fileAnnotations.filter((a: FileAnnotation) => (
        a.owner === currentUser.value && a.model === 'User Defined'
      ));
      if (userAnnotations.find((a: FileAnnotation) => a.submitted)) return 1;
      return userAnnotations.length ? 0 : -1;
    }

    function currentUserSubmissionLabel(recording: Recording): string {
      const ann = recording.fileAnnotations.find((a: FileAnnotation) => (
        a.owner === currentUser.value && a.submitted
      ));
      return ann?.species?.[0]?.species_code ?? '';
    }

    function addTagToFilter(tag: string) {
      if (!filterTagsModel.value.includes(tag)) {
        filterTagsModel.value = [...filterTagsModel.value, tag];
      }
    }

    type OptionsPayload = { page: number; itemsPerPage: number; sortBy?: { key: string; order: string }[] };
    function onUpdateOptions(options: OptionsPayload) {
      fetchRecordings(options);
    }

    function onUpdateSortBy(e: { key: string; order: 'asc' | 'desc' }[]) {
      sortBy.value = e;
    }

    const tableClass = computed(() => (props.variant === 'my' ? 'my-recordings' : 'shared-recordings'));

    const showTotalCount = computed(() => (
      totalCount.value > 0
      && configuration.value.mark_annotations_completed_enabled
      && (props.variant === 'shared' || configuration.value.is_admin || configuration.value.non_admin_upload_enabled)
    ));

    watch(filterTagsModel, () => {
      fetchRecordings(lastOptions.value);
      saveFilterTags();
    }, { deep: true });

    watch(showSubmittedRecordings, () => {
      fetchRecordings(lastOptions.value);
    });

    watch(
      () => props.bboxFilter,
      () => {
        fetchRecordings(lastOptions.value);
      },
      { deep: true }
    );

    onMounted(() => {
      fetchRecordings({ page: 1, itemsPerPage: 20 });
    });

    expose({ refetch: () => fetchRecordings(lastOptions.value) });

    return {
      sortBy,
      headers,
      items,
      totalCount,
      loading,
      filterTagsModel,
      recordingTagOptions,
      configuration,
      showSubmittedRecordings,
      currentRecordingId,
      getItemLocation,
      getRowProps,
      currentUserSubmissionStatus,
      currentUserSubmissionLabel,
      addTagToFilter,
      onUpdateOptions,
      onUpdateSortBy,
      tableClass,
      showTotalCount,
      rawHeaders,
      isColumnVisible,
      setColumnVisible,
    };
  },
});
</script>

<template>
  <v-data-table-server
    v-model:sort-by="sortBy"
    :headers="headers"
    :items="items"
    :items-length="totalCount"
    :loading="loading"
    :row-props="getRowProps"
    items-per-page="20"
    :items-per-page-options="[{ value: 10, title: '10' }, { value: 20, title: '20' }, { value: 50, title: '50' }, { value: 100, title: '100' }]"
    density="compact"
    class="elevation-1"
    :class="tableClass"
    @update:options="onUpdateOptions"
    @update:sort-by="onUpdateSortBy"
  >
    <template #top>
      <div
        class="d-flex align-center"
        max-height="100px"
      >
        <v-autocomplete
          v-model="filterTagsModel"
          :items="recordingTagOptions"
          label="Filter recordings by tags"
          autocomplete="off"
          multiple
          chips
          closable-chips
          clearable
          class="flex-grow-1"
        />
        <v-menu>
          <template #activator="{ props }">
            <v-btn
              v-bind="props"
              icon
              class="ml-2"
              variant="text"
            >
              <v-icon>mdi-cog</v-icon>
            </v-btn>
          </template>
          <v-list>
            <v-list-subheader>Column visibility</v-list-subheader>
            <v-list-item
              v-for="header in rawHeaders"
              :key="header.key"
              @click.stop
            >
              <v-checkbox
                :model-value="isColumnVisible(header.key)"
                :label="header.title"
                :disabled="header.key === 'name' || header.key === 'edit'"
                hide-details
                density="compact"
                @update:model-value="(val) => setColumnVisible(header.key, !!val)"
              />
            </v-list-item>
          </v-list>
        </v-menu>
      </div>
    </template>

    <template
      v-if="variant === 'my' && editRecording && openDeleteRecordingDialog"
      #item.edit="{ item }"
    >
      <v-icon @click="editRecording(item)">
        mdi-pencil
      </v-icon>
      <v-icon
        color="error"
        @click="openDeleteRecordingDialog(item)"
      >
        mdi-delete
      </v-icon>
    </template>

    <template #item.name="{ item }">
      <router-link
        v-if="item.hasSpectrogram || variant === 'shared'"
        :to="`/recording/${item.id.toString()}/spectrogram`"
      >
        {{ item.name }}
      </router-link>
      <div v-else>
        {{ item.name }}
        <v-tooltip bottom>
          <template #activator="{ props: subProps }">
            <span v-bind="subProps">
              <v-icon color="warning">mdi-alert</v-icon>
              <v-icon>mdi-sync mdi-spin</v-icon>
            </span>
          </template>
          <span>Waiting for spectrogram to be computed</span>
        </v-tooltip>
      </div>
    </template>

    <template #item.annotation="{ item }">
      <RecordingAnnotationSummary :file-annotations="item.fileAnnotations" />
    </template>

    <template #item.tag_text="{ item }">
      <span v-if="item.tags_text">
        <v-tooltip text="Add to filter">
          <template #activator="{ props: tooltipProps }">
            <v-chip
              v-for="tag in item.tags_text"
              :key="tag"
              size="small"
              class="tag-filter-chip"
              v-bind="tooltipProps"
              @click.stop="addTagToFilter(tag)"
            >
              {{ tag }}
            </v-chip>
          </template>
        </v-tooltip>
      </span>
    </template>

    <template #item.recorded_date="{ item }">
      {{ item.recorded_date }} {{ item.recorded_time }}
    </template>

    <template #item.grts_cell_id="{ item }">
      <span class="d-flex align-center gap-1">
        <div>{{ item.grts_cell_id ?? '—' }}</div>
        <v-menu
          v-if="item.recording_location || (configuration.mark_annotations_completed_enabled && item.grts_cell_id)"
          open-on-hover
          :close-on-content-click="false"
        >
          <template #activator="{ props }">
            <v-icon 
              v-bind="props" 
              color="primary" 
              class="ml-2"
              size="x-large"
            >
              mdi-map
            </v-icon>
          </template>
          <v-card>
            <map-location
              :editor="false"
              :size="{ width: 400, height: 400 }"
              :location="getItemLocation(item)"
              :grts-cell-id="configuration.mark_annotations_completed_enabled ? item.grts_cell_id || undefined : undefined"
            />
          </v-card>
        </v-menu>
      </span>
    </template>

    <template #item.comments="{ item }">
      <v-menu
        v-if="item.comments !== undefined"
        open-on-click
        :close-on-content-click="false"
      >
        <template #activator="{ props }">
          <v-icon v-bind="props">
            mdi-information-outline
          </v-icon>
        </template>
        <recording-info-display
          :recording-info="item"
          :minimal-metadata="configuration.mark_annotations_completed_enabled && variant === 'my'"
          disable-button
        />
      </v-menu>
    </template>

    <template #item.public="{ item }">
      <v-icon
        v-if="item.public"
        color="success"
      >
        mdi-check
      </v-icon>
      <v-icon
        v-else
        color="error"
      >
        mdi-close
      </v-icon>
    </template>

    <template
      v-if="variant === 'shared'"
      #item.userMadeAnnotations="{ item }"
    >
      <v-icon
        v-if="item.userMadeAnnotations"
        color="success"
      >
        mdi-check
      </v-icon>
      <v-icon
        v-else
        color="error"
      >
        mdi-close
      </v-icon>
    </template>

    <template
      v-if="configuration.mark_annotations_completed_enabled"
      #item.submitted="{ item }"
    >
      <v-tooltip v-if="currentUserSubmissionStatus(item) === 1">
        <template #activator="{ props }">
          <v-icon
            v-bind="props"
            color="success"
          >
            mdi-check
          </v-icon>
        </template>
        You have submitted an annotation for this recording
      </v-tooltip>
      <v-tooltip v-else-if="currentUserSubmissionStatus(item) === 0">
        <template #activator="{ props }">
          <v-icon
            v-bind="props"
            color="warning"
          >
            mdi-circle-outline
          </v-icon>
        </template>
        You have created an annotation, but it has not been submitted
      </v-tooltip>
      <v-tooltip v-else>
        <template #activator="{ props }">
          <v-icon
            v-bind="props"
            color="error"
          >
            mdi-close
          </v-icon>
        </template>
        You have not created an annotation for this recording
      </v-tooltip>
    </template>
    <template
      v-if="configuration.mark_annotations_completed_enabled && showSubmittedRecordings"
      #item.submittedLabel="{ item }"
    >
      {{ currentUserSubmissionLabel(item) }}
    </template>
  </v-data-table-server>
</template>

<style scoped>
.tag-filter-chip {
  cursor: pointer;
}
</style>
