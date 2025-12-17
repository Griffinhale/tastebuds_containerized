"use client";

import { apiFetch } from './api';

export const SESSION_FLAG_KEY = 'tastebuds_session_active';
export const SESSION_EVENT = 'tastebuds:session';

type SessionEventDetail = {
  hasSession: boolean;
};

function broadcastSessionState(hasSession: boolean) {
  if (typeof window === 'undefined') return;
  try {
    if (hasSession) {
      window.localStorage.setItem(SESSION_FLAG_KEY, '1');
    } else {
      window.localStorage.removeItem(SESSION_FLAG_KEY);
    }
  } catch {
    // ignore storage failures (private mode, etc.)
  }
  try {
    const event = new CustomEvent<SessionEventDetail>(SESSION_EVENT, { detail: { hasSession } });
    window.dispatchEvent(event);
  } catch {
    // swallow dispatch errors
  }
}

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
  broadcastSessionState(true);
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
  broadcastSessionState(true);
  return res.user;
}

export async function refreshTokens() {
  try {
    const res = await apiFetch<AuthResponse>(
      '/auth/refresh',
      {
        method: 'POST'
      },
      { isServer: false }
    );
    broadcastSessionState(true);
    return res;
  } catch (err) {
    broadcastSessionState(false);
    throw err;
  }
}

export async function logout() {
  await apiFetch('/auth/logout', { method: 'POST' }, { isServer: false });
  broadcastSessionState(false);
}
