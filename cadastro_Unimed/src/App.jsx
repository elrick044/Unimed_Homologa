import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Cadastro from "./pages/Cadastro";
import Login from "./pages/Login";
import PrestadorDashboard from "./pages/PrestadorDashboard";
import AdminProcessos from "./pages/AdminProcessos";
import AdminProcessoDetalhe from "./pages/AdminProcessoDetalhe";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./layout/layout";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/Cadastro" element={<Cadastro />} />
          <Route path="/cadastro" element={<Cadastro />} />
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute allowedProfiles={["PRESTADOR"]} />}>
            <Route path="/prestador/dashboard" element={<PrestadorDashboard />} />
          </Route>
          <Route element={<ProtectedRoute allowedProfiles={["EQUIPE_ADMINISTRATIVA", "ADMINISTRADOR"]} />}>
            <Route path="/admin/processos" element={<AdminProcessos />} />
            <Route path="/admin/processos/:id" element={<AdminProcessoDetalhe />} />
          </Route>
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App


