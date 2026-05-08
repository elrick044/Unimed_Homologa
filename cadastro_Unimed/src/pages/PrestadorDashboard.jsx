import { ArrowRightOnRectangleIcon, ShieldCheckIcon } from "@heroicons/react/24/outline";
import { Link, useNavigate } from "react-router-dom";
import DocumentoUpload from "../components/DocumentoUpload";

export default function PrestadorDashboard() {
  const navigate = useNavigate();
  const hasToken = Boolean(localStorage.getItem("access_token"));

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_profile");
    navigate("/login", { replace: true });
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#009966]/20 bg-white px-3 py-1 text-sm font-medium text-[#006F46] shadow-sm">
              <ShieldCheckIcon className="h-4 w-4" />
              Area do prestador
            </div>
            <h1 className="text-3xl font-semibold text-gray-950">Dashboard do prestador</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600">
              Envie e acompanhe os documentos necessarios para a homologacao da empresa.
            </p>
          </div>

          {hasToken ? (
            <button
              type="button"
              onClick={logout}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
            >
              <ArrowRightOnRectangleIcon className="h-5 w-5" />
              Sair
            </button>
          ) : (
            <Link
              to="/login"
              className="inline-flex min-h-11 items-center justify-center rounded-lg bg-[#006F46] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C]"
            >
              Entrar
            </Link>
          )}
        </header>

        {!hasToken && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
            Voce precisa estar autenticado para enviar documentos.
          </div>
        )}

        <DocumentoUpload disabled={!hasToken} />
      </div>
    </main>
  );
}
