"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useSyncExternalStore
} from "react";

import { clearStoredSession, getStoredSession, setStoredSession } from "../lib/api";

const AuthContext = createContext(undefined);

const emptySubscribe = () => () => {};

let authEpoch = 0;
const authListeners = new Set();

function subscribeAuth(onStoreChange) {
  authListeners.add(onStoreChange);
  return () => authListeners.delete(onStoreChange);
}

function getAuthEpochSnapshot() {
  return authEpoch;
}

function getServerAuthEpochSnapshot() {
  return 0;
}

function bumpAuthEpoch() {
  authEpoch += 1;
  authListeners.forEach((listener) => listener());
}

export function AuthProvider({ children }) {
  const isClient = useSyncExternalStore(emptySubscribe, () => true, () => false);
  const epoch = useSyncExternalStore(
    subscribeAuth,
    getAuthEpochSnapshot,
    getServerAuthEpochSnapshot
  );

  const session = useMemo(() => {
    if (!isClient) return null;
    void epoch;
    return getStoredSession();
  }, [isClient, epoch]);

  const login = useCallback((next) => {
    setStoredSession(next);
    bumpAuthEpoch();
  }, []);

  const logout = useCallback(() => {
    clearStoredSession();
    bumpAuthEpoch();
  }, []);

  const value = useMemo(
    () => ({
      session,
      ready: isClient,
      isAdmin: session?.role === "admin",
      login,
      logout
    }),
    [session, isClient, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
