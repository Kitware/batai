interface UseNABatSessionOptions {
  sessionId: string;
  warningSeconds?: number;
}

export function useNABatSession(options: UseNABatSessionOptions) {
  const { sessionId, warningSeconds } = options;

  const storageKey = 'nabat_session_id';

  function initialize() {
    localStorage.setItem(storageKey, sessionId);
  }

  return {
    sessionId,
    warningSeconds,
    initialize,
  };
}
