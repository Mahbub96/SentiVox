/* client.js — SentiVox API Client with JWT Authorization Interceptor */

import axios from 'axios';

// API Base URL — Configurable for different environments
// For local dev:   http://10.0.2.2:8000 (Android emulator)
//                  http://192.168.1.X:8000 (Physical device local network)
// For production:  https://sentivox-api.example.com
let currentBaseUrl = __DEV__
  ? 'http://10.0.2.2:8000'
  : 'http://10.0.2.2:8000';

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
  timeout: 30000, // 30s timeout for audio inference
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

