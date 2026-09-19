import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import type { User } from '../types';
import { authApi } from '../services/api';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (email: string, password: string, fullName: string, role: 'applicant' | 'client') => Promise<User>;
  completeGoogleLogin: (token: string) => Promise<User>;
  logout: () => void;
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const TOKEN_KEY = 'xai_loan_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { token, user: loggedInUser } = await authApi.login({ email, password });
    localStorage.setItem(TOKEN_KEY, token);
    setUser(loggedInUser);
    return loggedInUser;
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string, role: 'applicant' | 'client') => {
    const { token, user: newUser } = await authApi.register({ email, password, full_name: fullName, role });
    localStorage.setItem(TOKEN_KEY, token);
    setUser(newUser);
    return newUser;
  }, []);

  const completeGoogleLogin = useCallback(async (token: string) => {
    localStorage.setItem(TOKEN_KEY, token);
    try {
      const loggedInUser = await authApi.me();
      setUser(loggedInUser);
      return loggedInUser;
    } catch (error) {
      localStorage.removeItem(TOKEN_KEY);
      throw error;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
    authApi.logout().catch(() => undefined);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, completeGoogleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
