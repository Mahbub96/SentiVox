/* client.js — SentiVox API Client with JWT Authorization Interceptor */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

// API Base URL — Configurable for different environments
// For local dev:   http://10.0.2.2:8000 (Android emulator)
//                  http://localhost:8000 (iOS simulator)
// For production:  https://your-server.com
const DEFAULT_BASE_URL = __DEV__
  ? 'http://10.0.2.2:8000'
  : 'https://your-server.com';

export const API_BASE_URL = DEFAULT_BASE_URL;

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30s timeout (inference can be slow on CPU)
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
      // Token expired — clear auth state and let the app redirect to login
      authToken = null;
    }

    return Promise.reject(error);
  }
);

export default client;
