import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import loginImg from "./656702.jpg"; // Ensure this file is correctly named and placed
import "./Login.css";

const Login = () => {
  const location = useLocation();
  const role = location.state?.role || "user";
  const navigate = useNavigate();

  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = () => {
    if (!userId || !password) {
      alert("Please fill in both fields");
      return;
    }

    if (role === "supervisor") {
      navigate("/production-entry");
    } else {
      alert("Admin login redirect can be added later");
    }
  };

  return (
    <div className="login-container">
      <div className="login-wrapper">
        <div className="login-left">
          <img src={loginImg} alt="Login Visual" />
        </div>
        <div className="login-right">
          <h2>{role.charAt(0).toUpperCase() + role.slice(1)} Login</h2>

          <div className="input-wrapper">
            <input
              type="text"
              placeholder="User ID"
              value={userId}
              onChange={(e) =>
                setUserId(e.target.value.replace(/\D/g, ""))
              }
              onPaste={(e) => {
                const pasted = e.clipboardData.getData("text");
                if (/\D/.test(pasted)) e.preventDefault();
              }}
              required
            />
          </div>

          <div className="input-wrapper">
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button onClick={handleLogin}>Login</button>
        </div>
      </div>
    </div>
  );
};

export default Login;
