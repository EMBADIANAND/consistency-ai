/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Overrides the API origin when the SPA is hosted separately from the API. */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
