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

export default function DocumentoUpload({ disabled = false }) {
  const inputRef = useRef(null);
  const [documentTypes, setDocumentTypes] = useState(DEFAULT_DOCUMENT_TYPES);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [feedback, setFeedback] = useState(null);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);

  const canSubmit = useMemo(
    () => !disabled && selectedFiles.length > 0 && selectedFiles.every((item) => item.tipoDocumentoId),
    [disabled, selectedFiles],
  );

  useEffect(() => {
    if (disabled) return;

    let isMounted = true;

    api
      .get("/documentos/tipos/")
      .then(({ data }) => {
        const apiTypes = data.tipos_documento || [];

        if (isMounted && apiTypes.length) {
          setDocumentTypes(apiTypes.map((type) => ({ id: String(type.id), nome: type.nome })));
        }
      })
      .catch(() => {
        if (isMounted) {
          setDocumentTypes(DEFAULT_DOCUMENT_TYPES);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [disabled]);

  const addFiles = (fileList) => {
    if (disabled || isUploading) return;

    const incomingFiles = Array.from(fileList || []);
    const pdfFiles = incomingFiles.filter(isPdf);
    const rejectedFiles = incomingFiles.filter((file) => !isPdf(file));

    if (rejectedFiles.length) {
      setFeedback({
        type: "error",
        message: "Apenas arquivos PDF podem ser selecionados.",
      });
    } else {
      setFeedback(null);
    }

    if (!pdfFiles.length) return;

    setSelectedFiles((currentFiles) => [
      ...currentFiles,
      ...pdfFiles.map((file) => ({
        id: `${file.name}-${file.size}-${file.lastModified}-${crypto.randomUUID()}`,
        file,
        tipoDocumentoId: documentTypes[0]?.id || "",
      })),
    ]);
  };

  const removeFile = (fileId) => {
    setSelectedFiles((currentFiles) => currentFiles.filter((item) => item.id !== fileId));
  };

  const updateDocumentType = (fileId, tipoDocumentoId) => {
    setSelectedFiles((currentFiles) =>
      currentFiles.map((item) => (item.id === fileId ? { ...item, tipoDocumentoId } : item)),
    );
  };

  const submitUpload = async (event) => {
    event.preventDefault();

    if (!canSubmit || isUploading || disabled) return;

    const formData = new FormData();
    selectedFiles.forEach((item) => {
      formData.append("arquivos", item.file);
      formData.append("tipos_documento", item.tipoDocumentoId);
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
      setSelectedFiles([]);
      setUploadProgress(100);
      setFeedback({
        type: "success",
        message: "Documentos recebidos com sucesso.",
      });

      if (inputRef.current) {
        inputRef.current.value = "";
      }
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
    addFiles(event.dataTransfer.files);
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm sm:p-6 lg:p-8">
      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-950">Envio de documentos</h2>
          <p className="mt-1 text-sm text-gray-600">
            Selecione os PDFs exigidos para a homologacao e confirme o envio.
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
          <p className="mt-1 text-sm text-gray-600">ou selecione multiplos arquivos no computador</p>
          <input
            ref={inputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="sr-only"
            onChange={(event) => addFiles(event.target.files)}
            disabled={isUploading || disabled}
          />
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={isUploading || disabled}
            className="mt-5 inline-flex min-h-11 items-center justify-center rounded-lg bg-[#006F46] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] focus:outline-none focus:ring-2 focus:ring-[#009966] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
          >
            Selecionar PDFs
          </button>
        </div>

        {selectedFiles.length > 0 && (
          <div className="overflow-hidden rounded-lg border border-gray-200">
            <div className="border-b border-gray-200 bg-gray-50 px-4 py-3 text-sm font-semibold text-gray-700">
              Arquivos selecionados
            </div>
            <ul className="divide-y divide-gray-200">
              {selectedFiles.map((item) => (
                <li key={item.id} className="grid gap-3 px-4 py-4 md:grid-cols-[1fr_220px_auto] md:items-center">
                  <div className="flex min-w-0 items-center gap-3">
                    <DocumentTextIcon className="h-6 w-6 shrink-0 text-[#006F46]" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-gray-900">{item.file.name}</p>
                      <p className="text-sm text-gray-500">{formatFileSize(item.file.size)}</p>
                    </div>
                  </div>
                  <select
                    value={item.tipoDocumentoId}
                    onChange={(event) => updateDocumentType(item.id, event.target.value)}
                    disabled={isUploading || disabled}
                    className="block w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20 disabled:cursor-not-allowed disabled:bg-gray-100"
                    aria-label={`Tipo do documento ${item.file.name}`}
                  >
                    {documentTypes.map((type) => (
                      <option key={type.id} value={type.id}>
                        {type.nome}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => removeFile(item.id)}
                    disabled={isUploading || disabled}
                    className="inline-flex min-h-10 items-center justify-center rounded-lg px-3 text-sm font-semibold text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    aria-label={`Remover ${item.file.name}`}
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </li>
              ))}
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
