import { useCallback, useEffect, useMemo, useState } from "react";
import { Dialog } from "@headlessui/react";
import { PlusIcon, UserPlusIcon } from "@heroicons/react/24/outline";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useOutletContext } from "react-router-dom";
import { api } from "../config/api";
import ConfirmDialog from "../components/ConfirmDialog";
import Toast from "../components/Toast";

const userSchema = z.object({
  nome: z.string().min(2, "Informe o nome do usuário."),
  email: z.string().email("Informe um e-mail válido."),
  perfil: z.enum(["EQUIPE_ADMINISTRATIVA", "ADMINISTRADOR"]),
  password: z.string().min(8, "A senha precisa ter pelo menos 8 caracteres."),
});

const simulatedUsers = [
  { id: 1, nome: "Rosa Ferreira", email: "rosa.ferreira@unimed.com.br", perfil: "EQUIPE_ADMINISTRATIVA", ativo: true },
  { id: 2, nome: "Thiago Lima", email: "thiago.lima@unimed.com.br", perfil: "EQUIPE_ADMINISTRATIVA", ativo: true },
  { id: 3, nome: "Camila Santos", email: "camila.santos@unimed.com.br", perfil: "ADMINISTRADOR", ativo: true },
];

function normalizeUser(user) {
  return {
    id: user.id,
    nome: user.nome || user.name || "-",
    email: user.email || user.username || "-",
    perfil: user.perfil || user.role || "EQUIPE_ADMINISTRATIVA",
    ativo: typeof user.ativo === "boolean" ? user.ativo : true,
  };
}

export default function AdminUsuarios() {
  const { user } = useOutletContext();
  const [users, setUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingUser, setPendingUser] = useState(null);
  const [toast, setToast] = useState({ message: "", type: "success" });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(userSchema),
    defaultValues: { nome: "", email: "", perfil: "EQUIPE_ADMINISTRATIVA", password: "" },
  });

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get("/admin/config/usuarios/");
      const apiUsers = Array.isArray(data) ? data : data.usuarios || data.results || [];
      setUsers(apiUsers.map(normalizeUser));
    } catch {
      setUsers(simulatedUsers);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const pendingConfirmation = (formData) => {
    setPendingUser(formData);
    setConfirmOpen(true);
  };

  const createUser = async () => {
    if (!pendingUser) return;

    const newUser = {
      id: Date.now(),
      ...pendingUser,
      ativo: true,
    };

    const payload = {
      email: pendingUser.email,
      perfil: pendingUser.perfil,
      password: pendingUser.password,
      first_name: pendingUser.nome,
    };

    try {
      setUsers((current) => [newUser, ...current]);
      setConfirmOpen(false);
      setModalOpen(false);
      reset();

      await api.post("/admin/config/usuarios/", payload);
      setToast({ message: "Usuário criado com sucesso.", type: "success" });
    } catch (error) {
      setUsers((current) => current.filter((item) => item.id !== newUser.id));
      setToast({ message: "Não foi possível criar o usuário. Tente novamente.", type: "error" });
    } finally {
      setPendingUser(null);
    }
  };

  const userList = useMemo(() => users, [users]);

  return (
    <main className="mx-auto max-w-6xl">
      <div className="mb-6 rounded-3xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gray-500">Usuários internos</p>
            <h1 className="mt-3 text-3xl font-semibold text-gray-950">Equipe de análise</h1>
            <p className="mt-2 max-w-2xl text-sm text-gray-600">
              Adicione e gerencie os colaboradores que terão acesso à área administrativa.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-2xl bg-[#006F46] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C]"
          >
            <PlusIcon className="h-5 w-5" />
            Novo usuário
          </button>
        </div>
      </div>

      <section className="rounded-3xl border border-gray-200 bg-white shadow-sm">
        <div className="border-b border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-950">Equipe cadastrada</h2>
          <p className="mt-1 text-sm text-gray-600">Veja os usuários que podem acessar e analisar processos.</p>
        </div>

        <div className="overflow-x-auto p-6">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Nome</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">E-mail</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Perfil</th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-sm text-gray-600">
                    Carregando usuários...
                  </td>
                </tr>
              ) : userList.length > 0 ? (
                userList.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 text-sm text-gray-950">{item.nome}</td>
                    <td className="px-4 py-4 text-sm text-gray-600">{item.email}</td>
                    <td className="px-4 py-4 text-sm text-gray-700">{item.perfil === "ADMINISTRADOR" ? "Administrador" : "Equipe administrativa"}</td>
                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                          item.ativo ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {item.ativo ? "Ativo" : "Inativo"}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="4" className="px-4 py-8 text-center text-sm text-gray-600">
                    Nenhum usuário cadastrado ainda.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      <Toast message={toast.message} type={toast.type} onClose={() => setToast({ message: "", type: "success" })} />

      <Dialog open={modalOpen} onClose={() => setModalOpen(false)} className="relative z-50">
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <div className="w-full max-w-2xl rounded-3xl border border-gray-200 bg-white p-6 shadow-xl shadow-slate-900/10">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gray-500">Novo usuário</p>
                <h2 className="mt-2 text-2xl font-semibold text-gray-950">Cadastrar colaborador</h2>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-full bg-gray-100 p-2 text-gray-600 transition hover:bg-gray-200"
              >
                ✕
              </button>
            </div>

            <form className="mt-6 space-y-5" onSubmit={handleSubmit(pendingConfirmation)} noValidate>
              <div>
                <label htmlFor="nome" className="block text-sm font-medium text-gray-700">
                  Nome completo
                </label>
                <input
                  id="nome"
                  type="text"
                  {...register("nome")}
                  className="mt-2 block w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                />
                {errors.nome?.message && <p className="mt-2 text-sm text-rose-600">{errors.nome.message}</p>}
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  E-mail
                </label>
                <input
                  id="email"
                  type="email"
                  {...register("email")}
                  className="mt-2 block w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                />
                {errors.email?.message && <p className="mt-2 text-sm text-rose-600">{errors.email.message}</p>}
              </div>

              <div>
                <label htmlFor="perfil" className="block text-sm font-medium text-gray-700">
                  Perfil
                </label>
                <select
                  id="perfil"
                  {...register("perfil")}
                  className="mt-2 block w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                >
                  <option value="EQUIPE_ADMINISTRATIVA">Equipe administrativa</option>
                  <option value="ADMINISTRADOR">Administrador</option>
                </select>
                {errors.perfil?.message && <p className="mt-2 text-sm text-rose-600">{errors.perfil.message}</p>}
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                  Senha
                </label>
                <input
                  id="password"
                  type="password"
                  {...register("password")}
                  className="mt-2 block w-full rounded-2xl border border-gray-300 bg-white px-4 py-3 text-sm text-gray-900 shadow-sm outline-none transition focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20"
                />
                {errors.password?.message && <p className="mt-2 text-sm text-rose-600">{errors.password.message}</p>}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-2xl bg-[#006F46] px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] disabled:cursor-not-allowed disabled:opacity-70"
              >
                <UserPlusIcon className="h-5 w-5" />
                Criar usuário
              </button>
            </form>
          </div>
        </div>
      </Dialog>

      <ConfirmDialog
        open={confirmOpen}
        title="Confirmar criação"
        description={`Deseja criar o usuário ${pendingUser?.nome} com o perfil ${pendingUser?.perfil === "ADMINISTRADOR" ? "Administrador" : "Equipe administrativa"}?`}
        onClose={() => setConfirmOpen(false)}
        onConfirm={createUser}
      />
    </main>
  );
}
