const defaultApiBaseUrl = 'http://localhost:8000';

export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl;

const configuredWsBaseUrl = import.meta.env.VITE_WS_BASE_URL;
const derivedWsBaseUrl = API_BASE_URL.replace(/^http/i, 'ws');

export const WS_BASE_URL = configuredWsBaseUrl ?? derivedWsBaseUrl;
