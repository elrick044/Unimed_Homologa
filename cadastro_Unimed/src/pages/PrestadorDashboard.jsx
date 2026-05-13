import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  ArrowRightOnRectangleIcon,
  CheckCircleIcon,
  ClockIcon,
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

const documentStatusLabels = {
  PENDENTE: "Pendente",
  ENVIADO: "Enviado",
  EM_VALIDACAO: "Em validacao",
  APROVADO: "Aprovado",
  REPROVADO: "Reprovado",
  SUBSTITUIDO: "Substituido",
};

const documentStatusTone = {
  PENDENTE: "border-amber-200 bg-amber-50 text-amber-800",
  ENVIADO: "border-orange-200 bg-orange-50 text-orange-800",
  EM_VALIDACAO: "border-yellow-200 bg-yellow-50 text-yellow-800",
  APROVADO: "border-emerald-200 bg-emerald-50 text-emerald-800",
  REPROVADO: "border-red-200 bg-red-50 text-red-800",
  SUBSTITUIDO: "border-gray-200 bg-gray-50 text-gray-600",
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

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex w-fit rounded-full border px-3 py-1 text-xs font-semibold ${
        documentStatusTone[status] || "border-gray-200 bg-gray-50 text-gray-700"
      }`}
    >
      {documentStatusLabels[status] || status}
    </span>
  );
}

function DocumentCard({ item }) {
  const document = item.documento;

  return (
    <li className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="font-semibold text-gray-950">{item.tipo_documento?.nome || "Documento"}</p>
          {item.tipo_documento?.descricao && <p className="mt-1 text-sm text-gray-600">{item.tipo_documento.descricao}</p>}
          {document && (
            <p className="mt-2 text-sm text-gray-500">
              {formatFileSize(document.tamanho_bytes)} - versao {document.versao || 1} - {formatDate(document.enviado_em)}
            </p>
          )}
        </div>
        <StatusBadge status={item.status} />
      </div>

      {item.status === "REPROVADO" && (
        <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">Correcao solicitada</p>
            <p className="mt-1">{document?.motivo_reprovacao || "Motivo nao informado pela equipe administrativa."}</p>
            {document?.observacoes && <p className="mt-1 text-red-600">{document.observacoes}</p>}
          </div>
        </div>
      )}
    </li>
  );
}

function DocumentStatusSection({ title, icon, items, emptyText, accentClass }) {
  const StatusIcon = icon;

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <StatusIcon className={`h-5 w-5 ${accentClass}`} />
        <h2 className="text-lg font-semibold text-gray-950">{title}</h2>
      </div>
      {items.length ? (
        <ul className="space-y-3">
          {items.map((item) => (
            <DocumentCard key={`${item.status}-${item.tipo_documento?.id || item.documento?.id}`} item={item} />
          ))}
        </ul>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">{emptyText}</div>
      )}
    </section>
  );
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

  const documentItems = useMemo(() => {
    const activeDocuments = documentosEnviados.filter((documento) => documento.status !== "SUBSTITUIDO");
    const sentTypeIds = new Set(activeDocuments.map((documento) => String(documento.tipo_documento?.id)));
    const pendingItems = pendencias
      .filter((type) => !sentTypeIds.has(String(type.id)))
      .map((type) => ({
        tipo_documento: type,
        documento: null,
        status: "PENDENTE",
      }));

    const sentItems = activeDocuments.map((documento) => ({
      tipo_documento: documento.tipo_documento,
      documento,
      status: documento.status || "ENVIADO",
    }));

    return [...pendingItems, ...sentItems];
  }, [documentosEnviados, pendencias]);

  const documentBuckets = useMemo(
    () => ({
      pendentes: documentItems.filter((item) => item.status === "PENDENTE"),
      validacao: documentItems.filter((item) => item.status === "ENVIADO" || item.status === "EM_VALIDACAO"),
      aprovados: documentItems.filter((item) => item.status === "APROVADO"),
      reprovados: documentItems.filter((item) => item.status === "REPROVADO"),
    }),
    [documentItems],
  );

  const uploadDocumentTypes = useMemo(() => {
    const mergedById = new Map();

    [...documentBuckets.pendentes, ...documentBuckets.reprovados].forEach((item) => {
      const type = item.tipo_documento;
      if (type?.id) {
        mergedById.set(String(type.id), type);
      }
    });

    return Array.from(mergedById.values());
  }, [documentBuckets]);

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
                    <p className="mt-1 text-2xl font-semibold text-gray-950">{documentBuckets.pendentes.length}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm text-gray-500">Em validacao</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-950">{documentBuckets.validacao.length}</p>
                  </div>
                  <div className="rounded-lg bg-slate-50 p-4">
                    <p className="text-sm text-gray-500">Reprovados</p>
                    <p className="mt-1 text-2xl font-semibold text-gray-950">{documentBuckets.reprovados.length}</p>
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
              <DocumentStatusSection
                title="Documentos pendentes"
                icon={ExclamationTriangleIcon}
                items={documentBuckets.pendentes}
                emptyText="Nenhuma pendencia obrigatoria no momento."
                accentClass="text-amber-600"
              />
              <DocumentStatusSection
                title="Em validacao"
                icon={ClockIcon}
                items={documentBuckets.validacao}
                emptyText="Nenhum documento aguardando validacao."
                accentClass="text-orange-600"
              />
              <DocumentStatusSection
                title="Aprovados"
                icon={CheckCircleIcon}
                items={documentBuckets.aprovados}
                emptyText="Nenhum documento aprovado ainda."
                accentClass="text-emerald-600"
              />
              <DocumentStatusSection
                title="Reprovados"
                icon={ExclamationTriangleIcon}
                items={documentBuckets.reprovados}
                emptyText="Nenhum documento reprovado."
                accentClass="text-red-600"
              />
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
              onUploadSuccess={loadProcesso}
            />
          </div>
        )}
      </div>
    </main>
  );
}
