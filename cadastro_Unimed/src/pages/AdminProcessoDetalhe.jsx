import { useCallback, useMemo, useState, useEffect } from "react";
import {
  ArrowDownTrayIcon,
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
} from "@heroicons/react/24/outline";
import { Link, useParams } from "react-router-dom";
import { API_URL, api } from "../config/api";

const documentStatusLabels = {
  ENVIADO: "Enviado",
  EM_VALIDACAO: "Em validacao",
  APROVADO: "Aprovado",
  REPROVADO: "Reprovado",
  SUBSTITUIDO: "Substituido",
};

const documentStatusTone = {
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

function getFileUrl(path) {
  if (!path) return "#";
  if (/^https?:\/\//i.test(path)) return path;

  const appOrigin = API_URL.replace(/\/api\/?$/, "").replace(/\/$/, "");
  return `${appOrigin}${path.startsWith("/") ? path : `/${path}`}`;
}

function getApiMessage(data) {
  if (Array.isArray(data?.motivo_reprovacao)) return data.motivo_reprovacao.join(" ");
  if (Array.isArray(data?.status)) return data.status.join(" ");
  if (typeof data?.detail === "string") return data.detail;

  return "Nao foi possivel validar o documento.";
}

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${
        documentStatusTone[status] || "border-gray-200 bg-gray-50 text-gray-700"
      }`}
    >
      {documentStatusLabels[status] || status || "Sem envio"}
    </span>
  );
}

function RejectionModal({ document, isSubmitting, errorMessage, onClose, onConfirm }) {
  const [motivo, setMotivo] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const canSubmit = motivo.trim().length > 0 && !isSubmitting;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4 py-6">
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-lg font-semibold text-gray-950">Reprovar documento</h2>
          <p className="mt-1 text-sm text-gray-600">
            Informe o motivo que sera exibido ao prestador para correcao.
          </p>
        </div>

        <div className="space-y-4 px-6 py-5">
          <div className="rounded-lg bg-slate-50 p-3 text-sm text-gray-700">
            {document?.tipo_documento?.nome || "Documento"} - versao {document?.versao || 1}
          </div>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Motivo da reprovacao</span>
            <textarea
              value={motivo}
              onChange={(event) => setMotivo(event.target.value)}
              rows="4"
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
              placeholder="Ex.: Documento ilegivel. Enviar novamente com melhor qualidade."
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-sm font-medium text-gray-700">Observacoes internas</span>
            <textarea
              value={observacoes}
              onChange={(event) => setObservacoes(event.target.value)}
              rows="3"
              className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
              placeholder="Opcional"
            />
          </label>

          {errorMessage && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          )}
        </div>

        <div className="flex flex-col-reverse gap-3 border-t border-gray-200 px-6 py-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={isSubmitting}
            className="inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => onConfirm({ motivo_reprovacao: motivo.trim(), observacoes: observacoes.trim() })}
            disabled={!canSubmit}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            Confirmar reprovacao
          </button>
        </div>
      </div>
    </div>
  );
}

function VersionHistory({ versions }) {
  const replacedVersions = versions.filter((version) => version.status === "SUBSTITUIDO");

  if (!replacedVersions.length) {
    return (
      <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600">
        Nenhuma versao substituida para este tipo de documento.
      </div>
    );
  }

  return (
    <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
      <h4 className="text-sm font-semibold text-gray-950">Historico de versoes substituidas</h4>
      <ul className="mt-3 divide-y divide-gray-200">
        {replacedVersions.map((version) => (
          <li key={version.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm">
              <p className="font-medium text-gray-950">Versao {version.versao || 1}</p>
              <p className="text-gray-500">{formatDate(version.enviado_em)}</p>
            </div>
            <a
              href={getFileUrl(version.arquivo)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
            >
              <ArrowDownTrayIcon className="h-4 w-4" />
              Abrir PDF
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function AdminProcessoDetalhe() {
  const { id } = useParams();
  const [documentGroups, setDocumentGroups] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [expandedHistory, setExpandedHistory] = useState({});
  const [validationError, setValidationError] = useState("");
  const [validatingId, setValidatingId] = useState(null);
  const [rejectionDocument, setRejectionDocument] = useState(null);

  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage("");

    try {
      const { data } = await api.get(`/processos/${id}/documentos/`);
      setDocumentGroups(data.documentos || []);
    } catch (error) {
      setErrorMessage(error.response?.data?.detail || "Nao foi possivel carregar os documentos do processo.");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const totalPendingValidation = useMemo(
    () =>
      documentGroups.filter((group) => {
        const status = group.documento_atual?.status;
        return status === "ENVIADO" || status === "EM_VALIDACAO";
      }).length,
    [documentGroups],
  );

  const validateDocument = async (document, payload) => {
    setValidationError("");
    setValidatingId(document.id);

    try {
      await api.post(`/admin/documentos/${document.id}/validar/`, payload);
      setRejectionDocument(null);
      await loadDocuments();
    } catch (error) {
      setValidationError(getApiMessage(error.response?.data));
    } finally {
      setValidatingId(null);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <Link
              to="/admin/processos"
              className="mb-4 inline-flex items-center gap-2 text-sm font-semibold text-[#006F46] hover:text-[#00583C]"
            >
              <ArrowLeftIcon className="h-4 w-4" />
              Voltar para processos
            </Link>
            <h1 className="text-3xl font-semibold text-gray-950">Validacao de documentos</h1>
            <p className="mt-2 text-sm text-gray-600">
              Processo #{id} com {totalPendingValidation} documento(s) aguardando acao da equipe.
            </p>
          </div>
        </header>

        {isLoading ? (
          <section className="rounded-lg border border-gray-200 bg-white p-6 text-sm font-medium text-gray-600 shadow-sm">
            <span className="inline-flex items-center gap-2">
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              Carregando documentos...
            </span>
          </section>
        ) : errorMessage ? (
          <section className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700">
            {errorMessage}
          </section>
        ) : (
          <section className="space-y-4">
            {documentGroups.length ? (
              documentGroups.map((group) => {
                const currentDocument = group.documento_atual;
                const canValidate =
                  currentDocument?.status === "ENVIADO" || currentDocument?.status === "EM_VALIDACAO";
                const hasHistory = group.versoes?.some((version) => version.status === "SUBSTITUIDO");
                const isExpanded = Boolean(expandedHistory[group.tipo_documento?.id]);

                return (
                  <article key={group.tipo_documento?.id} className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-3">
                          <h2 className="text-lg font-semibold text-gray-950">
                            {group.tipo_documento?.nome || "Documento"}
                          </h2>
                          <StatusBadge status={currentDocument?.status} />
                        </div>
                        {group.tipo_documento?.descricao && (
                          <p className="mt-2 text-sm text-gray-600">{group.tipo_documento.descricao}</p>
                        )}
                        {currentDocument ? (
                          <p className="mt-2 text-sm text-gray-500">
                            Versao {currentDocument.versao || 1} - {formatFileSize(currentDocument.tamanho_bytes)} -{" "}
                            {formatDate(currentDocument.enviado_em)}
                          </p>
                        ) : (
                          <p className="mt-2 text-sm text-gray-500">Nenhum arquivo atual enviado.</p>
                        )}
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {currentDocument?.arquivo && (
                          <a
                            href={getFileUrl(currentDocument.arquivo)}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
                          >
                            <ArrowDownTrayIcon className="h-4 w-4" />
                            Abrir PDF
                          </a>
                        )}

                        {hasHistory && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedHistory((current) => ({
                                ...current,
                                [group.tipo_documento.id]: !isExpanded,
                              }))
                            }
                            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
                          >
                            <ClockIcon className="h-4 w-4" />
                            Ver historico
                          </button>
                        )}
                      </div>
                    </div>

                    {currentDocument?.status === "REPROVADO" && (
                      <div className="mt-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 shrink-0" />
                        <div>
                          <p className="font-semibold">Documento reprovado</p>
                          <p className="mt-1">{currentDocument.motivo_reprovacao || "Motivo nao informado."}</p>
                          {currentDocument.observacoes && <p className="mt-1">{currentDocument.observacoes}</p>}
                        </div>
                      </div>
                    )}

                    {canValidate && (
                      <div className="mt-5 flex flex-col gap-3 border-t border-gray-200 pt-5 sm:flex-row sm:justify-end">
                        <button
                          type="button"
                          onClick={() => validateDocument(currentDocument, { status: "APROVADO" })}
                          disabled={validatingId === currentDocument.id}
                          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          {validatingId === currentDocument.id ? (
                            <ArrowPathIcon className="h-4 w-4 animate-spin" />
                          ) : (
                            <CheckCircleIcon className="h-4 w-4" />
                          )}
                          Aprovar
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setValidationError("");
                            setRejectionDocument(currentDocument);
                          }}
                          disabled={validatingId === currentDocument.id}
                          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-70"
                        >
                          <XCircleIcon className="h-4 w-4" />
                          Reprovar
                        </button>
                      </div>
                    )}

                    {isExpanded && <VersionHistory versions={group.versoes || []} />}
                  </article>
                );
              })
            ) : (
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-sm text-gray-600 shadow-sm">
                Nenhum documento enviado para este processo.
              </div>
            )}
          </section>
        )}
      </div>

      {rejectionDocument && (
        <RejectionModal
          document={rejectionDocument}
          isSubmitting={validatingId === rejectionDocument.id}
          errorMessage={validationError}
          onClose={() => {
            setRejectionDocument(null);
            setValidationError("");
          }}
          onConfirm={(payload) => validateDocument(rejectionDocument, { status: "REPROVADO", ...payload })}
        />
      )}
    </main>
  );
}
