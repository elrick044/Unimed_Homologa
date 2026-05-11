import { ArrowRightOnRectangleIcon, ClipboardDocumentCheckIcon } from "@heroicons/react/24/outline";
import { useNavigate, useOutletContext } from "react-router-dom";
import { clearSession } from "../auth/session";

export default function AdminProcessos() {
  const navigate = useNavigate();
  const { user } = useOutletContext();

  const logout = () => {
    clearSession();
    navigate("/login", { replace: true });
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#009966]/20 bg-white px-3 py-1 text-sm font-medium text-[#006F46] shadow-sm">
              <ClipboardDocumentCheckIcon className="h-4 w-4" />
              Processos administrativos
            </div>
            <h1 className="text-3xl font-semibold text-gray-950">Homologacao de prestadores</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600">
              {user?.nome || user?.email}, acompanhe os processos de homologacao dos prestadores.
            </p>
          </div>

          <button
            type="button"
            onClick={logout}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
          >
            <ArrowRightOnRectangleIcon className="h-5 w-5" />
            Sair
          </button>
        </header>

        <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-950">Fila de processos</h2>
          <p className="mt-2 text-sm text-gray-600">
            Esta area ja esta protegida por perfil e pronta para receber a listagem operacional.
          </p>
        </section>
      </div>
    </main>
  );
}
