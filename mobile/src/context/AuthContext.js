/* AuthContext.js — Global Authentication & ACL State Provider */

import React, { createContext, useState, useEffect } from 'react';
import client, { setAuthToken } from '../api/client';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Login handler
  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.post('/api/v1/auth/login', { email, password });
      const { access_token, user: userProfile } = response.data;

      setToken(access_token);
      setUser(userProfile);
      setAuthToken(access_token);

      return true;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed. Please check credentials.';
      setError(msg);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Register handler
  const register = async (email, password, fullName) => {
    setLoading(true);
    setError(null);
    try {
      await client.post('/api/v1/auth/register', {
        email,
        password,
        full_name: fullName,
      });

      // Auto-login after registration
      return await login(email, password);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed.';
      setError(msg);
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout handler
  const logout = () => {
    setUser(null);
    setToken(null);
    setAuthToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        error,
        isAdmin: user?.role === 'ADMIN',
        login,
        register,
        logout,
        setError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
