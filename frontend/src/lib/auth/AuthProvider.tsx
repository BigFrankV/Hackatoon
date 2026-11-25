import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";

import {
  getAccessToken,
  setAccessToken,
  setRefreshHandler,
  setUnauthorizedHandler,
} from "@/lib/api/client";
import { ApiRequestError } from "@/lib/api/client";
import {
  changePasswordRequest,
  loginRequest,
  logoutRequest,
  meRequest,
  refreshRequest,
  updateProfileRequest,
} from "@/lib/auth/authApi";
import type { UserPublic } from "@/types";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

interface AuthContextValue {
  status: AuthStatus;
  user: UserPublic | null;
  accessToken: string | null;
  authError: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<UserPublic>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<UserPublic | null>;
  updateProfile: (payload: {
    first_name?: string | null;
    last_name?: string | null;
  }) => Promise<UserPublic>;
  changePassword: (payload: {
    current_password: string;
    new_password: string;
  }) => Promise<string>;
  clearAuthError: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<UserPublic | null>(null);
  const [token, setTokenState] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const refreshPromiseRef = useRef<Promise<string | null> | null>(null);
  const bootstrapRef = useRef(false);

  const applyToken = useCallback((newToken: string | null) => {
    setAccessToken(newToken);
    setTokenState(newToken);
  }, []);

  const clearSession = useCallback((message?: string) => {
    applyToken(null);
    setUser(null);
    setStatus("unauthenticated");
    if (message) setAuthError(message);
  }, [applyToken]);

  const refreshSession = useCallback(async (): Promise<string | null> => {
    if (refreshPromiseRef.current) {
      return refreshPromiseRef.current;
    }

    const promise = (async () => {
      try {
        const response = await refreshRequest();
        applyToken(response.access_token);
        return response.access_token;
      } catch {
        applyToken(null);
        setUser(null);
        setStatus("unauthenticated");
        return null;
      } finally {
        refreshPromiseRef.current = null;
      }
    })();

    refreshPromiseRef.current = promise;
    return promise;
  }, [applyToken]);

  const refreshUser = useCallback(async (): Promise<UserPublic | null> => {
    try {
      const me = await meRequest();
      setUser(me);
      setStatus("authenticated");
      return me;
    } catch (error) {
      if (error instanceof ApiRequestError && error.status === 401) {
        clearSession();
      }
      return null;
    }
  }, [clearSession]);

  useEffect(() => {
    setRefreshHandler(refreshSession);
    setUnauthorizedHandler(() => {
      clearSession("Tu sesión ha caducado. Inicia sesión de nuevo.");
    });
    return () => {
      setRefreshHandler(null);
      setUnauthorizedHandler(null);
    };
  }, [clearSession, refreshSession]);

  useEffect(() => {
    if (bootstrapRef.current) return;
    bootstrapRef.current = true;

    const bootstrap = async () => {
      setStatus("loading");
      const newToken = await refreshSession();
      if (!newToken) {
        clearSession();
        return;
      }
      try {
        const me = await meRequest();
        setUser(me);
        setStatus("authenticated");
      } catch {
        clearSession();
      }
    };

    void bootstrap();
  }, [clearSession, refreshSession]);

  const login = useCallback(async (email: string, password: string): Promise<UserPublic> => {
    setAuthError(null);
    const response = await loginRequest(email, password);
    applyToken(response.access_token);
    setUser(response.user);
    setStatus("authenticated");
    return response.user;
  }, [applyToken]);

  const logout = useCallback(async (): Promise<void> => {
    try {
      if (getAccessToken()) {
        await logoutRequest();
      }
    } catch {
      // Always clear local session even if server logout fails.
    } finally {
      clearSession();
    }
  }, [clearSession]);

  const updateProfile = useCallback(async (payload: {
    first_name?: string | null;
    last_name?: string | null;
  }): Promise<UserPublic> => {
    const updated = await updateProfileRequest(payload);
    setUser(updated);
    return updated;
  }, []);

  const changePassword = useCallback(async (payload: {
    current_password: string;
    new_password: string;
  }): Promise<string> => {
    const response = await changePasswordRequest(payload);
    applyToken(response.access_token);
    // Refresh profile (must_change_password may have changed).
    try {
      const me = await meRequest();
      setUser(me);
      setStatus("authenticated");
    } catch {
      // Token already updated; ignore profile refresh failure.
    }
    return response.message;
  }, [applyToken]);

  const clearAuthError = useCallback(() => setAuthError(null), []);

  const value = useMemo<AuthContextValue>(() => ({
    status,
    user,
    accessToken: token,
    authError,
    isAuthenticated: status === "authenticated" && !!user,
    login,
    logout,
    refreshUser,
    updateProfile,
    changePassword,
    clearAuthError,
  }), [status, user, token, authError, login, logout, refreshUser, updateProfile, changePassword, clearAuthError]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
