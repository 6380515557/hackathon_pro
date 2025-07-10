import React from 'react';
import { useAuth } from '../App'; // Import useAuth from App.js

function Dashboard() {
  const { token, logout } = useAuth();

  return (
    <div>
      <h2>Dashboard</h2>
      <p>Welcome to your Dashboard!</p>
      {token && <p>You are logged in with token: {token.substring(0, 10)}...</p>}
      <button onClick={logout}>Logout</button>
    </div>
  );
}

export default Dashboard;