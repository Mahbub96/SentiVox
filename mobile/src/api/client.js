/* client.js — SentiVox API Client with JWT Authorization Interceptor */

import axios from 'axios';

// ─── Production Server ──────────────────────────────────────────
// Your Oracle Cloud server at 144.24.142.3
const PRODUCTION_URL = 'http://144.24.142.3:8000';

// For local development on Android emulator: 'http://10.0.2.2:8000'
// For local development on physical device: 'http://192.168.1.X:8000'
const DEV_URL = 'http://10.0.2.2:8000';

let currentBaseUrl = __DEV__ ? DEV_URL : PRODUCTION_URL;

export const setBaseUrl = (url) => {
  if (url) {
    currentBaseUrl = url;
    client.defaults.baseURL = url;
  }
};

export const getBaseUrl = () => currentBaseUrl;

const client = axios.create({
  baseURL: currentBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60s timeout — inference can be slow on CPU-only server
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
};

export const getAuthToken = () => authToken;

// Request Interceptor: Attach Bearer JWT token if available
client.interceptors.request.use(
  (config) => {
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 (token expired) globally
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // If we get a 401 and haven't retried yet, the token might be expired
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      authToken = null;
    }

    return Promise.reject(error);
  }
);

export default client;
