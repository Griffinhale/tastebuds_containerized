"use client";

import { apiFetch } from './api';

export type User = {
  id: string;
  email: string;
  display_name: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
};

export async function login(email: string, password: string) {
  const res = await apiFetch<AuthResponse>(
    '/auth/login',
    {
      method: 'POST',
      body: JSON.stringify({ email, password })
    },
    { isServer: false }
  );
  return res.user;
}

export async function register(email: string, password: string, displayName: string) {
  const res = await apiFetch<AuthResponse>(
    '/auth/register',
    {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName })
    },
    { isServer: false }
  );
  return res.user;
}

export async function refreshTokens() {
  return apiFetch<AuthResponse>(
    '/auth/refresh',
    {
      method: 'POST'
    },
    { isServer: false }
  );
}

export async function logout() {
  await apiFetch('/auth/logout', { method: 'POST' }, { isServer: false });
}
