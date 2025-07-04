// src/utils/offlineDb.js
import localforage from 'localforage';

// Configure localforage for your application
localforage.config({
  name: 'productionTrackerDB', // Database name
  storeName: 'productionEntries', // Store name (like a table in SQL)
  description: 'Stores production data entries for offline use',
});

// Create an instance for the specific store
const productionEntriesStore = localforage.createInstance({
  name: 'productionTrackerDB',
  storeName: 'productionEntries',
});

// Function to save a new production entry to offline storage
export const saveOfflineEntry = async (entry) => {
  try {
    // Generate a unique ID for the offline entry (important for syncing later)
    // Using a timestamp + random number to ensure high uniqueness
    const offlineId = `offline-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const entryWithId = { ...entry, _offlineId: offlineId, _isSynced: false };

    await productionEntriesStore.setItem(offlineId, entryWithId);
    console.log(`Entry saved offline with ID: ${offlineId}`);
    return entryWithId;
  } catch (error) {
    console.error('Error saving entry offline:', error);
    throw error;
  }
};

// Function to get all offline entries
export const getOfflineEntries = async () => {
  try {
    const entries = [];
    await productionEntriesStore.iterate((value, key, iterationNumber) => {
      entries.push(value);
    });
    // Sort by offlineId (which includes timestamp) to maintain some order
    return entries.sort((a, b) => (a._offlineId > b._offlineId ? 1 : -1));
  } catch (error) {
    console.error('Error retrieving offline entries:', error);
    return [];
  }
};

// Function to mark an offline entry as synced and potentially remove it
export const markEntryAsSynced = async (offlineId) => {
  try {
    const entry = await productionEntriesStore.getItem(offlineId);
    if (entry) {
      // Option 1: Update the entry to mark as synced (useful for debugging/tracking)
      await productionEntriesStore.setItem(offlineId, { ...entry, _isSynced: true });
      console.log(`Entry ${offlineId} marked as synced.`);
      // Option 2: Remove the entry after successful sync (more common to clean up)
      // await productionEntriesStore.removeItem(offlineId);
      // console.log(`Entry ${offlineId} removed after sync.`);
    }
  } catch (error) {
    console.error('Error marking entry as synced:', error);
  }
};

// Function to remove a specific offline entry
export const removeOfflineEntry = async (offlineId) => {
  try {
    await productionEntriesStore.removeItem(offlineId);
    console.log(`Offline entry ${offlineId} removed.`);
  } catch (error) {
    console.error('Error removing offline entry:', error);
  }
};

// Function to clear all offline entries
export const clearAllOfflineEntries = async () => {
  try {
    await productionEntriesStore.clear();
    console.log('All offline entries cleared.');
  } catch (error) {
    console.error('Error clearing all offline entries:', error);
  }
};
