import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  ArrowRightOnRectangleIcon,
  CheckCircleIcon,
  ClockIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ShieldCheckIcon,
} from "@heroicons/react/24/outline";
import { useNavigate, useOutletContext } from "react-router-dom";
import { clearSession } from "../auth/session";
import DocumentoUpload from "../components/DocumentoUpload";
import { api } from "../config/api";

const statusLabels = {
  CADASTRO_INICIADO: "Cadastro iniciado",
  DOCUMENTACAO_PENDENTE: "Documentacao pendente",
  EM_VALIDACAO: "Em validacao",
  CORRECAO_SOLICITADA: "Correcao solicitada",
  EM_APROVACAO_INTERNA: "Em aprovacao interna",
  REPROVADO: "Reprovado",
  APROVADO: "Aprovado",
  MINUTA_GERADA: "Minuta gerada",
  PROCESSO_CONCLUIDO: "Processo concluido",
};

const statusTone = {
  CADASTRO_INICIADO: "border-sky-200 bg-sky-50 text-sky-800",
  DOCUMENTACAO_PENDENTE: "border-amber-200 bg-amber-50 text-amber-800",
  EM_VALIDACAO: "border-blue-200 bg-blue-50 text-blue-800",
  CORRECAO_SOLICITADA: "border-orange-200 bg-orange-50 text-orange-800",
  EM_APROVACAO_INTERNA: "border-indigo-200 bg-indigo-50 text-indigo-800",
  REPROVADO: "border-red-200 bg-red-50 text-red-800",
  APROVADO: "border-emerald-200 bg-emerald-50 text-emerald-800",
  MINUTA_GERADA: "border-purple-200 bg-purple-50 text-purple-800",
  PROCESSO_CONCLUIDO: "border-emerald-200 bg-emerald-50 text-emerald-800",
};

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

function formatFileSize(bytes) {
  if (!bytes) return "0 KB";

  const units = ["bytes", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / 1024 ** index;

  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export default function PrestadorDashboard() {
  const navigate = useNavigate();
  const { user } = useOutletContext();
  const [processo, setProcesso] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  const logout = () => {
    clearSession();
    navigate("/login", { replace: true });
  };

  const loadProcesso = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const { data } = await api.get("/prestador/processo/");
      setProcesso(data);
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || "Nao foi possivel carregar os dados do processo.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadProcesso();
  }, [loadProcesso]);

  const documentosEnviados = useMemo(() => processo?.documentos_enviados || [], [processo]);
  const pendencias = useMemo(() => processo?.pendencias || [], [processo]);
  const statusAtual = processo?.status_atual || "CADASTRO_INICIADO";
  const isCorrection = statusAtual === "CORRECAO_SOLICITADA";

  const hiddenTypeIds = useMemo(() => {
    if (isCorrection) return [];
    return documentosEnviados.map((documento) => documento.tipo_documento?.id).filter(Boolean);
  }, [documentosEnviados, isCorrection]);

  const uploadDocumentTypes = useMemo(() => {
    const sentTypes = documentosEnviados.map((documento) => documento.tipo_documento).filter(Boolean);
    const mergedById = new Map();

    [...pendencias, ...sentTypes].forEach((type) => {
      if (type?.id) {
        mergedById.set(String(type.id), type);
      }
    });

    return Array.from(mergedById.values());
  }, [documentosEnviados, pendencias]);

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
              {user?.nome
                ? `${user.nome}, acompanhe o status real da sua homologacao.`
                : "Acompanhe o status real da sua homologacao."}
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

        {isLoading ? (
          <section className="rounded-lg border border-gray-200 bg-white p-6 text-sm font-medium text-gray-600 shadow-sm">
            <span className="inline-flex items-center gap-2">
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              Carregando processo...
            </span>
          </section>
        ) : errorMessage ? (
          <section className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            {errorMessage}
          </section>
        ) : (
          <div className="space-y-6">
            <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-950">Etapa atual</h2>
                    <p className="mt-1 text-sm text-gray-600">
                      Atualizado em {formatDate(processo?.atualizado_em)}
                    </p>
                  </div>
                  <span
                    className={`inline-flex w-fit rounded-full border px-3 py-1 text-sm font-semibold ${
                      statusTone[statusAtual] || "border-gray-200 bg-gray-50 text-gray-700"
                    }`}
                  >
                    {statusLabels[statusAtual] || statusAtual}
                  </span>
                </div>

                <div className="mt-6 grid gap-3 sm:grid-cols-3">
                  <div className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm text-gray-500">Pendencias</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-950">{pendencias.length}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm text-gray-500">Enviados</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-950">{documentosEnviados.length}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm text-gray-500">Criado em</p>
                    <p className="mt-1 text-sm font-semibold text-gray-950">{formatDate(processo?.criado_em)}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-gray-950">Empresa</h2>
                <div className="mt-4 space-y-3 text-sm">
                  <p>
                    <span className="block text-gray-500">Razao social</span>
                    <span className="font-medium text-gray-950">{processo?.prestador?.razao_social}</span>
                  </p>
                  <p>
                    <span className="block text-gray-500">CNPJ</span>
                    <span className="font-medium text-gray-950">{processo?.prestador?.cnpj}</span>
                  </p>
                </div>
              </div>
            </section>

            <section className="grid gap-6 lg:grid-cols-2">
              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <ExclamationTriangleIcon className="h-5 w-5 text-amber-600" />
                  <h2 className="text-lg font-semibold text-gray-950">Documentos pendentes</h2>
                </div>
                {pendencias.length ? (
                  <ul className="space-y-3">
                    {pendencias.map((documento) => (
                      <li key={documento.id} className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                        <p className="text-sm font-semibold text-amber-950">{documento.nome}</p>
                        {documento.descricao && <p className="mt-1 text-sm text-amber-800">{documento.descricao}</p>}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
                    <span className="inline-flex items-center gap-2">
                      <CheckCircleIcon className="h-5 w-5" />
                      Nenhuma pendencia obrigatoria no momento.
                    </span>
                  </div>
                )}
              </div>

              <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <DocumentTextIcon className="h-5 w-5 text-[#006F46]" />
                  <h2 className="text-lg font-semibold text-gray-950">Documentos enviados</h2>
                </div>
                {documentosEnviados.length ? (
                  <ul className="divide-y divide-gray-200">
                    {documentosEnviados.map((documento) => (
                      <li key={documento.id} className="flex items-start justify-between gap-4 py-3 text-sm">
                        <div className="min-w-0">
                          <p className="truncate font-semibold text-gray-950">
                            {documento.tipo_documento?.nome || "Documento"}
                          </p>
                          <p className="mt-1 text-gray-500">
                            {formatFileSize(documento.tamanho_bytes)} - {formatDate(documento.enviado_em)}
                          </p>
                        </div>
                        <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                          Recebido
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
                    Nenhum documento foi recebido ainda.
                  </div>
                )}
              </div>
            </section>

            {processo?.historico?.length > 0 && (
              <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
                <div className="mb-4 flex items-center gap-2">
                  <ClockIcon className="h-5 w-5 text-gray-500" />
                  <h2 className="text-lg font-semibold text-gray-950">Historico recente</h2>
                </div>
                <ul className="space-y-3">
                  {processo.historico.slice(0, 4).map((evento) => (
                    <li key={evento.id} className="rounded-lg bg-slate-50 p-4 text-sm">
                      <p className="font-semibold text-gray-950">{evento.acao}</p>
                      <p className="mt-1 text-gray-600">{evento.descricao}</p>
                      <p className="mt-2 text-xs text-gray-500">{formatDate(evento.criado_em)}</p>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            <DocumentoUpload
              documentTypes={uploadDocumentTypes}
              hiddenTypeIds={hiddenTypeIds}
              onUploadSuccess={loadProcesso}
            />
          </div>
        )}
      </div>
    </main>
  );
}
