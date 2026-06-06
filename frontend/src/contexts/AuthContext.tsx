import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getMe } from "../api";
import { clearAuth, getAuth, setAuth, type AuthUser } from "../auth";

interface AuthContextValue {
  user: AuthUser | null;
  setUser: (user: AuthUser | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(getAuth().user);

  useEffect(() => {
    const auth = getAuth();
    if (auth.token) {
      getMe()
        .then((u) => setUser(u))
        .catch(() => {
          clearAuth();
          setUser(null);
        });
    }
  }, []);

  const logout = () => {
    clearAuth();
    setUser(null);
  };

  const handleSetUser = (next: AuthUser | null) => {
    if (next) {
      const token = getAuth().token;
      if (token) setAuth({ token, user: next });
    }
    setUser(next);
  };

  return (
    <AuthContext.Provider value={{ user, setUser: handleSetUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
