import { motion } from "framer-motion";

export function BotaoCadastro() {
  return (
    <motion.a
      href="/Cadastro"
      className="inline-flex items-center gap-1.5 rounded-full bg-[#006F46] px-5 py-2.5
                 text-sm font-semibold text-white shadow-md hover:bg-[#00583C]
                 transition-colors"
      whileHover={{ y: -2, scale: 1.04 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
    >
      Faça Sua Homologação
      <motion.span aria-hidden="true" whileHover={{ x: 2 }}>
        →
      </motion.span>
    </motion.a>
  );
}