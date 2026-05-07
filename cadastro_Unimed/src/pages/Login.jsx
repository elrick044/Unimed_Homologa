import { useState } from "react";
import { ArrowPathIcon, EnvelopeIcon, LockClosedIcon } from "@heroicons/react/24/outline";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { api } from "../config/api";

const inputClass =
  "block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20 disabled:cursor-not-allowed disabled:bg-gray-100";

function parseJwt(token) {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      window
        .atob(base64)
        .split("")
        .map((char) => `%${`00${char.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join(""),
    );

    return JSON.parse(jsonPayload);
  } catch {
    return {};
  }
}

function getRedirectPath(profile) {
  if (profile === "EQUIPE_ADMINISTRATIVA" || profile === "ADMINISTRADOR") {
    return "/admin/processos";
  }

  return "/prestador/dashboard";
}

function getApiMessage(data) {
  if (Array.isArray(data?.non_field_errors)) return data.non_field_errors.join(" ");
  if (Array.isArray(data?.detail)) return data.detail.join(" ");
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.email)) return data.email.join(" ");
  if (Array.isArray(data?.senha)) return data.senha.join(" ");

  return "Nao foi possivel autenticar. Confira seus dados e tente novamente.";
}

export default function Login() {
  const navigate = useNavigate();
  const [errorMessage, setErrorMessage] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      email: "",
      senha: "",
    },
  });

  const onSubmit = async (formData) => {
    setErrorMessage("");

    try {
      const { data } = await api.post("/auth/login/", {
        email: formData.email.trim(),
        senha: formData.senha,
      });

      localStorage.setItem("access_token", data.access);
      localStorage.setItem("refresh_token", data.refresh);

      const tokenPayload = parseJwt(data.access);
      const profile = data.perfil || data.profile || tokenPayload.perfil || tokenPayload.profile || "PRESTADOR";

      localStorage.setItem("user_profile", profile);
      navigate(getRedirectPath(profile), { replace: true });
    } catch (error) {
      setErrorMessage(getApiMessage(error.response?.data));
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 sm:px-6 lg:px-8">
      <section className="mx-auto max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-gray-950">Login</h1>
          <p className="mt-2 text-sm text-gray-600">
            Acesse a plataforma de homologacao com seu e-mail e senha.
          </p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
          <div className="space-y-2">
            <label htmlFor="email" className="block text-sm font-medium text-gray-700">
              E-mail
            </label>
            <div className="relative">
              <EnvelopeIcon className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                id="email"
                type="email"
                autoComplete="email"
                className={`${inputClass} pl-10`}
                disabled={isSubmitting}
                {...register("email", {
                  required: "Informe seu e-mail.",
                  pattern: {
                    value: /^\S+@\S+\.\S+$/,
                    message: "Informe um e-mail valido.",
                  },
                })}
              />
            </div>
            {errors.email?.message && <p className="text-sm text-red-600">{errors.email.message}</p>}
          </div>

          <div className="space-y-2">
            <label htmlFor="senha" className="block text-sm font-medium text-gray-700">
              Senha
            </label>
            <div className="relative">
              <LockClosedIcon className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
              <input
                id="senha"
                type="password"
                autoComplete="current-password"
                className={`${inputClass} pl-10`}
                disabled={isSubmitting}
                {...register("senha", {
                  required: "Informe sua senha.",
                })}
              />
            </div>
            {errors.senha?.message && <p className="text-sm text-red-600">{errors.senha.message}</p>}
          </div>

          {errorMessage && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-[#006F46] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] focus:outline-none focus:ring-2 focus:ring-[#009966] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
            {isSubmitting ? "Entrando" : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
