import { Dialog } from "@headlessui/react";

export default function ConfirmDialog({ open, title, description, confirmLabel = "Confirmar", cancelLabel = "Cancelar", onConfirm, onClose }) {
  return (
    <Dialog open={open} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-md rounded-3xl border border-gray-200 bg-white p-6 shadow-xl shadow-slate-900/5">
          <Dialog.Title className="text-lg font-semibold text-gray-950">{title}</Dialog.Title>
          <Dialog.Description className="mt-3 text-sm leading-6 text-gray-600">{description}</Dialog.Description>

          <div className="mt-6 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="inline-flex items-center justify-center rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className="inline-flex items-center justify-center rounded-lg bg-[#006F46] px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-[#00583C]"
            >
              {confirmLabel}
            </button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
}
