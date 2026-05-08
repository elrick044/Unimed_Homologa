import { BrowserRouter, Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Cadastro from "./pages/Cadastro";
import Login from "./pages/Login";
import PrestadorDashboard from "./pages/PrestadorDashboard";
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
          <Route path="/prestador/dashboard" element={<PrestadorDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App


