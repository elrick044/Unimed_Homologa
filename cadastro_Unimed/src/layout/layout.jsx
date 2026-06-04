import Navbar from "../components/Navbar";
import AdminSidebar from "../components/AdminSidebar";
import { Outlet, useLocation } from "react-router-dom";
import { getStoredUser } from "../auth/session";

export default function Layout() {
  const location = useLocation();
  const user = getStoredUser();
  const showAdminSidebar = location.pathname.startsWith("/admin") && user?.perfil === "ADMINISTRADOR";

  return (
    <>
      <Navbar />
      <div className="pt-24 bg-slate-50">
        {location.pathname === "/" ? (
          <main className="min-h-screen">
            <Outlet />
          </main>
        ) : (
          <div className="mx-auto min-h-screen max-w-7xl px-4 pb-10 sm:px-6 lg:px-8">
            {showAdminSidebar ? (
              <div className="lg:grid lg:grid-cols-[240px_1fr] lg:gap-6">
                <AdminSidebar />
                <main className="rounded-3xl bg-slate-50 p-0 py-10">
                  <Outlet />
                </main>
              </div>
            ) : (
              <main className="py-10">
                <Outlet />
              </main>
            )}
          </div>
        )}
      </div>
    </>
  );
}