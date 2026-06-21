import { useEffect, useMemo, useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { api } from "../config/api";
import { clearSession, getAccessToken, getRedirectPath, getStoredUser, saveSession } from "../auth/session";

export default function ProtectedRoute({ allowedProfiles = [] }) {
  const location = useLocation();
  const requiredProfiles = useMemo(() => new Set(allowedProfiles), [allowedProfiles]);
  const [status, setStatus] = useState(() => (getAccessToken() ? "loading" : "anonymous"));
  const [user, setUser] = useState(() => getStoredUser());

  useEffect(() => {
    if (!getAccessToken()) {
      setStatus("anonymous");
      return;
    }

    let isMounted = true;

    api
      .get("/auth/me/")
      .then(({ data }) => {
        if (!isMounted) return;

        saveSession({ user: data });
        setUser(data);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!isMounted) return;

        clearSession();
        setUser(null);
        setStatus("anonymous");
      });

    return () => {
      isMounted = false;
    };
  }, [location.pathname]);

  if (status === "loading") {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-10 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl text-sm font-medium text-gray-600">Validando sessao...</div>
      </main>
    );
  }

  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  if (requiredProfiles.size > 0 && !requiredProfiles.has(user?.perfil)) {
    return <Navigate to={getRedirectPath(user)} replace />;
  }

  return <Outlet context={{ user }} />;
}
