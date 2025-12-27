// Typed environment variables for the web app runtime/build.
declare namespace NodeJS {
  interface ProcessEnv {
    NEXT_PUBLIC_API_BASE?: string;
    API_INTERNAL_BASE?: string;
  }
}
