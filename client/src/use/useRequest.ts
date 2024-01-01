import { reactive, toRefs } from 'vue';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function getResponseError(error: any) {
  return error?.response?.data || error;
}

export default function useRequest<T>(func: (...args: unknown[]) => Promise<T>) {
  const state = reactive({
    loading: false, // indicates request in progress
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    error: null as any | null, // indicates request failure
    count: 0, // indicates number of successful calls
  });

  async function request(...args: unknown[]): Promise<T> {
    try {
      state.loading = true;
      state.error = null;
      state.count += 1;
      const val = await func(...args);
      state.loading = false;
      return val;
    } catch (err) {
      state.loading = false;
      state.error = getResponseError(err);
      throw err;
    }
  }

  function reset() {
    state.loading = false;
    state.error = null;
    state.count = 0;
  }

  return {
    ...toRefs(state),
    state,
    request,
    reset,
  };
}