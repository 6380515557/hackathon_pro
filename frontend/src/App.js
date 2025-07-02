import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import RoleSelect from "./pages/RoleSelect";
import Login from "./pages/Login";
import ProductionEntry from "./pages/ProductionEntry"; // ✅ updated component name

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<RoleSelect />} />
        <Route path="/login" element={<Login />} />
        <Route path="/production-entry" element={<ProductionEntry />} /> {/* ✅ correct route */}
      </Routes>
    </Router>
  );
}

export default App;
