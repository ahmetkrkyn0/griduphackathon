/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" ise API yerine ornek veri kullanilir (npm run dev:mock). */
  readonly VITE_USE_MOCKS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
