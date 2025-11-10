import { useEffect, useState } from "react";
import { Dialog, DialogPanel } from "@headlessui/react";
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline";
import { motion, AnimatePresence } from "framer-motion";

// Logo local
import UnimedLogo from "../assets/Unimed_logo.png";

const navigation = [
  { name: "Prestadores", href: "#" },
  { name: "Documentos", href: "#" },
  { name: "Relatórios", href: "#" },
  { name: "Dashboard", href: "http://localhost:8501" },
];

export default function Navbar() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const navVariants = {
    hidden: { y: -24, opacity: 0 },
    show: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 260, damping: 26 } },
  };

  const listVariants = {
    show: { transition: { staggerChildren: 0.06, delayChildren: 0.06 } },
  };

  const itemVariants = {
    hidden: { y: 8, opacity: 0 },
    show: { y: 0, opacity: 1, transition: { type: "spring", stiffness: 320, damping: 24 } },
  };

  return (
    <div className="relative">
      {/* HEADER */}
      <motion.header
        variants={navVariants}
        initial="hidden"
        animate="show"
        className="fixed inset-x-0 top-0 z-50 transition-all duration-300 bg-white/90 backdrop-blur-xl supports-[backdrop-filter]:bg-white/80"
        style={{ boxShadow: scrolled ? "0 8px 30px rgba(0,0,0,.06)" : "none" }}
      >
        <nav
          className={[
            "mx-auto flex max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8",
            scrolled ? "py-3" : "py-4 lg:py-5",
            "transition-all duration-300",
          ].join(" ")}
        >
          {/* ✅ LOGO DESKTOP */}
          <motion.div
            className="flex lg:flex-1 items-center"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          >
            <a href="https://www.unimed.coop.br/site/web/pontagrossa" className="flex items-center gap-3">
              <img
                src={UnimedLogo}
                alt="Unimed"
                className="w-[60px] h-auto rounded-xl transition-all duration-500 ease-out hover:rounded-full"
              />

            </a>
          </motion.div>

          {/* Botão Mobile */}
          <div className="flex lg:hidden">
            <motion.button
              type="button"
              whileTap={{ scale: 0.96 }}
              onClick={() => setMobileMenuOpen(true)}
              className="-m-2.5 inline-flex items-center justify-center rounded-md p-2.5 text-[#006F46]"
            >
              <Bars3Icon className="h-6 w-6" />
            </motion.button>
          </div>

          {/* Links Desktop */}
          <motion.div
            variants={listVariants}
            initial="hidden"
            animate="show"
            className="hidden lg:flex lg:gap-x-10"
          >
            {navigation.map((item) => (
              <motion.a
                key={item.name}
                href={item.href}
                variants={itemVariants}
                className="relative text-sm font-semibold text-[#006F46]"
                whileHover={{ y: -2, scale: 1.06 }}
                whileTap={{ scale: 0.97 }}
              >
                <span className="relative inline-block group">
                  {item.name}
                  <motion.span
                    layoutId="nav-underline"
                    className="absolute left-0 -bottom-1 h-0.5 w-full rounded bg-[#006F46]"
                    initial={false}
                    style={{ scaleX: 0 }}
                    whileHover={{ scaleX: 1 }}
                    transition={{ type: "spring", stiffness: 400, damping: 30 }}
                  />
                </span>
              </motion.a>
            ))}
          </motion.div>

          {/* Botão Login */}
          <div className="hidden lg:flex lg:flex-1 lg:justify-end">
            <motion.a
              href="/"
              className="inline-flex items-center gap-1.5 rounded-full bg-[#006F46] px-4 py-2 text-sm font-semibold text-white shadow-md hover:bg-[#00583C]"
              whileHover={{ y: -1 }}
              whileTap={{ scale: 0.98 }}
            >
              Homologa +
            </motion.a>
          </div>
        </nav>
      </motion.header>

      {/* Spacer para o header fixo */}
      <div className={scrolled ? "h-16" : "h-20 lg:h-24"} />

      {/* MENU MOBILE */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <Dialog open={mobileMenuOpen} onClose={setMobileMenuOpen} className="lg:hidden">
            <motion.div
              className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />

            <DialogPanel
              as={motion.div}
              initial={{ x: "100%" }}
              animate={{ x: 0 }}
              exit={{ x: "100%" }}
              transition={{ type: "spring", stiffness: 260, damping: 28 }}
              className="fixed inset-y-0 right-0 z-50 w-full overflow-y-auto bg-white p-6 sm:max-w-sm"
            >
              <div className="flex items-center justify-between">
                <a href="#" className="flex items-center gap-3">
                  <img
                    src={UnimedLogo}
                    alt="Unimed"
                    className="w-[180px] h-auto shrink-0 block"
                  />
                </a>

                <motion.button
                  type="button"
                  whileTap={{ scale: 0.96 }}
                  onClick={() => setMobileMenuOpen(false)}
                  className="-m-2.5 rounded-md p-2.5 text-[#006F46]"
                >
                  <XMarkIcon className="h-6 w-6" />
                </motion.button>
              </div>

              <motion.div variants={listVariants} initial="hidden" animate="show" className="mt-6">
                <div className="-my-6 divide-y divide-gray-200">
                  <div className="space-y-2 py-6">
                    {navigation.map((item, i) => (
                      <motion.a
                        key={item.name}
                        href={item.href}
                        variants={itemVariants}
                        onClick={() => setMobileMenuOpen(false)}
                        transition={{ delay: i * 0.02 }}
                        className="-mx-3 block rounded-lg px-3 py-3 text-base font-semibold text-[#006F46] hover:bg-gray-100"
                      >
                        {item.name}
                      </motion.a>
                    ))}
                  </div>

                  {/* Login Mobile */}
                  <div className="py-6">
                    <motion.a
                      href="#"
                      variants={itemVariants}
                      onClick={() => setMobileMenuOpen(false)}
                      className="-mx-3 block rounded-lg px-3 py-3 text-base font-semibold text-[#006F46] hover:bg-gray-100"
                    >
                      Log in
                    </motion.a>
                  </div>
                </div>
              </motion.div>
            </DialogPanel>
          </Dialog>
        )}
      </AnimatePresence>
    </div>
  );
}
