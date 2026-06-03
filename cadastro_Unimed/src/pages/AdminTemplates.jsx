import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Dialog } from "@headlessui/react";
import { PlusIcon, PencilSquareIcon, DocumentDuplicateIcon } from "@heroicons/react/24/outline";
import { api } from "../config/api";
import Toast from "../components/Toast";

const dynamicVariables = [
  { tag: "{{ razao_social }}", label: "Razão social" },
  { tag: "{{ cnpj }}", label: "CNPJ" },
  { tag: "{{ endereco }}", label: "Endereço" },
  { tag: "{{ nome_responsavel }}", label: "Nome do responsável" },
  { tag: "{{ email }}", label: "E-mail" },
];

const emptyTemplate = {
  nome: "",
  conteudo_html: "",
  ativo: true,
};

export default function AdminTemplates() {
  const [templates, setTemplates] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [editorOpen, setEditorOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [draft, setDraft] = useState(emptyTemplate);
  const [toast, setToast] = useState({ message: "", type: "success" });
  const [isSaving, setIsSaving] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const editorRef = useRef(null);
  const editorInitialized = useRef(false);

  const loadTemplates = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/admin/config/templates/");
      setTemplates(Array.isArray(data.templates) ? data.templates : []);
    } catch (error) {
      setTemplates([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const openEditor = (template = null) => {
    setSelectedTemplate(template);
    setDraft(
      template
        ? {
            nome: template.nome,
            conteudo_html: template.conteudo_html || "",
            ativo: template.ativo,
          }
        : emptyTemplate,
    );
    setEditorOpen(true);
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setSelectedTemplate(null);
    setDraft(emptyTemplate);
    setHelpOpen(false);
  };

  const execEditorCommand = (command, value = null) => {
    document.execCommand(command, false, value);
    const html = editorRef.current?.innerHTML || "";
    setDraft((current) => ({ ...current, conteudo_html: html }));
  };

  const updateEditorContent = () => {
    const html = editorRef.current?.innerHTML || "";
    setDraft((current) => ({ ...current, conteudo_html: html }));
  };

  useEffect(() => {
    if (!editorOpen) {
      editorInitialized.current = false;
      return;
    }

    if (editorRef.current && !editorInitialized.current) {
      editorRef.current.innerHTML = draft.conteudo_html || "";
      editorInitialized.current = true;
    }
  }, [editorOpen]);

  const handleSave = async () => {
    if (!draft.nome.trim()) {
      setToast({ message: "Informe um nome para o template.", type: "error" });
      return;
    }

    if (!draft.conteudo_html.trim()) {
      setToast({ message: "O conteúdo do template não pode ficar vazio.", type: "error" });
      return;
    }

    if (selectedTemplate?.ativo) {
      const confirmed = window.confirm(
        "Salvar um template ativo gerará uma nova versão. Deseja continuar?",
      );
      if (!confirmed) {
        return;
      }
    }

    setIsSaving(true);

    try {
      if (selectedTemplate) {
        await api.put(`/admin/config/templates/${selectedTemplate.id}/`, {
          nome: draft.nome,
          conteudo_html: draft.conteudo_html,
          ativo: draft.ativo,
        });
        setToast({ message: "Template atualizado com sucesso.", type: "success" });
      } else {
        await api.post("/admin/config/templates/", {
          nome: draft.nome,
          conteudo_html: draft.conteudo_html,
          ativo: draft.ativo,
        });
        setToast({ message: "Template criado com sucesso.", type: "success" });
      }
      closeEditor();
      loadTemplates();
    } catch (error) {
      setToast({ message: "Não foi possível salvar o template. Tente novamente.", type: "error" });
    } finally {
      setIsSaving(false);
    }
  };

  const copyVariable = async (value) => {
    try {
      await navigator.clipboard.writeText(value);
      setToast({ message: `Copiado ${value} para a área de transferência.`, type: "success" });
    } catch {
      setToast({ message: "Não foi possível copiar a variável.", type: "error" });
    }
  };

  const historyForSelected = useMemo(() => {
    if (!selectedTemplate) return [];
    return templates
      .filter((item) => item.nome === selectedTemplate.nome)
      .sort((a, b) => b.versao - a.versao);
  }, [selectedTemplate, templates]);

  return (
    <main className="mx-auto max-w-7xl">
      <div className="mb-6 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gray-500">Templates de minuta</p>
            <h1 className="mt-3 text-3xl font-semibold text-gray-950">Gestão de templates de contrato</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600">
              Crie, edite e versionamento os modelos usados para gerar minutas contratuais automaticamente.
            </p>
          </div>

          <button
            type="button"
            onClick={() => openEditor(null)}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#006F46] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C]"
          >
            <PlusIcon className="h-5 w-5" />
            Novo template
          </button>
        </div>
      </div>

      <section className="rounded-3xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-950">Templates cadastrados</h2>
              <p className="mt-1 text-sm text-gray-600">Veja as versões ativas e inativas dos templates de contrato.</p>
            </div>
          </div>
        </div>

        <div className="overflow-x-auto p-6">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Nome</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Versão</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Status</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Atualizado em</th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-gray-500">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-sm text-gray-600">
                    Carregando templates...
                  </td>
                </tr>
              ) : templates.length > 0 ? (
                templates.map((template) => (
                  <tr key={template.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 text-sm text-gray-950">{template.nome}</td>
                    <td className="px-4 py-4 text-sm text-gray-600">{template.versao}</td>
                    <td className="px-4 py-4 text-sm">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                          template.ativo ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {template.ativo ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm text-gray-600">
                      {new Date(template.atualizado_em).toLocaleDateString("pt-BR", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                      })}
                    </td>
                    <td className="px-4 py-4 text-right">
                      <button
                        type="button"
                        onClick={() => openEditor(template)}
                        className="inline-flex items-center justify-center rounded-2xl border border-gray-200 bg-white px-3 py-2 text-xs font-semibold text-gray-700 transition hover:border-[#006F46] hover:text-[#006F46]"
                      >
                        <PencilSquareIcon className="mr-2 h-4 w-4" />
                        Editar
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-4 py-8 text-center text-sm text-gray-600">
                    Nenhum template cadastrado ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: "", type: "success" })} />

      <Dialog open={editorOpen} onClose={closeEditor} className="relative z-50">
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-start justify-center overflow-y-auto p-4 pt-16">
          <Dialog.Panel className="w-full max-w-6xl rounded-3xl border border-gray-200 bg-white p-6 shadow-xl shadow-slate-900/10">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <Dialog.Title className="text-2xl font-semibold text-gray-950">
                  {selectedTemplate ? "Editar template" : "Novo template"}
                </Dialog.Title>
                <p className="mt-2 text-sm text-gray-600">
                  {selectedTemplate
                    ? "Editar o contrato criará uma nova versão caso o template ativo seja salvo."
                    : "Crie um novo template de contrato que poderá ser usado na geração de minutas."}
                </p>
              </div>
              <button
                type="button"
                onClick={closeEditor}
                className="rounded-full bg-gray-100 p-2 text-gray-600 transition hover:bg-gray-200"
              >
                ✕
              </button>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_0.9fr]">
              <div className="space-y-6">
                <div>
                  <label htmlFor="templateName" className="block text-sm font-medium text-gray-700">
                    Nome do template
                  </label>
                  <input
                    id="templateName"
                    type="text"
                    value={draft.nome}
                    onChange={(event) => setDraft((current) => ({ ...current, nome: event.target.value }))}
                    className="mt-2 block w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <label className="block text-sm font-medium text-gray-700">Conteúdo do template</label>
                    <button
                      type="button"
                      onClick={() => setHelpOpen((current) => !current)}
                      className="text-sm font-semibold text-[#006F46] hover:text-[#00583C]"
                    >
                      {helpOpen ? "Esconder variáveis" : "Ajuda de variáveis"}
                    </button>
                  </div>
                  <div className="mt-3 rounded-3xl border border-gray-200 bg-white shadow-sm">
                    <div className="flex flex-wrap gap-2 border-b border-gray-200 bg-gray-50 p-3">
                      <button
                        type="button"
                        onClick={() => execEditorCommand("bold")}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        Negrito
                      </button>
                      <button
                        type="button"
                        onClick={() => execEditorCommand("italic")}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        Itálico
                      </button>
                      <button
                        type="button"
                        onClick={() => execEditorCommand("underline")}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        Sublinhado
                      </button>
                      <button
                        type="button"
                        onClick={() => execEditorCommand("insertUnorderedList")}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        Lista
                      </button>
                      <button
                        type="button"
                        onClick={() => execEditorCommand("insertOrderedList")}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        Numeração
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          const url = window.prompt("Digite a URL:", "https://");
                          if (url) execEditorCommand("createLink", url);
                        }}
                        className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs font-semibold text-gray-700 hover:bg-gray-100"
                      >
                        Link
                      </button>
                    </div>
                    <div
                      ref={editorRef}
                      contentEditable
                      suppressContentEditableWarning
                      onInput={updateEditorContent}
                      className="min-h-[320px] rounded-b-3xl bg-white p-4 text-sm text-gray-900 outline-none focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <input
                    id="activeTemplate"
                    type="checkbox"
                    checked={draft.ativo}
                    onChange={(event) => setDraft((current) => ({ ...current, ativo: event.target.checked }))}
                    className="h-4 w-4 rounded border-gray-300 text-[#006F46] focus:ring-[#006F46]"
                  />
                  <label htmlFor="activeTemplate" className="text-sm text-gray-700">
                    Definir como template ativo para novas minutas
                  </label>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:justify-between">
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={isSaving}
                    className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#006F46] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {selectedTemplate ? "Salvar versão" : "Criar template"}
                  </button>
                  {selectedTemplate && (
                    <div className="rounded-3xl border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
                      Ao salvar um template ativo, uma nova versão será criada e a versão anterior será inativada.
                    </div>
                  )}
                </div>
              </div>

              <aside className="space-y-6 rounded-3xl border border-gray-200 bg-[#FAFAFA] p-6 shadow-sm">
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold text-gray-950">Ajuda de variáveis</h3>
                  <p className="text-sm text-gray-600">
                    Clique para copiar as tags suportadas e cole no corpo do contrato.
                  </p>
                </div>

                <div className="space-y-3">
                  {dynamicVariables.map((variable) => (
                    <button
                      type="button"
                      key={variable.tag}
                      onClick={() => copyVariable(variable.tag)}
                      className="w-full rounded-2xl border border-gray-200 bg-white px-4 py-3 text-left text-sm text-gray-700 shadow-sm transition hover:border-[#006F46] hover:text-[#006F46]"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <p className="font-medium">{variable.label}</p>
                          <p className="text-xs text-gray-500">{variable.tag}</p>
                        </div>
                        <DocumentDuplicateIcon className="h-5 w-5 text-gray-400" />
                      </div>
                    </button>
                  ))}
                </div>

                {selectedTemplate && historyForSelected.length > 0 && (
                  <div className="rounded-3xl border border-gray-200 bg-white p-4">
                    <h3 className="text-sm font-semibold text-gray-900">Histórico de versões</h3>
                    <div className="mt-4 space-y-3">
                      {historyForSelected.map((version) => (
                        <div key={version.id} className="rounded-2xl border border-gray-100 bg-gray-50 p-3 text-sm">
                          <p className="font-semibold text-gray-900">Versão {version.versao}</p>
                          <p className="text-gray-600">{version.ativo ? "Ativa" : "Inativa"}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </aside>
            </div>
          </Dialog.Panel>
        </div>
      </Dialog>
    </main>
  );
}
