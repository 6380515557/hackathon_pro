import { useState, useEffect } from 'react'; // Make sure useState and useEffect are imported
import './App.css'; // Keep the default styling (or remove if you're not using it)

// Ensure your App component is defined as a function
function App() {
  const [backendMessage, setBackendMessage] = useState('Loading message from backend...');
  const [error, setError] = useState(null);

  // Define your backend URL
  // Make sure your FastAPI backend is running on http://localhost:8000
  const BACKEND_URL = 'http://localhost:8000';

  useEffect(() => {
    const fetchBackendMessage = async () => {
      try {
        // Make a GET request to your FastAPI backend's root endpoint
        const response = await fetch(BACKEND_URL);

        // Check if the response was successful
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        setBackendMessage(data.message); // Assuming your root endpoint returns {"message": "..."}

      } catch (e) {
        console.error("Failed to fetch backend message:", e);
        setError("Failed to connect to backend or retrieve message: " + e.message);
      }
    };

    fetchBackendMessage();
  }, []); // Empty dependency array means this effect runs once after the initial render

  // The return statement MUST be inside the function
  return (
    <>
      <div>
        <h1>Manufacturing Operations Frontend</h1>
        <p>This is your React frontend.</p>

        <h2>Backend Status:</h2>
        {error ? (
          <p style={{ color: 'red' }}>Error: {error}</p>
        ) : (
          <p>Message from FastAPI Backend: <strong>{backendMessage}</strong></p>
        )}

        <p>
          Remember to keep your FastAPI backend running on{' '}
          <a href={BACKEND_URL} target="_blank" rel="noopener noreferrer">
            {BACKEND_URL}
          </a>{' '}
          in a separate terminal.
        </p>
        <p>
          You can explore the backend API documentation at{' '}
          <a href={`${BACKEND_URL}/docs`} target="_blank" rel="noopener noreferrer">
            {BACKEND_URL}/docs
          </a>
          .
        </p>
      </div>
    </>
  ); // Added semicolon here as a good practice
}

export default App; // Export your App component