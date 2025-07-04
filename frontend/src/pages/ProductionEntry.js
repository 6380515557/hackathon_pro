import React, { useState, useEffect } from 'react';
import { Loader2, CloudOff, Cloud } from 'lucide-react'; // Added CloudOff and Cloud icons
import { useAuth } from '../contexts/AuthContext';
import MessageModal from '../components/MessageModal';
import Navbar from '../components/Navbar';
import {
  saveOfflineEntry,
  getOfflineEntries,
  markEntryAsSynced,
  removeOfflineEntry // Added removeOfflineEntry
} from '../utils/offlineDb'; // Import offline storage utilities

const ProductionEntry = () => {
  const { getAuthHeader } = useAuth();
  const [formData, setFormData] = useState({
    production_date: '',
    machineId: '',
    shift: '',
    productName: '',
    quantityProduced: '',
    remarks: '',
  });

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [offlineEntries, setOfflineEntries] = useState([]);
  const [isOnline, setIsOnline] = useState(navigator.onLine); // Track online status

  // --- Effect to load offline entries on component mount ---
  useEffect(() => {
    const loadEntries = async () => {
      const entries = await getOfflineEntries();
      setOfflineEntries(entries);
    };
    loadEntries();

    // --- Event listeners for online/offline status ---
    const handleOnline = () => {
      setIsOnline(true);
      setMessage({ text: 'You are back online!', type: 'success' });
      // Immediately try to sync if there are offline entries
      if (offlineEntries.length > 0) {
        setTimeout(() => syncOfflineEntries(), 2000); // Give a moment for connection to stabilize
      }
    };
    const handleOffline = () => {
      setIsOnline(false);
      setMessage({ text: 'You are currently offline. Data will be saved locally.', type: 'error' });
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [offlineEntries.length]); // Re-run if offlineEntries length changes, to ensure sync attempt on online event

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const clearForm = () => {
    setFormData({
      production_date: '',
      machineId: '',
      shift: '',
      productName: '',
      quantityProduced: '',
      remarks: '',
    });
  };

  const submitToServer = async (data, offlineId = null) => {
    const headers = getAuthHeader();
    if (!headers.Authorization) {
      throw new Error('User not authenticated.');
    }

    const response = await fetch('/api/production_data/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...headers,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || response.statusText);
    }
    return response.json();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);

    const dataToSend = {
      ...formData,
      quantityProduced: parseInt(formData.quantityProduced, 10),
    };

    try {
      await submitToServer(dataToSend);
      setMessage({ text: 'Production data submitted successfully!', type: 'success' });
      clearForm();
    } catch (error) {
      console.error('Server submission failed:', error.message);
      // If submission fails, save to offline storage
      try {
        const savedEntry = await saveOfflineEntry(dataToSend);
        setOfflineEntries((prev) => [...prev, savedEntry]);
        setMessage({ text: 'Server unreachable. Data saved offline. Will sync when online.', type: 'error' });
        clearForm();
      } catch (offlineError) {
        setMessage({ text: `Failed to save data: ${offlineError.message}`, type: 'error' });
      }
    } finally {
      setLoading(false);
    }
  };

  // --- Function to sync offline entries to the backend ---
  const syncOfflineEntries = async () => {
    if (!isOnline) {
      setMessage({ text: 'Cannot sync: You are currently offline.', type: 'error' });
      return;
    }
    if (offlineEntries.length === 0) {
      setMessage({ text: 'No offline entries to sync.', type: 'info' });
      return;
    }

    setLoading(true);
    setMessage({ text: 'Attempting to sync offline entries...', type: 'info' });
    const successfulSyncs = [];
    const failedSyncs = [];

    for (const entry of offlineEntries) {
      try {
        await submitToServer(entry, entry._offlineId);
        successfulSyncs.push(entry._offlineId);
        await removeOfflineEntry(entry._offlineId); // Remove after successful sync
      } catch (error) {
        console.error(`Failed to sync entry ${entry._offlineId}:`, error.message);
        failedSyncs.push(entry._offlineId);
      }
    }

    const updatedOfflineEntries = await getOfflineEntries(); // Reload remaining entries
    setOfflineEntries(updatedOfflineEntries);

    if (successfulSyncs.length > 0) {
      setMessage({ text: `Successfully synced ${successfulSyncs.length} entries!`, type: 'success' });
    }
    if (failedSyncs.length > 0) {
      setMessage({ text: `Failed to sync ${failedSyncs.length} entries. Please try again later.`, type: 'error' });
    }
    if (successfulSyncs.length === 0 && failedSyncs.length === 0) {
       setMessage({ text: 'No offline entries to sync.', type: 'info' });
    }

    setLoading(false);
  };

  const handleCloseMessage = () => {
    setMessage(null);
  };

  return (
    <div className="min-h-screen bg-gray-100 font-inter">
      <Navbar />
      <div className="flex items-center justify-center p-4 sm:p-6 lg:p-8">
        <div className="bg-white p-6 sm:p-8 rounded-xl shadow-lg w-full max-w-md border border-gray-200">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-800 text-center">Production Data Entry</h2>
            <div className={`flex items-center text-sm font-medium ${isOnline ? 'text-green-600' : 'text-red-600'}`}>
              {isOnline ? (
                <>
                  <Cloud className="w-5 h-5 mr-1" /> Online
                </>
              ) : (
                <>
                  <CloudOff className="w-5 h-5 mr-1" /> Offline
                </>
              )}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Date */}
            <div className="flex flex-col">
              <label htmlFor="production_date" className="text-sm font-medium text-gray-700 mb-1">Date</label>
              <input
                type="date"
                id="production_date"
                name="production_date"
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
                <option value="Afternoon">Afternoon</option>
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
                name="quantityProduced"
                placeholder="Enter quantity"
                value={formData.quantityProduced}
                onChange={handleChange}
                required
                min="0"
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

          {/* --- Offline Entries Section --- */}
          {offlineEntries.length > 0 && (
            <div className="mt-8 pt-6 border-t border-gray-200">
              <h3 className="text-lg font-bold text-gray-800 mb-4">
                Offline Entries ({offlineEntries.length})
                <button
                  onClick={syncOfflineEntries}
                  disabled={loading || !isOnline}
                  className={`ml-3 px-3 py-1 text-sm rounded-md font-semibold
                    ${!isOnline || loading
                      ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
                      : 'bg-green-500 hover:bg-green-600 text-white focus:outline-none focus:ring-2 focus:ring-green-500'
                    }
                  `}
                >
                  {loading ? 'Syncing...' : 'Sync Now'}
                </button>
              </h3>
              <ul className="space-y-3 max-h-60 overflow-y-auto">
                {offlineEntries.map((entry) => (
                  <li key={entry._offlineId} className="p-3 bg-gray-50 rounded-md border border-gray-100 text-sm text-gray-700 flex justify-between items-center">
                    <div>
                      <p className="font-semibold">{entry.productName} ({entry.quantityProduced})</p>
                      <p className="text-xs text-gray-500">Machine: {entry.machineId}, Shift: {entry.shift}</p>
                      <p className="text-xs text-gray-500">Date: {entry.production_date}</p>
                    </div>
                    {/* Optionally add a delete button for offline entries */}
                    <button
                      onClick={() => {
                        removeOfflineEntry(entry._offlineId);
                        setOfflineEntries((prev) => prev.filter(e => e._offlineId !== entry._offlineId));
                        setMessage({ text: 'Offline entry removed.', type: 'info' });
                      }}
                      className="ml-2 px-2 py-1 text-xs bg-red-100 text-red-600 rounded hover:bg-red-200"
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {message && (
          <MessageModal
            message={message.text}
            type={message.type}
            onClose={handleCloseMessage}
          />
        )}
      </div>
    </div>
  );
};

export default ProductionEntry;
