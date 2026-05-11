import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  ArrowRightOnRectangleIcon,
  ClipboardDocumentCheckIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import { useNavigate, useOutletContext } from "react-router-dom";
import { clearSession } from "../auth/session";
import { api } from "../config/api";

const statusOptions = [
  { value: "", label: "Todos os status" },
  { value: "CADASTRO_INICIADO", label: "Cadastro iniciado" },
  { value: "DOCUMENTACAO_PENDENTE", label: "Documentacao pendente" },
  { value: "EM_VALIDACAO", label: "Em validacao" },
  { value: "CORRECAO_SOLICITADA", label: "Correcao solicitada" },
  { value: "EM_APROVACAO_INTERNA", label: "Em aprovacao interna" },
  { value: "REPROVADO", label: "Reprovado" },
  { value: "APROVADO", label: "Aprovado" },
  { value: "MINUTA_GERADA", label: "Minuta gerada" },
  { value: "PROCESSO_CONCLUIDO", label: "Processo concluido" },
];

const simulatedProcesses = [
  {
    id: 1,
    empresa: "Clinica Exemplo LTDA",
    cnpj: "12345678000190",
    criado_em: "2026-05-10T10:00:00Z",
    status: "DOCUMENTACAO_PENDENTE",
  },
  {
    id: 2,
    empresa: "Laboratorio Central SA",
    cnpj: "11222333000144",
    criado_em: "2026-05-09T14:20:00Z",
    status: "EM_VALIDACAO",
  },
  {
    id: 3,
    empresa: "Imagem Saude Diagnosticos",
    cnpj: "98765432000110",
    criado_em: "2026-05-08T09:45:00Z",
    status: "CORRECAO_SOLICITADA",
  },
];

const statusTone = {
  CADASTRO_INICIADO: "bg-sky-50 text-sky-700",
  DOCUMENTACAO_PENDENTE: "bg-amber-50 text-amber-700",
  EM_VALIDACAO: "bg-blue-50 text-blue-700",
  CORRECAO_SOLICITADA: "bg-orange-50 text-orange-700",
  EM_APROVACAO_INTERNA: "bg-indigo-50 text-indigo-700",
  REPROVADO: "bg-red-50 text-red-700",
  APROVADO: "bg-emerald-50 text-emerald-700",
  MINUTA_GERADA: "bg-purple-50 text-purple-700",
  PROCESSO_CONCLUIDO: "bg-emerald-50 text-emerald-700",
};

function getStatusLabel(status) {
  return statusOptions.find((option) => option.value === status)?.label || status;
}

function formatDate(value) {
  if (!value) return "-";

  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatCnpj(value = "") {
  const digits = value.replace(/\D/g, "").slice(0, 14);

  if (digits.length !== 14) return value || "-";

  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8, 12)}-${digits.slice(12)}`;
}

function normalizeProcess(item) {
  const prestador = item.prestador || {};

  return {
    id: item.id,
    empresa: item.empresa || prestador.razao_social || item.razao_social || "-",
    cnpj: item.cnpj || prestador.cnpj || "-",
    criado_em: item.criado_em || item.data_criacao || item.created_at,
    status: item.status || item.status_atual || "CADASTRO_INICIADO",
  };
}

export default function AdminProcessos() {
  const navigate = useNavigate();
  const { user } = useOutletContext();
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [processes, setProcesses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  const logout = () => {
    clearSession();
    navigate("/login", { replace: true });
  };

  const filteredFallbackProcesses = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return simulatedProcesses.filter((processo) => {
      const matchesStatus = !statusFilter || processo.status === statusFilter;
      const matchesSearch =
        !normalizedSearch ||
        processo.empresa.toLowerCase().includes(normalizedSearch) ||
        processo.cnpj.includes(normalizedSearch.replace(/\D/g, ""));

      return matchesStatus && matchesSearch;
    });
  }, [search, statusFilter]);

  const loadProcesses = useCallback(async () => {
    setIsLoading(true);

    try {
      const { data } = await api.get("/admin/processos/", {
        params: {
          status: statusFilter || undefined,
          busca: search.trim() || undefined,
        },
      });

      const apiProcesses = data.processos || data.results || data;
      setProcesses(Array.isArray(apiProcesses) ? apiProcesses.map(normalizeProcess) : []);
      setUsingFallback(false);
    } catch {
      setProcesses(filteredFallbackProcesses);
      setUsingFallback(true);
    } finally {
      setIsLoading(false);
    }
  }, [filteredFallbackProcesses, search, statusFilter]);

  useEffect(() => {
    loadProcesses();
  }, [loadProcesses]);

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
              {user?.nome || user?.email}, acompanhe a fila consolidada dos processos.
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

        <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="border-b border-gray-200 p-5 sm:p-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-gray-950">Fila de processos</h2>
                <p className="mt-1 text-sm text-gray-600">
                  Use os filtros para localizar prestadores por status, empresa ou CNPJ.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-[220px_280px]">
                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700">Status</span>
                  <select
                    value={statusFilter}
                    onChange={(event) => setStatusFilter(event.target.value)}
                    className="block min-h-11 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                  >
                    {statusOptions.map((option) => (
                      <option key={option.value || "todos"} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-1 block text-sm font-medium text-gray-700">Busca</span>
                  <div className="relative">
                    <MagnifyingGlassIcon className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                    <input
                      type="search"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Empresa ou CNPJ"
                      className="block min-h-11 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 pl-10 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                    />
                  </div>
                </label>
              </div>
            </div>

            {usingFallback && (
              <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                Endpoint administrativo ainda indisponivel; exibindo dados simulados temporarios.
              </div>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-normal text-gray-500">
                    Empresa
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-normal text-gray-500">
                    CNPJ
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-normal text-gray-500">
                    Data de criacao
                  </th>
                  <th className="px-5 py-3 text-left text-xs font-semibold uppercase tracking-normal text-gray-500">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {isLoading ? (
                  <tr>
                    <td colSpan="4" className="px-5 py-8 text-sm text-gray-600">
                      <span className="inline-flex items-center gap-2">
                        <ArrowPathIcon className="h-4 w-4 animate-spin" />
                        Carregando processos...
                      </span>
                    </td>
                  </tr>
                ) : processes.length ? (
                  processes.map((processo) => (
                    <tr key={processo.id} className="hover:bg-gray-50">
                      <td className="whitespace-nowrap px-5 py-4 text-sm font-medium text-gray-950">
                        {processo.empresa}
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-sm text-gray-600">
                        {formatCnpj(processo.cnpj)}
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-sm text-gray-600">
                        {formatDate(processo.criado_em)}
                      </td>
                      <td className="whitespace-nowrap px-5 py-4 text-sm">
                        <span
                          className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                            statusTone[processo.status] || "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {getStatusLabel(processo.status)}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="4" className="px-5 py-8 text-sm text-gray-600">
                      Nenhum processo encontrado com os filtros atuais.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
