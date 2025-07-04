import React, { useState } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react'; // Using lucide-react for icons

// Simple Message Modal Component
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

const ProductionEntry = () => {
  const [formData, setFormData] = useState({
    production_date: '', // Aligned with backend schema
    machineId: '',
    shift: '', // Will be 'Morning', 'Afternoon', 'Night'
    productName: '',
    quantityProduced: '', // Aligned with backend schema
    remarks: '',
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

    // Get token from local storage
    const token = localStorage.getItem('access_token');
    if (!token) {
      setMessage({ text: 'You are not logged in. Please log in to submit data.', type: 'error' });
      setLoading(false);
      return;
    }

    // Prepare data for backend (ensure quantity is number)
    const dataToSend = {
      ...formData,
      quantityProduced: parseInt(formData.quantityProduced, 10), // Convert to integer
      // Backend expects 'production_date'
    };

    try {
      const response = await fetch('/api/production_data/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(dataToSend),
      });

      if (response.ok) {
        const result = await response.json();
        setMessage({ text: 'Production data submitted successfully!', type: 'success' });
        // Clear form after successful submission
        setFormData({
          production_date: '',
          machineId: '',
          shift: '',
          productName: '',
          quantityProduced: '',
          remarks: '',
        });
      } else {
        const errorData = await response.json();
        setMessage({ text: `Failed to submit data: ${errorData.detail || response.statusText}`, type: 'error' });
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
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 mb-6 text-center">Production Data Entry</h2>
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Date */}
          <div className="flex flex-col">
            <label htmlFor="production_date" className="text-sm font-medium text-gray-700 mb-1">Date</label>
            <input
              type="date"
              id="production_date"
              name="production_date" // Aligned with backend
              value={formData.production_date}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
            />
          </div>

          {/* Machine ID */}
          <div className="flex flex-col">
            <label htmlFor="machineId" className="text-sm font-medium text-gray-700 mb-1">Machine ID</label>
            <input
              type="text"
              id="machineId"
              name="machineId"
              placeholder="Enter machine ID"
              value={formData.machineId}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
            />
          </div>

          {/* Shift */}
          <div className="flex flex-col">
            <label htmlFor="shift" className="text-sm font-medium text-gray-700 mb-1">Shift</label>
            <select
              id="shift"
              name="shift"
              value={formData.shift}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 bg-white"
            >
              <option value="">Select Shift</option>
              <option value="Morning">Morning</option>
              <option value="Afternoon">Afternoon</option> {/* Corrected to match backend Literal */}
              <option value="Night">Night</option>
            </select>
          </div>

          {/* Product Name/Type */}
          <div className="flex flex-col">
            <label htmlFor="productName" className="text-sm font-medium text-gray-700 mb-1">Product Name/Type</label>
            <input
              type="text"
              id="productName"
              name="productName"
              placeholder="Enter product name/type"
              value={formData.productName}
              onChange={handleChange}
              required
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
            />
          </div>

          {/* Quantity Produced */}
          <div className="flex flex-col">
            <label htmlFor="quantityProduced" className="text-sm font-medium text-gray-700 mb-1">Quantity Produced</label>
            <input
              type="number"
              id="quantityProduced"
              name="quantityProduced" // Aligned with backend
              placeholder="Enter quantity"
              value={formData.quantityProduced}
              onChange={handleChange}
              required
              min="0" // Ensure non-negative as per backend schema
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200"
            />
          </div>

          {/* Comments / Remarks */}
          <div className="flex flex-col">
            <label htmlFor="remarks" className="text-sm font-medium text-gray-700 mb-1">Comments / Remarks</label>
            <textarea
              id="remarks"
              name="remarks"
              rows="3"
              placeholder="Any additional comments"
              value={formData.remarks}
              onChange={handleChange}
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition duration-200 resize-y"
            ></textarea>
          </div>

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2 px-4 rounded-md font-semibold text-white transition duration-300 ease-in-out
              ${loading ? 'bg-blue-300 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-75'}
              flex items-center justify-center
            `}
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin mr-2" size={20} /> Submitting...
              </>
            ) : (
              'Submit Entry'
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

export default ProductionEntry;
