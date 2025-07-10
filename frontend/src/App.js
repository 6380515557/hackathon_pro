// frontend/src/App.js

import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import './App.css'; // Your main CSS file

// Import your new components (we will create these next)
import LoginPage from './components/Auth/LoginPage';
import RegisterPage from './components/Auth/RegisterPage';
import Dashboard from './pages/Dashboard'; // Create this simple placeholder for now
import NotificationsPage from './pages/NotificationsPage'; // Placeholder
import ProductionEntryPage from './pages/ProductionEntryPage'; // Placeholder
import ReferenceDataPage from './pages/ReferenceDataPage'; // Placeholder


// --- Authentication Context ---
// This context will hold the user's authentication state (token, user info)
const AuthContext = createContext(null);

// Custom hook to use the AuthContext
export const useAuth = () => {
  return useContext(AuthContext);
};

// AuthProvider component to wrap your application and provide auth state
const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token')); // Try to get token from localStorage
  const [user, setUser] = useState(null); // You can fetch full user details here if needed

  // Function to log in a user
  const login = (newToken) => {
    setToken(newToken);
    localStorage.setItem('token', newToken); // Store token in local storage
    // Optionally fetch user details here:
    // fetch(`${process.env.REACT_APP_BACKEND_URL}/users/me`, {
    //   headers: { Authorization: `Bearer ${newToken}` }
    // }).then(res => res.json()).then(setUser);
  };

  // Function to log out a user
  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token'); // Remove token from local storage
  };

  const authValue = {
    token,
    user,
    login,
    logout,
    isAuthenticated: !!token // A simple way to check if token exists
  };

  return (
    <AuthContext.Provider value={authValue}>
      {children}
    </AuthContext.Provider>
  );
};


// --- Protected Route Component ---
// This component ensures only authenticated users can access certain routes
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    // Redirect unauthenticated users to the login page
    return <Navigate to="/login" replace />;
  }

  return children;
};


// --- Main App Component ---
function App() {
  const [backendMessage, setBackendMessage] = useState('Loading message from backend...');
  const [error, setError] = useState(null);

  // Define your backend URL (use environment variable for best practice)
  // Add REACT_APP_BACKEND_URL="http://localhost:8000" to a .env file in your frontend root
  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';


  useEffect(() => {
    // Example fetch to your backend's root endpoint
    const fetchBackendMessage = async () => {
      try {
        const response = await fetch(BACKEND_URL);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setBackendMessage(data.message);
      } catch (e) {
        console.error("Failed to fetch backend message:", e);
        setError("Failed to connect to backend or retrieve message: " + e.message);
      }
    };

    fetchBackendMessage();
  }, []);

  return (
    <Router>
      <AuthProvider> {/* Wrap your entire application with AuthProvider */}
        <div className="App">
          <header className="App-header">
            <h1>Manufacturing Operations Frontend</h1>
            <p>This is your React frontend.</p>

            <h2>Backend Status:</h2>
            {error ? (
              <p style={{ color: 'red' }}>Error: {error}</p>
            ) : (
              <p>Message from FastAPI Backend: <strong>{backendMessage}</strong></p>
            )}

            <p>
              Backend URL:{' '}
              <a href={BACKEND_URL} target="_blank" rel="noopener noreferrer">
                {BACKEND_URL}
              </a>{' '}
              | API Docs:{' '}
              <a href={`${BACKEND_URL}/docs`} target="_blank" rel="noopener noreferrer">
                {BACKEND_URL}/docs
              </a>
            </p>
          </header>

          <nav>
            {/* Simple Navigation (adjust as needed with actual Auth state) */}
            <ul>
              <li><a href="/dashboard">Dashboard</a></li>
              <li><a href="/production">Production Entry</a></li>
              <li><a href="/notifications">Notifications</a></li>
              <li><a href="/reference-data">Reference Data</a></li>
              <li><a href="/login">Login</a></li>
              <li><a href="/register">Register</a></li>
              {/* You'll add conditional rendering for Login/Logout based on isAuthenticated */}
            </ul>
          </nav>

          <main>
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} /> {/* Redirect root to dashboard */}

              {/* Protected Routes */}
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
              <Route path="/production" element={<ProtectedRoute><ProductionEntryPage /></ProtectedRoute>} />
              <Route path="/notifications" element={<ProtectedRoute><NotificationsPage /></ProtectedRoute>} />
              <Route path="/reference-data" element={<ProtectedRoute><ReferenceDataPage /></ProtectedRoute>} />

              {/* Catch-all for unknown routes */}
              <Route path="*" element={<h2>404: Not Found</h2>} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;