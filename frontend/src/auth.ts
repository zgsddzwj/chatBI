export interface AuthUser {
  id: number;
  username: string;
  display_name: string | null;
  role: string;
}

export interface AuthState {
  token: string | null;
  user: AuthUser | null;
}

const AUTH_KEY = "chatbi_auth";

export const getAuth = (): AuthState => {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    if (!raw) return { token: null, user: null };
    return JSON.parse(raw) as AuthState;
  } catch {
    return { token: null, user: null };
  }
};

export const setAuth = (state: AuthState) => {
  localStorage.setItem(AUTH_KEY, JSON.stringify(state));
};

export const clearAuth = () => {
  localStorage.removeItem(AUTH_KEY);
};

export const getToken = (): string | null => getAuth().token;
