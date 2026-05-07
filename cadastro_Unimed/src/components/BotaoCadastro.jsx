import { motion } from "framer-motion";

const MotionA = motion.a;
const MotionSpan = motion.span;

export function BotaoCadastro() {
  return (
    <MotionA
      href="/Cadastro"
      className="inline-flex items-center gap-1.5 rounded-full bg-[#006F46] px-5 py-2.5 text-sm font-semibold text-white shadow-md transition-colors hover:bg-[#00583C]"
      whileHover={{ y: -2, scale: 1.04 }}
      whileTap={{ scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 28 }}
    >
      Faca sua homologacao
      <MotionSpan aria-hidden="true" whileHover={{ x: 2 }}>
        -&gt;
      </MotionSpan>
    </MotionA>
  );
}
