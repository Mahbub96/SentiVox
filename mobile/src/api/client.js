/* client.js — SentiVox API Client with JWT Authorization Interceptor */

import axios from 'axios';

// API Base URL (adjust for local network IP when testing on physical device)
export const API_BASE_URL = 'http://127.0.0.1:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

let authToken = null;

export const setAuthToken = (token) => {
  authToken = token;
};

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

export default client;
