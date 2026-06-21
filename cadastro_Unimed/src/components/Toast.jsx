import { useEffect } from "react";

export default function Toast({ message, type = "success", onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timer = window.setTimeout(onClose, 4500);
    return () => window.clearTimeout(timer);
  }, [message, onClose]);

  if (!message) return null;

  const tone = type === "error" ? "bg-rose-50 text-rose-700 border-rose-100" : "bg-emerald-50 text-emerald-700 border-emerald-100";

  return (
    <div className={`fixed bottom-6 right-6 z-50 max-w-sm rounded-2xl border px-4 py-3 shadow-xl shadow-slate-900/10 ${tone}`}>
      <div className="text-sm font-semibold">{type === "error" ? "Erro" : "Sucesso"}</div>
      <p className="mt-1 text-sm leading-6">{message}</p>
    </div>
  );
}
