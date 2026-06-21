import { Link, useLocation } from "react-router-dom";
import { getStoredUser } from "../auth/session";

const navigation = [
  { name: "Processos", to: "/admin/processos" },
  { name: "Usuarios internos", to: "/admin/config/usuarios" },
  { name: "Tipos de documento", to: "/admin/config/documentos" },
  { name: "Fluxo de aprovacao", to: "/admin/config/fluxo" },
  { name: "Templates de contrato", to: "/admin/config/templates" },
];

export default function AdminSidebar() {
  const location = useLocation();
  const user = getStoredUser();

  if (!user || user.perfil !== "ADMINISTRADOR") {
    return null;
  }

  return (
    <aside className="sticky top-24 hidden h-[calc(100vh-6rem)] shrink-0 overflow-y-auto rounded-3xl border border-gray-200 bg-white p-6 shadow-sm lg:block">
      <div className="space-y-4">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-gray-500">Configuracoes</p>
          <p className="mt-3 text-sm text-gray-600">Gerencie usuarios, documentos, templates e o fluxo padrao.</p>
        </div>
        <nav className="space-y-2">
          {navigation.map((item) => {
            const active = location.pathname === item.to;
            return (
              <Link
                key={item.name}
                to={item.to}
                className={`block rounded-2xl px-4 py-3 text-sm font-medium transition ${
                  active
                    ? "bg-[#006F46] text-white shadow-sm"
                    : "border border-gray-200 bg-white text-gray-700 hover:border-[#006F46] hover:text-[#006F46]"
                }`}
              >
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
