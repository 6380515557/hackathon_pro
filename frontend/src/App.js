import React, { useState } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react'; // Using lucide-react for icons

// Simple Message Modal Component (reused from Login and ProductionEntry)
const MessageModal = ({ message, type, onClose }) => {
  const isSuccess = type === 'success';
  const icon = isSuccess ? <CheckCircle className="w-8 h-8 text-green-500" /> : <XCircle className="w-8 h-8 text-red-500" />;
  const title = isSuccess ? 'Success!' : 'Error!';
  const bgColor = isSuccess ? 'bg-green-100' : 'bg-red-100';
  const textColor = isSuccess ? 'text-green-800' : 'text-red-800';

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className={`rounded-lg shadow-xl p-6 max-w-sm w-full text-center ${bgColor}`}>
        <div className="flex justify-center mb-4">
          {icon}
        </div>
        <h3 className={`text-lg font-semibold mb-2 ${textColor}`}>{title}</h3>
        <p className={`text-sm mb-4 ${textColor}`}>{message}</p>
        <button
          onClick={onClose}
          className={`px-4 py-2 rounded-md font-semibold focus:outline-none focus:ring-2 focus:ring-opacity-75
            ${isSuccess ? 'bg-green-600 hover:bg-green-700 text-white focus:ring-green-500' : 'bg-red-600 hover:bg-red-700 text-white focus:ring-red-500'}
          `}
        >
          Close
        </button>
      </div>
    </div>
  );
};

const Register = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    role: 'operator', // Default role for new registrations
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null); // { text: '', type: 'success' | 'error' }

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null); // Clear previous messages

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        const result = await response.json();
        setMessage({ text: `Registration successful for ${result.username}! You can now log in.`, type: 'success' });
        // Clear form after successful registration
        setFormData({
          username: '',
          password: '',
          role: 'operator',
        });
      } else {
        const errorData = await response.json();
        setMessage({ text: `Registration failed: ${errorData.detail || response.statusText}`, type: 'error' });
      }
    } catch (error) {
      setMessage({ text: `An unexpected error occurred: ${error.message}`, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleCloseMessage = () => {
    setMessage(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4 sm:p-6 lg:p-8 font-inter">
      <div className="bg-white p-6 sm:p-8 rounded-xl shadow-lg w-full max-w-md border border-gray-200">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 mb-6 text-center">Register New User</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username */}
          <div className="flex flex-col">
            <label htmlFor="username" className="text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              id="username"
              name="username"
              placeholder="Choose a username"
              value={formData.username}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
            />
          </div>

          {/* Password */}
          <div className="flex flex-col">
            <label htmlFor="password" className="text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              placeholder="Choose a strong password"
              value={formData.password}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
            />
          </div>

          {/* Role Selection */}
          <div className="flex flex-col">
            <label htmlFor="role" className="text-sm font-medium text-gray-700 mb-1">Role</label>
            <select
              id="role"
              name="role"
              value={formData.role}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 bg-white"
            >
              <option value="operator">Operator</option>
              <option value="supervisor">Supervisor</option>
              <option value="admin">Admin</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 px-4 rounded-md font-semibold text-white transition duration-300 ease-in-out
              ${loading ? 'bg-green-300 cursor-not-allowed' : 'bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-opacity-75'}
              flex items-center justify-center
            `}
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin mr-2" size={20} /> Registering...
              </>
            ) : (
              'Register'
            )}
          </button>
        </form>
      </div>

      {message && (
        <MessageModal
          message={message.text}
          type={message.type}
          onClose={handleCloseMessage}
        />
      )}
    </div>
  );
};

export default Register;
