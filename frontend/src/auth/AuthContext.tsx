import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, onUnauthorized, tokenStore } from "../api/client";
import type { User } from "../api/types";

type AuthState = {
  user: User | null;
  ready: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, displayName: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // `ready` stays false until we know whether the stored token is still valid,
  // so the app never flashes the sign-in screen at an already-signed-in user.
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const token = tokenStore.get();
    if (!token) {
      setReady(true);
      return;
    }
    api
      .me()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => {
        tokenStore.clear();
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => onUnauthorized(() => setUser(null)), []);

  const signIn = useCallback(async (email: string, password: string) => {
    const result = await api.login(email, password);
    tokenStore.set(result.access_token);
    setUser(result.user);
  }, []);

  const signUp = useCallback(
    async (email: string, password: string, displayName: string) => {
      const result = await api.register(email, password, displayName);
      tokenStore.set(result.access_token);
      setUser(result.user);
    },
    [],
  );

  const signOut = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, ready, signIn, signUp, signOut }),
    [user, ready, signIn, signUp, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside an AuthProvider");
  return context;
}
