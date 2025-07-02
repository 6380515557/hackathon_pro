import React from "react";
import { useNavigate } from "react-router-dom";
import "./RoleSelect.css";

const RoleSelect = () => {
  const navigate = useNavigate();

  const handleSelect = (role) => {
    navigate("/login", { state: { role } });
  };

  return (
    <div className="role-select-container">
      <div className="role-card" onClick={() => handleSelect("admin")}>
        <h2>Admin</h2>
        <p>Login as Admin</p>
      </div>
      <div className="role-card" onClick={() => handleSelect("supervisor")}>
        <h2>Supervisor</h2>
        <p>Login as Supervisor</p>
      </div>
    </div>
  );
};

export default RoleSelect;
