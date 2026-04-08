// background.js - Service Worker for AttendX Chrome Extension

const API_BASE = 'http://localhost:5000/api';

chrome.runtime.onInstalled.addListener(() => {
  console.log('AttendX Extension installed');
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'API_CALL') {
    fetch(`${API_BASE}${request.endpoint}`, {
      method: request.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${request.token || ''}`
      },
      body: request.body ? JSON.stringify(request.body) : undefined
    })
    .then(res => res.json())
    .then(data => sendResponse({ success: true, data }))
    .catch(err => sendResponse({ success: false, error: err.message }));
    return true;
  }
});