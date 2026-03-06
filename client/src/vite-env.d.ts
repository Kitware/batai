/// <reference types="vite/client" />

interface ViteTypeOptions {
  strictImportMetaEnv: unknown
}

interface ImportMetaEnv {
  readonly VITE_APP_API_ROOT: string;
  readonly VITE_APP_SUBPATH?: string;
  // This is not set in development
  readonly VITE_APP_SENTRY_DSN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
