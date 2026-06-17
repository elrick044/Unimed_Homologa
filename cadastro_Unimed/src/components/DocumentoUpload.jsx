import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  CloudArrowUpIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { api } from "../config/api";

const DEFAULT_DOCUMENT_TYPES = [
  { id: "1", nome: "Contrato Social" },
  { id: "2", nome: "Comprovante de Endereco" },
  { id: "3", nome: "Alvara de Funcionamento" },
  { id: "4", nome: "Certidao Negativa" },
];

const EMPTY_TYPE_IDS = [];

function formatFileSize(bytes) {
  if (!bytes) return "0 KB";

  const units = ["bytes", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const size = bytes / 1024 ** index;

  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function isPdf(file) {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

function getApiMessage(data) {
  if (Array.isArray(data?.arquivos)) return data.arquivos.join(" ");
  if (Array.isArray(data?.tipos_documento)) return data.tipos_documento.join(" ");
  if (Array.isArray(data?.arquivo)) return data.arquivo.join(" ");
  if (Array.isArray(data?.tipo_documento)) return data.tipo_documento.join(" ");
  if (typeof data?.detail === "string") return data.detail;

  return "Nao foi possivel enviar os documentos. Tente novamente.";
}

export default function DocumentoUpload({
  disabled = false,
  documentTypes: providedDocumentTypes,
  hiddenTypeIds = EMPTY_TYPE_IDS,
  onUploadSuccess,
}) {
  const inputRefs = useRef({});
  const [apiDocumentTypes, setApiDocumentTypes] = useState(DEFAULT_DOCUMENT_TYPES);
  const [filesByTypeId, setFilesByTypeId] = useState({});
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);

  const hiddenTypeSet = useMemo(() => new Set(hiddenTypeIds.map(String)), [hiddenTypeIds]);

  const documentTypes = useMemo(() => {
    const sourceTypes = providedDocumentTypes?.length ? providedDocumentTypes : apiDocumentTypes;
    return sourceTypes
      .map((type) => ({ ...type, id: String(type.id) }))
      .filter((type) => !hiddenTypeSet.has(String(type.id)));
  }, [apiDocumentTypes, hiddenTypeSet, providedDocumentTypes]);

  const canSubmit = useMemo(
    () =>
      !disabled &&
      documentTypes.length > 0 &&
      Object.values(filesByTypeId).some((file) => Boolean(file)),
    [disabled, documentTypes.length, filesByTypeId],
  );

  useEffect(() => {
    if (disabled || providedDocumentTypes?.length) return;

    let isMounted = true;

    api
      .get("/documentos/tipos/")
      .then(({ data }) => {
        const apiTypes = data.tipos_documento || [];

        if (isMounted && apiTypes.length) {
          setApiDocumentTypes(apiTypes);
        }
      })
      .catch(() => {
        if (isMounted) {
          setApiDocumentTypes(DEFAULT_DOCUMENT_TYPES);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [disabled, providedDocumentTypes]);

  useEffect(() => {
    const validTypeIds = new Set(documentTypes.map((type) => String(type.id)));

    setFilesByTypeId((currentFiles) =>
      Object.fromEntries(
        Object.entries(currentFiles).filter(([typeId]) => validTypeIds.has(String(typeId))),
      ),
    );
  }, [documentTypes]);

  const selectFileForType = (typeId, file) => {
    if (disabled || isUploading || !file) return;

    if (!isPdf(file)) {
      setFeedback({
        type: "error",
        message: "Apenas arquivos PDF podem ser selecionados.",
      });
      return;
    }

    setFilesByTypeId((currentFiles) => ({
      ...currentFiles,
      [String(typeId)]: file,
    }));
    setFeedback(null);
  };

  const addDroppedFiles = (fileList) => {
    if (disabled || isUploading || documentTypes.length === 0) return;

    const incomingFiles = Array.from(fileList || []);
    const pdfFiles = incomingFiles.filter(isPdf);
    const rejectedFiles = incomingFiles.filter((file) => !isPdf(file));

    if (rejectedFiles.length) {
      setFeedback({
        type: "error",
        message: "Apenas arquivos PDF podem ser selecionados.",
      });
    }

    if (!pdfFiles.length) return;

    setFilesByTypeId((currentFiles) => {
      const nextFiles = { ...currentFiles };
      const availableTypes = documentTypes.filter((type) => !nextFiles[String(type.id)]);

      pdfFiles.slice(0, availableTypes.length).forEach((file, index) => {
        nextFiles[String(availableTypes[index].id)] = file;
      });

      return nextFiles;
    });

    setFeedback(
      pdfFiles.length > documentTypes.length
        ? {
            type: "error",
            message: "Alguns arquivos nao foram adicionados porque nao havia campos livres.",
          }
        : null,
    );
  };

  const removeFile = (typeId) => {
    setFilesByTypeId((currentFiles) => {
      const nextFiles = { ...currentFiles };
      delete nextFiles[String(typeId)];
      return nextFiles;
    });

    if (inputRefs.current[String(typeId)]) {
      inputRefs.current[String(typeId)].value = "";
    }
  };

  const submitUpload = async (event) => {
    event.preventDefault();

    if (!canSubmit || isUploading || disabled) return;

    const formData = new FormData();
    documentTypes.forEach((type) => {
      const file = filesByTypeId[String(type.id)];

      if (file) {
        formData.append("arquivos", file);
        formData.append("tipos_documento", type.id);
      }
    });

    setIsUploading(true);
    setUploadProgress(0);
    setFeedback(null);

    try {
      const { data } = await api.post("/documentos/upload/", formData, {
        onUploadProgress: (progressEvent) => {
          if (!progressEvent.total) return;
          setUploadProgress(Math.round((progressEvent.loaded * 100) / progressEvent.total));
        },
      });

      setUploadedDocuments(data.documentos || []);
      setFilesByTypeId({});
      setUploadProgress(100);
      setFeedback({
        type: "success",
        message: "Documentos recebidos com sucesso.",
      });
      onUploadSuccess?.(data.documentos || []);

      Object.values(inputRefs.current).forEach((input) => {
        if (input) input.value = "";
      });
    } catch (error) {
      setFeedback({
        type: "error",
        message: getApiMessage(error.response?.data),
      });
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (event) => {
    event.preventDefault();
    setIsDragging(false);
    addDroppedFiles(event.dataTransfer.files);
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm sm:p-6 lg:p-8">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-950">Envio de documentos</h2>
          <p className="mt-1 text-sm text-gray-600">
            {documentTypes.length
              ? "Anexe o PDF correspondente em cada documento exigido e confirme o envio."
              : "Nao ha novos tipos de documento pendentes para envio."}
          </p>
        </div>
      </div>

      <form onSubmit={submitUpload} className="space-y-6">
        <div
          onDragEnter={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={(event) => {
            event.preventDefault();
            setIsDragging(false);
          }}
          onDrop={handleDrop}
          className={`flex min-h-52 flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-10 text-center transition ${
            isDragging ? "border-[#009966] bg-emerald-50" : "border-gray-300 bg-slate-50"
          }`}
        >
          <CloudArrowUpIcon className="h-12 w-12 text-[#006F46]" />
          <p className="mt-4 text-base font-semibold text-gray-900">Solte os PDFs aqui</p>
          <p className="mt-1 text-sm text-gray-600">ou use o campo de arquivo de cada documento abaixo</p>
        </div>

        {documentTypes.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div className="border-b border-gray-200 bg-gray-50 px-4 py-3 text-sm font-semibold text-gray-700">
              Documentos para envio
            </div>
            <ul className="divide-y divide-gray-200">
              {documentTypes.map((type) => {
                const selectedFile = filesByTypeId[String(type.id)];

                return (
                <li key={type.id} className="grid gap-4 px-4 py-4 lg:grid-cols-[1fr_280px_auto] lg:items-center">
                  <div className="flex min-w-0 items-center gap-3">
                    <DocumentTextIcon className="h-6 w-6 shrink-0 text-[#006F46]" />
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900">{type.nome}</p>
                      {type.descricao && <p className="mt-1 text-sm text-gray-500">{type.descricao}</p>}
                      {selectedFile && (
                        <p className="mt-2 truncate text-sm text-gray-600">
                          {selectedFile.name} - {formatFileSize(selectedFile.size)}
                        </p>
                      )}
                    </div>
                  </div>
                  <label className="block">
                    <span className="sr-only">Arquivo para {type.nome}</span>
                    <input
                      ref={(input) => {
                        inputRefs.current[String(type.id)] = input;
                      }}
                      type="file"
                      accept="application/pdf,.pdf"
                      onChange={(event) => selectFileForType(type.id, event.target.files?.[0])}
                      disabled={isUploading || disabled}
                      className="block w-full text-sm text-gray-700 file:mr-4 file:min-h-10 file:rounded-lg file:border-0 file:bg-[#006F46] file:px-4 file:text-sm file:font-semibold file:text-white hover:file:bg-[#00583C] disabled:cursor-not-allowed disabled:opacity-70"
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() => removeFile(type.id)}
                    disabled={isUploading || disabled || !selectedFile}
                    className="inline-flex min-h-10 items-center justify-center rounded-lg px-3 text-sm font-semibold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    aria-label={`Remover arquivo de ${type.nome}`}
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </li>
                );
              })}
            </ul>
          </div>
        )}

        {isUploading && (
          <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
            <div className="mb-2 flex items-center justify-between text-sm font-medium text-gray-700">
              <span>Enviando documentos</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-gray-200">
              <div className="h-full rounded-full bg-[#009966]" style={{ width: `${uploadProgress}%` }} />
            </div>
          </div>
        )}

        {feedback && (
          <div
            className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${
              feedback.type === "success"
                ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                : "border-red-200 bg-red-50 text-red-700"
            }`}
            role="alert"
          >
            {feedback.type === "success" ? (
              <CheckCircleIcon className="mt-0.5 h-5 w-5 shrink-0" />
            ) : (
              <ExclamationTriangleIcon className="mt-0.5 h-5 w-5 shrink-0" />
            )}
            <span>{feedback.message}</span>
          </div>
        )}

        {uploadedDocuments.length > 0 && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
            <h3 className="text-sm font-semibold text-emerald-900">Recebidos pela API</h3>
            <ul className="mt-3 space-y-2">
              {uploadedDocuments.map((documento) => (
                <li key={documento.id} className="flex items-center justify-between gap-3 text-sm text-emerald-900">
                  <span className="truncate">{documento.tipo_documento?.nome || documento.arquivo}</span>
                  <span className="shrink-0">{formatFileSize(documento.tamanho_bytes)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex justify-end border-t border-gray-200 pt-6">
          <button
            type="submit"
            disabled={!canSubmit || isUploading || disabled}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#006F46] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] focus:outline-none focus:ring-2 focus:ring-[#009966] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isUploading && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            {isUploading ? "Enviando" : "Enviar documentos"}
          </button>
        </div>
      </form>
    </section>
  );
}
