import bgImg from "../assets/unimed_hero.jpg";
import { BotaoCadastro } from "./BotaoCadastro";

export default function Hero() {
  return (
    <div
      className="relative h-screen bg-cover bg-center text-white bg-blend-multiply"
      style={{
        backgroundImage: `url(${bgImg})`,
      }}
    >
      {/* Overlay com a tonalidade exata */}
      <div className="absolute inset-0 bg-[#0A524E]/100 mix-blend-multiply"></div>

      {/* Conteúdo */}
      <div className="relative z-10 flex h-full flex-col items-center justify-center">
        <h1 className="text-5xl font-bold mb-8">
          Homologação de Clínicas e Profissionais da Saúde
        </h1>
        <h2 className="max-w-2xl text-lg sm:text-xl text-white/90 mb-10">
          Cadastre e regularize sua clínica, consultório ou serviço especializado com segurança e rapidez. 
          A Unimed garante conformidade, qualidade no atendimento e a melhor experiência para pacientes e parceiros.
        </h2>
        <BotaoCadastro />
      </div>
    </div>
  );
}
