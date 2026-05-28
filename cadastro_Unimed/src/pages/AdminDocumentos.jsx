import { useCallback, useEffect, useState } from "react";
import { ShieldCheckIcon, DocumentTextIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { api } from "../config/api";
import ConfirmDialog from "../components/ConfirmDialog";
import Toast from "../components/Toast";

const simulatedDocuments = [
  { id: 1, nome: "Contrato Social", descricao: "Documento societário exigido para comprovar constituição da empresa.", ativo: true, obrigatorio: true },
  { id: 2, nome: "Certidão Negativa", descricao: "Documento comprovando regularidade fiscal do prestador.", ativo: true, obrigatorio: false },
  { id: 3, nome: "Alvará Sanitário", descricao: "Licença para atuação de estabelecimentos de saúde.", ativo: false, obrigatorio: true },
];

function normalizeDocument(item) {
  return {
    id: item.id,
    nome: item.nome || item.name || "Documento desconhecido",
    descricao: item.descricao || item.description || "",
    ativo: typeof item.ativo === "boolean" ? item.ativo : true,
    obrigatorio: typeof item.obrigatorio === "boolean" ? item.obrigatorio : false,
  };
}

export default function AdminDocumentos() {
  const { user } = useOutletContext();
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [toast, setToast] = useState({ message: "", type: "success" });
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingChange, setPendingChange] = useState(null);

  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/admin/config/documentos/");
      const apiDocuments = Array.isArray(data) ? data : data.documentos || data.results || [];
      setDocuments(apiDocuments.map(normalizeDocument));
    } catch {
      setDocuments(simulatedDocuments);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const toggleDocument = async (item, field) => {
    const nextValue = !item[field];
    const nextDocuments = documents.map((doc) => (doc.id === item.id ? { ...doc, [field]: nextValue } : doc));
    setDocuments(nextDocuments);
    setConfirmOpen(false);
    setPendingChange(null);

    try {
      await api.patch(`/admin/config/documentos/${item.id}/`, { [field]: nextValue });
      setToast({ message: "Alteração salva com sucesso.", type: "success" });
    } catch {
      setDocuments(documents);
      setToast({ message: "Falha ao salvar a alteração. Tente novamente.", type: "error" });
    }
  };

  const requestToggle = (item, field) => {
    setPendingChange({ item, field });
    setConfirmOpen(true);
  };

  const changeLabel = (field, value) => {
    if (field === "ativo") return value ? "Ativo" : "Inativo";
    if (field === "obrigatorio") return value ? "Obrigatório" : "Opcional";
    return "";
  };

  const pendingSubject = pendingChange?.field === "ativo" ? "ativar/desativar" : "alterar obrigatoriedade";

  return (
    <main className="mx-auto max-w-6xl">
      <div className="mb-6 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gray-500">Tipos de documento</p>
            <h1 className="mt-3 text-3xl font-semibold text-gray-950">Documentos exigidos</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600">
              Gerencie quais documentos estão ativos e quais são obrigatórios para prestadores.
            </p>
          </div>
          <div className="inline-flex items-center gap-3 rounded-2xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-700">
            <ShieldCheckIcon className="h-5 w-5 text-[#006F46]" />
            Acesso exclusivo para administrador
          </div>
        </div>
      </div>

      <section className="space-y-6">
        {isLoading ? (
          <div className="rounded-3xl border border-gray-200 bg-white p-6 text-center text-sm text-gray-600 shadow-sm">
            <span className="inline-flex items-center gap-2">
              <ArrowPathIcon className="h-4 w-4 animate-spin" />
              Carregando documentos...
            </span>
          </div>
        ) : (
          documents.map((doc) => (
            <article key={doc.id} className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.24em] text-[#006F46]">
                    <DocumentTextIcon className="h-4 w-4" />
                    {doc.nome}
                  </div>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-600">{doc.descricao}</p>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <button
                    type="button"
                    onClick={() => requestToggle(doc, "ativo")}
                    className={`inline-flex min-h-[52px] items-center justify-between rounded-2xl border p-4 text-left transition ${
                      doc.ativo ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-gray-200 bg-white text-gray-700 hover:border-[#006F46]"
                    }`}
                  >
                    <span>
                      <span className="block text-sm font-semibold">Status</span>
                      <span className="text-sm text-gray-600">{changeLabel("ativo", doc.ativo)}</span>
                    </span>
                    <span className={`inline-flex h-7 w-12 items-center rounded-full p-1 ${doc.ativo ? "bg-emerald-600" : "bg-gray-300"}`}>
                      <span className={`h-5 w-5 rounded-full bg-white transition ${doc.ativo ? "translate-x-5" : "translate-x-0"}`} />
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => requestToggle(doc, "obrigatorio")}
                    className={`inline-flex min-h-[52px] items-center justify-between rounded-2xl border p-4 text-left transition ${
                      doc.obrigatorio ? "border-amber-200 bg-amber-50 text-amber-900" : "border-gray-200 bg-white text-gray-700 hover:border-[#006F46]"
                    }`}
                  >
                    <span>
                      <span className="block text-sm font-semibold">Obrigatoriedade</span>
                      <span className="text-sm text-gray-600">{changeLabel("obrigatorio", doc.obrigatorio)}</span>
                    </span>
                    <span className={`inline-flex h-7 w-12 items-center rounded-full p-1 ${doc.obrigatorio ? "bg-amber-600" : "bg-gray-300"}`}>
                      <span className={`h-5 w-5 rounded-full bg-white transition ${doc.obrigatorio ? "translate-x-5" : "translate-x-0"}`} />
                    </span>
                  </button>
                </div>
              </div>
            </article>
          ))
        )}
      </section>

      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: "", type: "success" })} />

      <ConfirmDialog
        open={confirmOpen}
        title="Confirmar alteração"
        description={`Você tem certeza que deseja ${pendingSubject} para o documento ${pendingChange?.item?.nome}?`}
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => toggleDocument(pendingChange.item, pendingChange.field)}
      />
    </main>
  );
}
