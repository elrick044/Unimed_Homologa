import { useState } from "react";
import { PhotoIcon, UserCircleIcon } from "@heroicons/react/24/solid";
import { ChevronDownIcon } from "@heroicons/react/16/solid";
import { motion } from "framer-motion";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// Helpers de CNPJ
const onlyDigits = (s) => s.replace(/\D/g, "");
const formatCnpj = (v) => {
  const d = onlyDigits(v).slice(0, 14);
  if (d.length <= 2) return d;
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`;
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  if (d.length <= 12)
    return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12, 14)}`;
};

export default function Cadastro() {
  // estados do formulário
  const [razaoSocial, setRazaoSocial] = useState("");
  const [cnpj, setCnpj] = useState("");
  const [setor, setSetor] = useState("");
  const [loading, setLoading] = useState(false);
  const [protocolo, setProtocolo] = useState("");
  const [erro, setErro] = useState("");

  // animação do card
  const cardVariants = {
    initial: { opacity: 0, y: 24, scale: 0.98 },
    animate: { opacity: 1, y: 0, scale: 1, transition: { duration: 0.5, ease: "easeOut" } },
  };

  const formInvalid =
    razaoSocial.trim().length < 2 || onlyDigits(cnpj).length !== 14;

  // envio
  const onSubmit = async (e) => {
    e.preventDefault();
    if (formInvalid) return;

    setErro("");
    setProtocolo("");
    setLoading(true);
    try {
      const payload = {
        razao_social: razaoSocial.trim(),
        cnpj: formatCnpj(cnpj),
        setor: setor || "Adulto", // envia formatado; se preferir, use onlyDigits(cnpj)
        // status: "Em análise", // opcional: API já usa default
      };

      const resp = await fetch(`${API_URL}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || data.message || "Falha no envio.");
      }

      const data = await resp.json();
      setProtocolo(data.protocolo);
    } catch (err) {
      setErro(err.message || "Erro ao conectar com a API.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#009966] text-white relative isolate px-6 py-24 lg:px-8 overflow-hidden">
      {/* POLÍGONO SUPERIOR */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 -top-40 -z-10 transform-gpu overflow-hidden blur-3xl sm:-top-80"
      >
        <div
          style={{
            clipPath:
              "polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)",
          }}
          className="relative left-[calc(50%-11rem)] aspect-[1155/678] w-[144.5rem] -translate-x-1/2 rotate-30 bg-gradient-to-tr from-[#006F46] to-[#00C784] opacity-25 sm:left-[calc(50%-30rem)] sm:w-[288.75rem]"
        />
      </div>

      {/* FORMULÁRIO */}
      <motion.form
        onSubmit={onSubmit}
        variants={cardVariants}
        initial="initial"
        animate="animate"
        whileHover={{ y: -2 }}
        className="max-w-xl mx-auto bg-white text-gray-800 rounded-2xl shadow-xl ring-1 ring-black/5 p-8 space-y-6"
      >
        {/* Título */}
        <div className="flex items-center gap-3">
          <UserCircleIcon className="h-8 w-8 text-[#006F46]" />
          <h2 className="text-2xl font-semibold text-[#006F46]">Cadastro</h2>
        </div>

        {/* Razão social */}
        <div className="space-y-1.5">
          <label htmlFor="razao" className="block text-sm font-medium text-gray-700">
            Razão social *
          </label>
          <input
            id="razao"
            name="razao"
            type="text"
            value={razaoSocial}
            onChange={(e) => setRazaoSocial(e.target.value)}
            placeholder="Ex.: Clínica São Lucas LTDA"
            required
            autoComplete="organization"
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#00A86B] focus:border-transparent"
          />
        </div>

        {/* CNPJ */}
        <div className="space-y-1.5">
          <label htmlFor="cnpj" className="block text-sm font-medium text-gray-700">
            CNPJ *
          </label>
          <input
            id="cnpj"
            name="cnpj"
            type="text"
            inputMode="numeric"
            value={cnpj}
            onChange={(e) => setCnpj(formatCnpj(e.target.value))}
            placeholder="00.000.000/0001-00"
            required
            autoComplete="on"
            className="block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#00A86B] focus:border-transparent"
          />
          <p className="text-xs text-gray-500">
            Informe 14 dígitos. Ex.: <span className="font-mono">12.345.678/0001-90</span>
          </p>
        </div>

        {/* Setor (UI apenas) */}
        <div className="space-y-1.5">
          <label htmlFor="setor" className="block text-sm font-medium text-gray-700">
            Setor
          </label>
          <div className="relative">
            <select
              id="setor"
              name="setor"
              value={setor}
              onChange={(e) => setSetor(e.target.value)}
              className="block w-full appearance-none rounded-lg border border-gray-300 bg-white px-3 py-2 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-[#00A86B] focus:border-transparent"
            >
              <option value="">Selecione um setor</option>
              <option>Adulto</option>
              <option>Infantil</option>
              <option>Obstétrico</option>
              <option>Ortopedia</option>
            </select>
            <ChevronDownIcon className="pointer-events-none absolute right-2.5 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
          </div>
        </div>

        {/* Upload (mock visual) */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700">Anexo (opcional)</label>
          <div className="flex items-center justify-center gap-3 rounded-lg border border-dashed border-gray-300 p-4">
            <PhotoIcon className="h-7 w-7 text-gray-400" />
            <span className="text-sm text-gray-500">Em breve: envio de arquivos</span>
          </div>
        </div>

        {/* feedback */}
        {erro && (
          <div className="rounded-lg bg-red-50 text-red-700 text-sm px-3 py-2" role="alert">
            {erro}
          </div>
        )}

        {protocolo && (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg bg-emerald-50 text-emerald-800 text-sm px-3 py-2"
          >
            Protocolo gerado: <span className="font-semibold">{protocolo}</span>
          </motion.div>
        )}

        {/* Ações */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <motion.button
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              setRazaoSocial("");
              setCnpj("");
              setSetor("");
              setErro("");
              setProtocolo("");
            }}
            className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100"
          >
            Cancelar
          </motion.button>

          <motion.button
            type="submit"
            disabled={loading || formInvalid}
            whileHover={{ y: loading || formInvalid ? 0 : -1 }}
            whileTap={{ scale: loading || formInvalid ? 1 : 0.98 }}
            transition={{ type: "spring", stiffness: 500, damping: 30 }}
            className={`rounded-lg bg-[#006F46] px-4 py-2 text-sm font-semibold text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#00A86B]
              ${loading || formInvalid ? "opacity-60 cursor-not-allowed" : "hover:bg-[#00583C]"}`}
          >
            {loading ? "Enviando..." : "Enviar"}
          </motion.button>
        </div>
      </motion.form>

      {/* POLÍGONO INFERIOR */}
      <div
        aria-hidden="true"
        className="absolute inset-x-0 bottom-0 -z-10 transform-gpu overflow-hidden blur-3xl"
      >
        <div
          style={{
            clipPath:
              "polygon(74.1% 44.1%, 100% 61.6%, 97.5% 26.9%, 85.5% 0.1%, 80.7% 2%, 72.5% 32.5%, 60.2% 62.4%, 52.4% 68.1%, 47.5% 58.3%, 45.2% 34.5%, 27.5% 76.7%, 0.1% 64.9%, 17.9% 100%, 27.6% 76.8%, 76.1% 97.7%, 74.1% 44.1%)",
          }}
          className="relative left-1/2 aspect-[1155/678] w-[144.5rem] -translate-x-1/2 bg-gradient-to-tr from-[#006F46] to-[#00C784] opacity-25 sm:w-[288.75rem]"
        />
      </div>
    </div>
  );
}
