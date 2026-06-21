const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const USER_KEY = "auth_user";
const LEGACY_PROFILE_KEY = "user_profile";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser() {
  const user = localStorage.getItem(USER_KEY);

  if (!user) return null;

  try {
    return JSON.parse(user);
  } catch {
    return null;
  }
}

export function saveSession({ access, refresh, user }) {
  if (access) {
    localStorage.setItem(ACCESS_TOKEN_KEY, access);
  }

  if (refresh) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  }

  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.setItem(LEGACY_PROFILE_KEY, user.perfil);
  }
}

export function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(LEGACY_PROFILE_KEY);
}

export function getRedirectPath(userOrProfile) {
  const perfil = typeof userOrProfile === "string" ? userOrProfile : userOrProfile?.perfil;

  if (perfil === "EQUIPE_ADMINISTRATIVA" || perfil === "ADMINISTRADOR") {
    return "/admin/processos";
  }

  return "/prestador/dashboard";
}
