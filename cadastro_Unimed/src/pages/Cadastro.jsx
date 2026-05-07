import { useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowPathIcon,
  BuildingOffice2Icon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  LockClosedIcon,
} from "@heroicons/react/24/outline";
import { motion } from "framer-motion";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { api } from "../config/api";

const MotionSection = motion.section;

const onlyDigits = (value = "") => value.replace(/\D/g, "");

const formatCnpj = (value = "") => {
  const digits = onlyDigits(value).slice(0, 14);

  if (digits.length <= 2) return digits;
  if (digits.length <= 5) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  if (digits.length <= 8) {
    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5)}`;
  }
  if (digits.length <= 12) {
    return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(8)}`;
  }

  return `${digits.slice(0, 2)}.${digits.slice(2, 5)}.${digits.slice(5, 8)}/${digits.slice(
    8,
    12,
  )}-${digits.slice(12, 14)}`;
};

const formatPhone = (value = "") => {
  const digits = onlyDigits(value).slice(0, 11);

  if (digits.length <= 2) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 2)}) ${digits.slice(2)}`;
  if (digits.length <= 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  }

  return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7, 11)}`;
};

const isValidCnpj = (value = "") => {
  const cnpj = onlyDigits(value);

  if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) return false;

  const calculateDigit = (base) => {
    const weights = base.length === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const sum = base.split("").reduce((total, digit, index) => total + Number(digit) * weights[index], 0);
    const remainder = sum % 11;

    return remainder < 2 ? 0 : 11 - remainder;
  };

  const firstDigit = calculateDigit(cnpj.slice(0, 12));
  const secondDigit = calculateDigit(`${cnpj.slice(0, 12)}${firstDigit}`);

  return cnpj.endsWith(`${firstDigit}${secondDigit}`);
};

const registerSchema = z
  .object({
    razao_social: z.string().trim().min(2, "Informe a razao social.").max(255, "Use no maximo 255 caracteres."),
    nome_fantasia: z.string().trim().min(2, "Informe o nome fantasia.").max(255, "Use no maximo 255 caracteres."),
    cnpj: z.string().refine(isValidCnpj, "Informe um CNPJ valido."),
    endereco: z.string().trim().min(5, "Informe o endereco completo."),
    nome_responsavel: z.string().trim().min(2, "Informe o nome do responsavel.").max(255, "Use no maximo 255 caracteres."),
    email: z.string().trim().email("Informe um e-mail valido."),
    telefone: z.string().refine((value) => onlyDigits(value).length >= 10, "Informe um telefone valido."),
    senha: z.string().min(8, "A senha deve ter pelo menos 8 caracteres."),
    confirmar_senha: z.string().min(1, "Confirme a senha de acesso."),
  })
  .refine((data) => data.senha === data.confirmar_senha, {
    message: "As senhas nao conferem.",
    path: ["confirmar_senha"],
  });

const backendFieldNames = [
  "razao_social",
  "nome_fantasia",
  "cnpj",
  "endereco",
  "nome_responsavel",
  "email",
  "telefone",
  "senha",
];

const inputClass =
  "block w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 shadow-sm outline-none transition placeholder:text-gray-400 focus:border-[#009966] focus:ring-2 focus:ring-[#009966]/20 disabled:cursor-not-allowed disabled:bg-gray-100";

const labelClass = "block text-sm font-medium text-gray-700";

function FieldError({ message }) {
  if (!message) return null;

  return <p className="text-sm text-red-600">{message}</p>;
}

function backendMessage(value) {
  if (Array.isArray(value)) return value.join(" ");
  if (typeof value === "string") return value;
  return "";
}

export default function Cadastro() {
  const navigate = useNavigate();
  const [feedback, setFeedback] = useState(null);

  const {
    register,
    handleSubmit,
    setError,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      razao_social: "",
      nome_fantasia: "",
      cnpj: "",
      endereco: "",
      nome_responsavel: "",
      email: "",
      telefone: "",
      senha: "",
      confirmar_senha: "",
    },
  });

  const setBackendErrors = (data) => {
    let hasFieldError = false;

    backendFieldNames.forEach((field) => {
      if (data?.[field]) {
        hasFieldError = true;
        setError(field, { type: "server", message: backendMessage(data[field]) || "Revise este campo." });
      }
    });

    return hasFieldError;
  };

  const onSubmit = async (data) => {
    setFeedback(null);

    const formData = {
      razao_social: data.razao_social,
      nome_fantasia: data.nome_fantasia,
      cnpj: data.cnpj,
      endereco: data.endereco,
      nome_responsavel: data.nome_responsavel,
      email: data.email,
      telefone: data.telefone,
      senha: data.senha,
    };

    try {
      await api.post("/auth/register/prestador/", {
        ...formData,
        cnpj: formatCnpj(formData.cnpj),
        telefone: formatPhone(formData.telefone),
      });

      setFeedback({
        type: "success",
        message: "Cadastro enviado com sucesso. Voce sera redirecionado para o login.",
      });

      window.setTimeout(() => navigate("/login"), 1200);
    } catch (error) {
      const responseData = error.response?.data;
      const hasFieldError = responseData && setBackendErrors(responseData);

      setFeedback({
        type: "error",
        message: hasFieldError
          ? "Alguns dados precisam de ajuste antes do envio."
          : backendMessage(responseData?.detail || responseData?.non_field_errors) || "Nao foi possivel concluir o cadastro.",
      });
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10 sm:px-6 lg:px-8">
      <MotionSection
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        className="mx-auto max-w-5xl"
      >
        <div className="mb-8 max-w-3xl">
          <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-[#009966]/20 bg-white px-3 py-1 text-sm font-medium text-[#006F46] shadow-sm">
            <BuildingOffice2Icon className="h-4 w-4" />
            Homologacao de prestadores
          </div>
          <h1 className="text-3xl font-semibold tracking-normal text-gray-950 sm:text-4xl">
            Cadastro publico do prestador
          </h1>
          <p className="mt-3 max-w-2xl text-base text-gray-600">
            Informe os dados da empresa e do responsavel para iniciar o processo de homologacao.
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm sm:p-6 lg:p-8"
          noValidate
        >
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="razao_social" className={labelClass}>
                Razao social
              </label>
              <input
                id="razao_social"
                type="text"
                autoComplete="organization"
                className={inputClass}
                disabled={isSubmitting}
                {...register("razao_social")}
              />
              <FieldError message={errors.razao_social?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="nome_fantasia" className={labelClass}>
                Nome fantasia
              </label>
              <input
                id="nome_fantasia"
                type="text"
                autoComplete="organization-title"
                className={inputClass}
                disabled={isSubmitting}
                {...register("nome_fantasia")}
              />
              <FieldError message={errors.nome_fantasia?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="cnpj" className={labelClass}>
                CNPJ
              </label>
              <input
                id="cnpj"
                type="text"
                inputMode="numeric"
                placeholder="00.000.000/0000-00"
                className={inputClass}
                disabled={isSubmitting}
                {...register("cnpj")}
                onChange={(event) => {
                  setValue("cnpj", formatCnpj(event.target.value), { shouldDirty: true, shouldValidate: true });
                }}
              />
              <FieldError message={errors.cnpj?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="telefone" className={labelClass}>
                Telefone
              </label>
              <input
                id="telefone"
                type="tel"
                inputMode="tel"
                placeholder="(11) 99999-9999"
                autoComplete="tel"
                className={inputClass}
                disabled={isSubmitting}
                {...register("telefone")}
                onChange={(event) => {
                  setValue("telefone", formatPhone(event.target.value), { shouldDirty: true, shouldValidate: true });
                }}
              />
              <FieldError message={errors.telefone?.message} />
            </div>

            <div className="space-y-2 md:col-span-2">
              <label htmlFor="endereco" className={labelClass}>
                Endereco
              </label>
              <input
                id="endereco"
                type="text"
                autoComplete="street-address"
                className={inputClass}
                disabled={isSubmitting}
                {...register("endereco")}
              />
              <FieldError message={errors.endereco?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="nome_responsavel" className={labelClass}>
                Nome do responsavel
              </label>
              <input
                id="nome_responsavel"
                type="text"
                autoComplete="name"
                className={inputClass}
                disabled={isSubmitting}
                {...register("nome_responsavel")}
              />
              <FieldError message={errors.nome_responsavel?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="email" className={labelClass}>
                E-mail
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                className={inputClass}
                disabled={isSubmitting}
                {...register("email")}
              />
              <FieldError message={errors.email?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="senha" className={labelClass}>
                Senha de acesso
              </label>
              <div className="relative">
                <LockClosedIcon className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  id="senha"
                  type="password"
                  autoComplete="new-password"
                  className={`${inputClass} pl-10`}
                  disabled={isSubmitting}
                  {...register("senha")}
                />
              </div>
              <FieldError message={errors.senha?.message} />
            </div>

            <div className="space-y-2">
              <label htmlFor="confirmar_senha" className={labelClass}>
                Confirmacao de senha
              </label>
              <div className="relative">
                <LockClosedIcon className="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
                <input
                  id="confirmar_senha"
                  type="password"
                  autoComplete="new-password"
                  className={`${inputClass} pl-10`}
                  disabled={isSubmitting}
                  {...register("confirmar_senha")}
                />
              </div>
              <FieldError message={errors.confirmar_senha?.message} />
            </div>
          </div>

          {feedback && (
            <div
              className={`mt-6 flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${
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

          <div className="mt-8 flex flex-col-reverse gap-3 border-t border-gray-200 pt-6 sm:flex-row sm:items-center sm:justify-end">
            <button
              type="button"
              disabled={isSubmitting}
              onClick={() => navigate("/")}
              className="inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#006F46] px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C] focus:outline-none focus:ring-2 focus:ring-[#009966] focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {isSubmitting && <ArrowPathIcon className="h-4 w-4 animate-spin" />}
              {isSubmitting ? "Enviando cadastro" : "Confirmar cadastro"}
            </button>
          </div>
        </form>
      </MotionSection>
    </main>
  );
}
