import { useCallback, useEffect, useState } from "react";
import { ArrowDownIcon, ArrowUpIcon, PlusIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { useOutletContext } from "react-router-dom";
import { api } from "../config/api";
import Toast from "../components/Toast";

const simulatedUsers = [
  { id: 1, nome: "Rosa Ferreira", email: "rosa.ferreira@unimed.com.br", perfil: "EQUIPE_ADMINISTRATIVA", ativo: true },
  { id: 2, nome: "Thiago Lima", email: "thiago.lima@unimed.com.br", perfil: "EQUIPE_ADMINISTRATIVA", ativo: true },
  { id: 3, nome: "Camila Santos", email: "camila.santos@unimed.com.br", perfil: "ADMINISTRADOR", ativo: true },
];

function normalizeUser(item) {
  return {
    id: item.id,
    nome: item.nome || item.name || item.username || "Nome não disponível",
    email: item.email || item.username || "",
    perfil: item.perfil || item.role || "EQUIPE_ADMINISTRATIVA",
    ativo: typeof item.ativo === "boolean" ? item.ativo : true,
  };
}

export default function AdminFluxo() {
  const { user } = useOutletContext();
  const [availableUsers, setAvailableUsers] = useState([]);
  const [flow, setFlow] = useState([]);
  const [flowConfigId, setFlowConfigId] = useState(null);
  const [selectedUserId, setSelectedUserId] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState({ text: "", type: "success" });
  const [usingFallback, setUsingFallback] = useState(false);

  const loadData = useCallback(async () => {
    setIsLoading(true);
    setUsingFallback(false);

    try {
      const usersResponse = await api.get("/admin/config/usuarios/");
      const users = Array.isArray(usersResponse.data)
        ? usersResponse.data
        : usersResponse.data.usuarios || usersResponse.data.results || [];
      const activeUsers = users.map(normalizeUser).filter((item) => item.ativo);
      setAvailableUsers(activeUsers);

      const fluxoResponse = await api.get("/admin/config/fluxos/");
      const fluxoList = fluxoResponse.data?.fluxos || [];
      const activeFlow = fluxoList.find((item) => item.ativo) || fluxoList[0] || null;

      if (activeFlow) {
        setFlowConfigId(activeFlow.id);
        setFlow(
          (activeFlow.etapas || [])
            .sort((a, b) => a.ordem - b.ordem)
            .map((etapa) => activeUsers.find((userItem) => Number(userItem.id) === Number(etapa.aprovador)))
            .filter(Boolean),
        );
      } else {
        setFlow([]);
      }
    } catch {
      setAvailableUsers(simulatedUsers);
      setFlow([simulatedUsers[0], simulatedUsers[1]]);
      setUsingFallback(true);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const reservedIds = flow.map((item) => item.id);
  const selectableUsers = availableUsers.filter((item) => !reservedIds.includes(item.id));

  const addUserToFlow = () => {
    if (!selectedUserId) return;
    const userToAdd = availableUsers.find((item) => String(item.id) === selectedUserId);
    if (!userToAdd || reservedIds.includes(userToAdd.id)) {
      setMessage({ text: "O aprovador já faz parte do fluxo.", type: "error" });
      return;
    }

    setFlow((current) => [...current, userToAdd]);
    setSelectedUserId("");
    setMessage({ text: "Aprovador adicionado ao fluxo.", type: "success" });
  };

  const moveItem = (index, direction) => {
    setFlow((current) => {
      const next = [...current];
      const swapIndex = direction === "up" ? index - 1 : index + 1;
      if (swapIndex < 0 || swapIndex >= next.length) return next;
      [next[index], next[swapIndex]] = [next[swapIndex], next[index]];
      return next;
    });
  };

  const removeUser = (id) => {
    setFlow((current) => current.filter((item) => item.id !== id));
  };

  const saveFlow = async () => {
    if (!flow.length) {
      setMessage({ text: "Não é possível salvar um fluxo vazio.", type: "error" });
      return;
    }

    const payload = {
      nome: "Fluxo padrão de aprovação",
      ativo: true,
      etapas: flow.map((item, index) => ({ aprovador: item.id, ordem: index + 1 })),
    };

    setIsSaving(true);

    try {
      const response = flowConfigId
        ? await api.put(`/admin/config/fluxos/${flowConfigId}/`, payload)
        : await api.post("/admin/config/fluxos/", payload);

      setFlowConfigId(response.data.id);
      setMessage({ text: "Fluxo padrão salvo com sucesso.", type: "success" });
    } catch {
      setMessage({ text: "Falha ao salvar o fluxo. Tente novamente.", type: "error" });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <main className="mx-auto max-w-6xl">
      <div className="mb-6 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gray-500">Fluxo de aprovação</p>
            <h1 className="mt-3 text-3xl font-semibold text-gray-950">Construtor de fluxo padrão</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600">
              Configure a ordem dos aprovadores para que o processo siga de forma sequencial e clara.
            </p>
          </div>
          <div className="rounded-2xl border border-gray-200 bg-[#F0FDF4] px-4 py-3 text-sm font-semibold text-[#166534]">
            {user?.nome ? `Logado como ${user.nome}` : "Acesso administrador"}
          </div>
        </div>
      </div>

      <section className="grid gap-6 lg:grid-cols-[360px_1fr]">
        <aside className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="space-y-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-950">Seleção de aprovadores</h2>
              <p className="mt-2 text-sm text-gray-600">
                Escolha colaboradores ativos para compor o fluxo. O primeiro item será o primeiro a aprovar.
              </p>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">Aprovador</label>
              <div className="flex gap-3">
                <select
                  value={selectedUserId}
                  onChange={(event) => setSelectedUserId(event.target.value)}
                  className="min-w-0 flex-1 rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                >
                  <option value="">Selecione um aprovador</option>
                  {selectableUsers.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nome} — {item.perfil === "ADMINISTRADOR" ? "Administrador" : "Equipe administrativa"}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={addUserToFlow}
                  disabled={!selectedUserId}
                  className="inline-flex min-h-[52px] items-center justify-center rounded-2xl bg-[#006F46] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <PlusIcon className="mr-2 h-5 w-5" />
                  Adicionar
                </button>
              </div>
            </div>

            <div className="rounded-3xl border border-dashed border-gray-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-gray-800">Notas rápidas</p>
              <ul className="mt-3 space-y-2 text-sm text-gray-600">
                <li>O primeiro aprovador na lista será acionado primeiro.</li>
                <li>Use as setas para mover aprovadores para cima ou baixo.</li>
                <li>Não é permitido salvar um fluxo vazio.</li>
              </ul>
            </div>
          </div>
        </aside>

        <article className="rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-950">Ordem de aprovação</h2>
              <p className="mt-1 text-sm text-gray-600">
                Arraste a ordem com os botões ou remova aprovadores para ajustar o fluxo.
              </p>
            </div>
            <button
              type="button"
              onClick={saveFlow}
              disabled={isSaving || !flow.length}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#006F46] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : null}
              Salvar fluxo padrão
            </button>
          </div>

          {usingFallback && (
            <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Falha ao carregar dados reais. Exibindo fluxo de exemplo temporário.
            </div>
          )}

          <div className="relative mt-8">
            <span className="pointer-events-none absolute left-5 top-5 bottom-5 w-px bg-slate-200" />
            <div className="space-y-4">
              {flow.length === 0 ? (
                <div className="rounded-3xl border border-dashed border-gray-200 bg-slate-50 p-8 text-center text-sm text-gray-600">
                  Nenhum aprovador definido ainda. Adicione um aprovador para começar.
                </div>
              ) : (
                flow.map((item, index) => (
                  <div
                    key={item.id}
                    className="relative rounded-3xl border border-gray-200 bg-white p-5 shadow-sm"
                  >
                    <div className="absolute left-0 top-5 flex h-10 w-10 items-center justify-center rounded-full bg-[#006F46] text-white shadow-sm">
                      <span className="text-sm font-semibold">{index + 1}</span>
                    </div>
                    <div className="pl-16">
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <div>
                          <div className="flex items-center gap-2 text-sm font-semibold text-[#006F46]">
                            <span>{index === 0 ? "Primeiro aprovador" : index === flow.length - 1 ? "Último aprovador" : "Aprovador"}</span>
                          </div>
                          <p className="mt-2 text-lg font-semibold text-gray-950">{item.nome}</p>
                          <p className="text-sm text-gray-600">{item.email}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => moveItem(index, "up")}
                            disabled={index === 0}
                            className="inline-flex items-center justify-center rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition hover:border-[#006F46] hover:text-[#006F46] disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <ArrowUpIcon className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => moveItem(index, "down")}
                            disabled={index === flow.length - 1}
                            className="inline-flex items-center justify-center rounded-2xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 transition hover:border-[#006F46] hover:text-[#006F46] disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            <ArrowDownIcon className="h-4 w-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => removeUser(item.id)}
                            className="inline-flex items-center justify-center rounded-2xl border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-100"
                          >
                            Remover
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </article>
      </section>

      <Toast message={message.text} type={message.type} onClose={() => setMessage({ text: "", type: "success" })} />
    </main>
  );
}
