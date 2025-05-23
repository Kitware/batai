import { ref, watch } from 'vue';

interface UseJWTTokenOptions {
  token: string;
  warningSeconds: number;
}

export function useJWTToken(options: UseJWTTokenOptions) {
  const { token, warningSeconds } = options;
  const storageKey = 'jwt-expiration';
  const exp = ref<number | null>(null);
  const shouldWarn = ref(false);
  let warningTimeout: ReturnType<typeof setTimeout> | null = null;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  function decodeJWT(token: string): any | null {
    try {
      const payload = token.split('.')[1];
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded);
    } catch (error) {
      console.error('Failed to decode JWT:', error);
      return null;
    }
  }

  function setupWarning(expiration: number) {
    const now = Math.floor(Date.now() / 1000);
    const secondsUntilWarning = expiration - now - warningSeconds;

    if (secondsUntilWarning <= 0) {
      // Immediate warning
      shouldWarn.value = true;
    } else {
      if (warningTimeout) {
        clear();
      }
      warningTimeout = setTimeout(() => {
        shouldWarn.value = true;
      }, secondsUntilWarning * 1000);
    }
  }

  function persistExpiration(expiration: number) {
    const data = { expiration };
    localStorage.setItem(storageKey, JSON.stringify(data));
  }

  function loadPersistedExpiration(): number | null {
    const stored = localStorage.getItem(storageKey);
    if (stored) {
      try {
        const data = JSON.parse(stored);
        if (typeof data.expiration === 'number') {
          return data.expiration;
        }
      } catch (error) {
        console.error('Failed to parse stored expiration:', error);
      }
    }
    return null;
  }

  function initialize() {
    if (!token) {
      return;
    }
    const decoded = decodeJWT(token);
    if (decoded && typeof decoded.exp === 'number') {
      exp.value = decoded.exp;
      persistExpiration(decoded.exp);
      setupWarning(decoded.exp);
    } else {
      console.warn('Token does not have a valid exp field.');
      const persisted = loadPersistedExpiration();
      if (persisted) {
        exp.value = persisted;
        setupWarning(persisted);
      }
    }
  }

  function clear() {
    if (warningTimeout) {
      clearTimeout(warningTimeout);
      warningTimeout = null;
    }
  }

  initialize();

  // Optional: clear storage if you manually call clear
  watch(shouldWarn, (newVal) => {
    if (newVal) {
      localStorage.removeItem(storageKey);
    }
  });

  return {
    exp,
    shouldWarn,
    clear,
  };
}