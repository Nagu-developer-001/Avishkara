export type AuthUser = {
  id: string;
  name: string;
  email: string;
  created_at: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type UserRole = "athlete" | "authority";

export type SessionResponse = {
  user: AuthUser;
  role: UserRole;
};

export type RegisterPayload = LoginPayload & {
  name: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type AuthContextValue = {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginPayload, intendedRole: UserRole) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => void;
};
