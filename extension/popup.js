// popup.js - AttendX Chrome Extension - CLEAN VERSION (Employee & Admin Only)

const API_BASE = 'http://localhost:5000/api';
let currentUser = null;
let timerInterval = null;

// ===== UTILS =====
const $ = id => document.getElementById(id);
const showScreen = name => {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  $(`screen-${name}`).classList.add('active');
};

function apiCall(endpoint, method = 'GET', body = null) {
  const token = localStorage.getItem('att_token');
  return fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  }).then(r => r.json());
}

function formatTime(isoString) {
  if (!isoString) return '—';
  return new Date(isoString).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
}

function formatHours(minutes) {
  if (!minutes && minutes !== 0) return '—';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h}h ${m}m`;
}

function getTodayStr() {
  return new Date().toISOString().split('T')[0];
}

// ===== LOGIN/SIGNUP =====
$('btn-to-signup').addEventListener('click', () => {
  showScreen('signup');
  $('signup-error').classList.add('hidden');
});

$('btn-to-login').addEventListener('click', () => {
  showScreen('login');
  $('login-error').classList.add('hidden');
});

$('btn-login').addEventListener('click', async () => {
  const id = $('login-id').value.trim();
  const pass = $('login-pass').value.trim();
  const errDiv = $('login-error');

  if (!id || !pass) {
    errDiv.textContent = 'Please fill in all fields.';
    errDiv.classList.remove('hidden');
    return;
  }

  errDiv.classList.add('hidden');

  try {
    const data = await apiCall('/auth/login', 'POST', { employee_id: id, password: pass });
    if (data.success) {
      localStorage.setItem('att_token', data.token);
      localStorage.setItem('att_user', JSON.stringify(data.user));
      currentUser = data.user;
      loadUserPanel();
    } else {
      errDiv.textContent = data.message || 'Invalid credentials.';
      errDiv.classList.remove('hidden');
    }
  } catch (e) {
    errDiv.textContent = 'Cannot reach server. Check Flask is running.';
    errDiv.classList.remove('hidden');
  }
});

$('login-pass').addEventListener('keydown', e => {
  if (e.key === 'Enter') $('btn-login').click();
});

$('btn-signup').addEventListener('click', async () => {
  const companyName = $('signup-company-name').value.trim();
  const companyEmail = $('signup-company-email').value.trim();
  const ownerName = $('signup-owner-name').value.trim();
  const ownerId = $('signup-owner-id').value.trim();
  const ownerEmail = $('signup-owner-email').value.trim();
  const password = $('signup-password').value.trim();
  const errDiv = $('signup-error');

  if (!companyName || !companyEmail || !ownerName || !ownerId || !ownerEmail || !password) {
    errDiv.textContent = 'Please fill in all fields.';
    errDiv.classList.remove('hidden');
    return;
  }

  if (ownerId.length < 3) {
    errDiv.textContent = 'Owner ID must be at least 3 characters.';
    errDiv.classList.remove('hidden');
    return;
  }

  errDiv.classList.add('hidden');
  $('btn-signup').disabled = true;
  $('btn-signup').textContent = 'Creating...';

  try {
    const data = await apiCall('/company/signup', 'POST', {
      company_name: companyName,
      company_email: companyEmail,
      owner_name: ownerName,
      owner_id: ownerId,
      owner_email: ownerEmail,
      password: password
    });

    if (data.success) {
      const loginData = await apiCall('/auth/login', 'POST', { employee_id: ownerId, password: password });
      if (loginData.success) {
        localStorage.setItem('att_token', loginData.token);
        localStorage.setItem('att_user', JSON.stringify(loginData.user));
        currentUser = loginData.user;
        loadUserPanel();
      } else {
        errDiv.textContent = 'Company created but login failed. Please login manually.';
        errDiv.classList.remove('hidden');
        showScreen('login');
      }
    } else {
      errDiv.textContent = data.message || 'Failed to create company.';
      errDiv.classList.remove('hidden');
      $('btn-signup').disabled = false;
      $('btn-signup').textContent = 'Create & Login';
    }
  } catch (e) {
    errDiv.textContent = 'Cannot reach server. Check Flask is running.';
    errDiv.classList.remove('hidden');
    $('btn-signup').disabled = false;
    $('btn-signup').textContent = 'Create & Login';
  }
});

// ===== AUTO LOGIN =====
window.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('att_token');
  const user = localStorage.getItem('att_user');
  if (token && user) {
    currentUser = JSON.parse(user);
    loadUserPanel();
  } else {
    showScreen('login');
  }
});

// ===== ROUTE TO CORRECT PANEL =====
function loadUserPanel() {
  if (currentUser.role === 'owner' || currentUser.role === 'admin') {
    loadAdminPanel();
  } else {
    loadEmployeePanel();
  }
}

// ========================================
// EMPLOYEE PANEL - MY ATTENDANCE ONLY
// ========================================
async function loadEmployeePanel() {
  showScreen('employee');
  $('emp-name').textContent = currentUser.name || currentUser.employee_id;

  const now = new Date();
  $('today-day').textContent = now.toLocaleDateString('en-IN', { weekday: 'long' });
  $('today-date').textContent = now.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });

  await refreshEmployeeStatus();
  await loadWeekGrid();
  await loadEmployeeLeaveRequests();
  
  setupCheckInOut();
  
  const applyBtn = $('btn-apply-leave');
  if (applyBtn) {
    const newApplyBtn = applyBtn.cloneNode(true);
    applyBtn.parentNode.replaceChild(newApplyBtn, applyBtn);
    newApplyBtn.addEventListener('click', applyForLeave);
  }

  $('emp-logout').addEventListener('click', logout);
}

function setupCheckInOut() {
  const btnIn = $('btn-checkin');
  const btnOut = $('btn-checkout');

  if (btnIn) {
    const newBtnIn = btnIn.cloneNode(true);
    btnIn.parentNode.replaceChild(newBtnIn, btnIn);
    newBtnIn.addEventListener('click', async () => {
      newBtnIn.disabled = true;
      try {
        const data = await apiCall('/attendance/checkin', 'POST');
        if (data.success) {
          await refreshEmployeeStatus();
          await loadWeekGrid();
        } else {
          alert(data.message || 'Check-in failed');
          newBtnIn.disabled = false;
        }
      } catch {
        alert('Server error. Try again.');
        newBtnIn.disabled = false;
      }
    });
  }

  if (btnOut) {
    const newBtnOut = btnOut.cloneNode(true);
    btnOut.parentNode.replaceChild(newBtnOut, btnOut);
    newBtnOut.addEventListener('click', async () => {
      newBtnOut.disabled = true;
      try {
        const data = await apiCall('/attendance/checkout', 'POST');
        if (data.success) {
          if (timerInterval) clearInterval(timerInterval);
          await refreshEmployeeStatus();
        } else {
          alert(data.message || 'Check-out failed');
          newBtnOut.disabled = false;
        }
      } catch {
        alert('Server error. Try again.');
        newBtnOut.disabled = false;
      }
    });
  }
}

async function refreshEmployeeStatus() {
  try {
    const data = await apiCall('/attendance/today');
    const record = data.record;

    const dot = $('status-dot');
    const label = $('status-label');
    const timeEl = $('status-time');
    const btnIn = $('btn-checkin');
    const btnOut = $('btn-checkout');

    // Check if user is on approved leave today
    let isOnLeave = false;
    try {
      const leaveData = await apiCall('/leave/my-requests');
      const requests = leaveData.requests || [];
      const today = new Date().toISOString().split('T')[0];
      
      const leaveToday = requests.find(req => 
        req.status === 'approved' && 
        req.start_date <= today && 
        req.end_date >= today
      );
      
      if (leaveToday) {
        isOnLeave = true;
      }
    } catch (e) {
      // If leave check fails, continue normally
    }

    if (isOnLeave) {
      dot.className = 'status-dot';
      label.textContent = '🚫 On Leave Today';
      timeEl.textContent = 'Cannot check-in';
      if (btnIn) btnIn.disabled = true;
      if (btnOut) btnOut.disabled = true;
      $('work-hours').textContent = '0h 0m';
    } else if (record && record.check_in && !record.check_out) {
      dot.className = 'status-dot checked-in';
      label.textContent = 'Checked In';
      timeEl.textContent = formatTime(record.check_in);
      if (btnIn) btnIn.disabled = true;
      if (btnOut) btnOut.disabled = false;
      startWorkTimer(record.check_in);
    } else if (record && record.check_in && record.check_out) {
      dot.className = 'status-dot checked-out';
      label.textContent = 'Work Done ✓';
      timeEl.textContent = formatTime(record.check_in) + ' → ' + formatTime(record.check_out);
      if (btnIn) btnIn.disabled = true;
      if (btnOut) btnOut.disabled = true;
      $('work-hours').textContent = formatHours(record.work_minutes);
    } else {
      dot.className = 'status-dot';
      label.textContent = 'Not Checked In';
      timeEl.textContent = '—';
      if (btnIn) btnIn.disabled = false;
      if (btnOut) btnOut.disabled = true;
      $('work-hours').textContent = '0h 0m';
    }
  } catch (e) {
    $('status-label').textContent = 'Error loading status';
  }
}

function startWorkTimer(checkInISO) {
  if (timerInterval) clearInterval(timerInterval);
  const checkInTime = new Date(checkInISO).getTime();
  function update() {
    const diff = Math.floor((Date.now() - checkInTime) / 60000);
    $('work-hours').textContent = formatHours(diff);
  }
  update();
  timerInterval = setInterval(update, 60000);
}

async function loadWeekGrid() {
  try {
    const data = await apiCall('/attendance/week');
    const grid = $('week-grid');
    const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const todayIdx = (new Date().getDay() + 6) % 7;

    grid.innerHTML = days.map((d, i) => {
      const rec = data.week ? data.week[i] : null;
      const isToday = i === todayIdx;
      const dotClass = rec?.present ? 'present' : (i < todayIdx ? 'absent' : '');
      return `<div class="week-day">
        <div class="week-day-name">${d}</div>
        <div class="week-day-dot ${dotClass} ${isToday ? 'today' : ''}"></div>
        <div class="week-day-hrs">${rec?.hours || ''}</div>
      </div>`;
    }).join('');
  } catch { }
}

async function loadEmployeeLeaveRequests() {
  try {
    const data = await apiCall('/leave/my-requests');
    const requests = data.requests || [];
    const list = $('employee-leave-list');
    
    if (!list) return;
    
    if (!requests.length) {
      list.innerHTML = '<div style="color:var(--text2);font-size:12px;text-align:center;padding:16px;">No leave requests yet</div>';
      return;
    }
    
    list.innerHTML = requests.map(req => {
      const statusColor = req.status === 'pending' ? 'var(--yellow)' 
                         : req.status === 'approved' ? 'var(--green)'
                         : 'var(--red)';
      const statusSymbol = req.status === 'pending' ? '⏳'
                          : req.status === 'approved' ? '✅'
                          : '❌';
      
      return `
        <div class="emp-card" style="flex-direction:column;align-items:flex-start;">
          <div style="display:flex;justify-content:space-between;width:100%;margin-bottom:8px;">
            <strong style="color:${statusColor}">${statusSymbol} ${req.leave_type.toUpperCase()}</strong>
            <span style="color:var(--text2);font-size:10px;">${req.start_date} to ${req.end_date}</span>
          </div>
          <div style="font-size:11px;color:var(--text2);width:100%;margin-bottom:6px;">
            <strong>${req.days_requested} days</strong>
          </div>
          <div style="font-size:10px;color:var(--text2);">${req.reason || 'No reason provided'}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    console.log('Error:', e);
  }
}

async function applyForLeave() {
  const leaveType = $('leave-type').value;
  const startDate = $('leave-start-date').value;
  const endDate = $('leave-end-date').value;
  const reason = $('leave-reason').value;
  const msgDiv = $('leave-form-msg');
  
  if (!leaveType || !startDate || !endDate) {
    msgDiv.textContent = '❌ Please fill all fields';
    msgDiv.className = 'alert alert-error';
    msgDiv.classList.remove('hidden');
    return;
  }
  
  msgDiv.classList.add('hidden');
  const btn = $('btn-apply-leave');
  btn.disabled = true;
  btn.textContent = 'Applying...';
  
  try {
    const data = await apiCall('/leave/request', 'POST', {
      leave_type: leaveType,
      start_date: startDate,
      end_date: endDate,
      reason: reason || ''
    });
    
    if (data.success) {
      msgDiv.textContent = '✅ Leave request submitted!';
      msgDiv.className = 'alert';
      msgDiv.style.background = 'rgba(0,229,160,0.15)';
      msgDiv.style.border = '1px solid rgba(0,229,160,0.3)';
      msgDiv.style.color = 'var(--green)';
      msgDiv.classList.remove('hidden');
      
      $('leave-type').value = '';
      $('leave-start-date').value = '';
      $('leave-end-date').value = '';
      $('leave-reason').value = '';
      
      setTimeout(() => loadEmployeeLeaveRequests(), 1000);
    } else {
      msgDiv.textContent = '❌ ' + (data.message || 'Error');
      msgDiv.className = 'alert alert-error';
      msgDiv.classList.remove('hidden');
    }
  } catch (e) {
    msgDiv.textContent = '❌ Server error';
    msgDiv.className = 'alert alert-error';
    msgDiv.classList.remove('hidden');
  }
  
  btn.disabled = false;
  btn.textContent = 'Apply for Leave';
}

// ========================================
// ADMIN PANEL - 3 TABS (Attendance, Employees, Leave)
// ========================================
async function loadAdminPanel() {
  showScreen('admin');
  $('admin-name').textContent = currentUser.name || 'Admin';
  
  const topbarRole = document.querySelector('.topbar-role');
  if (topbarRole) {
    topbarRole.textContent = 'ADMIN';
  }

  $('filter-date').value = getTodayStr();
  
  $('tab-attendance').addEventListener('click', () => switchTab('attendance'));
  $('tab-employees').addEventListener('click', () => switchTab('employees'));
  $('tab-leave').addEventListener('click', () => switchTab('leave'));
  
  $('btn-save-emp').addEventListener('click', saveEmployee);
  
  // Download button setup
  const downloadBtn = $('btn-download-attendance');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', downloadAttendance);
  }
  
  // Download type selector setup - show/hide date inputs
  const downloadTypeSelect = $('download-type');
  if (downloadTypeSelect) {
    downloadTypeSelect.addEventListener('change', (e) => {
      const type = e.target.value;
      $('date-input-day').style.display = type === 'day' ? 'block' : 'none';
      $('date-input-range').style.display = type === 'range' ? 'block' : 'none';
    });
  }
  
  await loadAdminData();
  $('filter-date').addEventListener('change', loadAdminData);
  $('filter-search').addEventListener('input', filterTable);
  await loadLeaveRequests();

  $('admin-logout').addEventListener('click', logout);
}

function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  $(`tab-${tab}`).classList.add('active');
  $('tab-content-attendance').classList.toggle('hidden', tab !== 'attendance');
  $('tab-content-employees').classList.toggle('hidden', tab !== 'employees');
  $('tab-content-leave').classList.toggle('hidden', tab !== 'leave');
  if (tab === 'employees') loadEmployeeList();
  if (tab === 'leave') loadLeaveRequests();
}

let allAdminRows = [];

async function loadAdminData() {
  const date = $('filter-date').value || getTodayStr();
  try {
    const data = await apiCall(`/attendance/admin/attendance?date=${date}`);
    allAdminRows = data.records || [];

    const present = allAdminRows.filter(r => r.status === 'present').length;
    const absent = allAdminRows.filter(r => r.status === 'absent').length;
    const late = allAdminRows.filter(r => r.status === 'late').length;
    $('stat-present').textContent = present;
    $('stat-absent').textContent = absent;
    $('stat-late').textContent = late;
    $('stat-total').textContent = allAdminRows.length;

    renderTable(allAdminRows);
  } catch (e) {
    console.log('Error:', e);
  }
}

function renderTable(rows) {
  const tbody = $('admin-table-body');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text2);padding:16px">No records</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => {
    const statusBadge = r.status === 'present' ? `<span class="badge badge-p">Present</span>`
      : r.status === 'late' ? `<span class="badge badge-l">Late</span>`
        : `<span class="badge badge-a">Absent</span>`;
    return `<tr>
      <td><div style="font-weight:600;font-size:12px">${r.name}</div><div style="font-size:10px;color:var(--text2)">${r.employee_id}</div></td>
      <td>${formatTime(r.check_in)}</td>
      <td>${formatTime(r.check_out)}</td>
      <td>${r.work_minutes ? formatHours(r.work_minutes) : '—'}</td>
      <td>${statusBadge}</td>
    </tr>`;
  }).join('');
}

function filterTable() {
  const q = $('filter-search').value.toLowerCase();
  const filtered = allAdminRows.filter(r =>
    r.name.toLowerCase().includes(q) || r.employee_id.toLowerCase().includes(q)
  );
  renderTable(filtered);
}

async function downloadAttendance() {
  const downloadType = $('download-type').value;
  
  if (!downloadType) {
    alert('❌ Please select a download type');
    return;
  }

  let fromDate, toDate, filename;

  if (downloadType === 'day') {
    fromDate = $('download-date-day').value;
    if (!fromDate) {
      alert('❌ Please select a date');
      return;
    }
    toDate = fromDate;
    filename = `attendance_${fromDate}.csv`;
  } else if (downloadType === 'range') {
    fromDate = $('download-date-from').value;
    toDate = $('download-date-to').value;
    if (!fromDate || !toDate) {
      alert('❌ Please select both From and To dates');
      return;
    }
    if (new Date(fromDate) > new Date(toDate)) {
      alert('❌ From date must be before To date');
      return;
    }
    filename = `attendance_${fromDate}_to_${toDate}.csv`;
  }

  const btn = $('btn-download-attendance');
  btn.disabled = true;
  btn.textContent = 'Downloading...';
  
  try {
    const endpoint = `/attendance/admin/export-pivot?type=range&date_from=${fromDate}&date_to=${toDate}`;

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('att_token')}`
      }
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      alert('✅ Attendance downloaded successfully!');
    } else {
      alert('❌ Download failed');
    }
  } catch (e) {
    alert('❌ Server error: ' + e.message);
  }
  
  btn.disabled = false;
  btn.textContent = 'Download';
}

async function loadEmployeeList() {
  try {
    const data = await apiCall('/admin/employees');
    const employees = data.employees || [];
    const list = $('emp-list');
    
    if (!employees.length) {
      list.innerHTML = '<div style="color:var(--text2);font-size:12px;text-align:center;padding:16px">No employees</div>';
      return;
    }
    
    list.innerHTML = employees.map(emp => `
      <div class="emp-card">
        <div style="flex:1;">
          <div class="emp-card-name">${emp.name}</div>
          <div class="emp-card-meta">${emp.email}</div>
        </div>
        <button class="btn-del" data-id="${emp.employee_id}" style="padding:4px 8px;background:rgba(255,71,87,0.2);border:1px solid rgba(255,71,87,0.3);color:var(--red);border-radius:4px;cursor:pointer;font-size:10px;">Delete</button>
      </div>
    `).join('');
    
    document.querySelectorAll('.btn-del').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (confirm('Delete this employee?')) {
          await deleteEmployee(btn.getAttribute('data-id'));
        }
      });
    });
  } catch (e) {
    console.log('Error:', e);
  }
}

async function saveEmployee() {
  const empId = $('f-empid').value.trim();
  const name = $('f-name').value.trim();
  const email = $('f-email').value.trim();
  const dept = $('f-dept').value.trim();
  const role = $('f-role').value || 'employee';
  const pass = $('f-pass').value.trim();

  if (!empId || !name || !email || !pass) {
    alert('❌ Please fill all fields!');
    return;
  }

  $('btn-save-emp').disabled = true;
  $('btn-save-emp').textContent = 'Saving...';

  try {
    const data = await apiCall('/admin/employees', 'POST', {
      employee_id: empId,
      name: name,
      email: email,
      department: dept || 'General',
      role: role,
      password: pass
    });

    if (data.success) {
      alert('✅ Employee added!');
      $('f-empid').value = '';
      $('f-name').value = '';
      $('f-email').value = '';
      $('f-dept').value = '';
      $('f-role').value = 'employee';
      $('f-pass').value = '';
      await loadEmployeeList();
    } else {
      alert('❌ Error: ' + (data.message || 'Failed'));
    }
  } catch (e) {
    alert('❌ Server error');
  }

  $('btn-save-emp').disabled = false;
  $('btn-save-emp').textContent = 'Save Employee';
}

async function deleteEmployee(empId) {
  try {
    const data = await apiCall(`/admin/employees/${empId}`, 'DELETE');
    if (data.success) {
      await loadEmployeeList();
    } else {
      alert('Error: ' + (data.message || 'Failed'));
    }
  } catch {
    alert('Server error');
  }
}

async function loadLeaveRequests() {
  try {
    const data = await apiCall('/leave/pending');
    const requests = data.requests || [];
    
    $('stat-leave-pending').textContent = requests.filter(r => r.status === 'pending').length;
    $('stat-leave-approved').textContent = requests.filter(r => r.status === 'approved').length;
    $('stat-leave-rejected').textContent = requests.filter(r => r.status === 'rejected').length;
    $('stat-leave-total').textContent = requests.length;
    
    renderLeaveRequests(requests);
  } catch (e) {
    console.log('Error:', e);
  }
}

function renderLeaveRequests(requests) {
  const tbody = $('leave-requests-body');
  
  if (!requests.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text2);padding:16px">No requests</td></tr>';
    return;
  }
  
  tbody.innerHTML = requests.map(req => {
    const statusBadge = req.status === 'pending' ? `<span class="badge" style="background:rgba(255,211,42,0.15);color:var(--yellow);">Pending</span>`
      : req.status === 'approved' ? `<span class="badge badge-p">Approved</span>`
        : `<span class="badge badge-a">Rejected</span>`;
    
    const actionBtn = req.status === 'pending' 
      ? `<button class="btn-approve" data-id="${req.id}" style="padding:4px 8px;background:rgba(0,229,160,0.2);border:1px solid rgba(0,229,160,0.3);color:var(--green);border-radius:4px;cursor:pointer;font-size:10px;margin-right:4px;">✓</button><button class="btn-reject" data-id="${req.id}" style="padding:4px 8px;background:rgba(255,71,87,0.2);border:1px solid rgba(255,71,87,0.3);color:var(--red);border-radius:4px;cursor:pointer;font-size:10px;">✗</button>`
      : '-';
    
    return `<tr>
      <td><div style="font-weight:600;font-size:12px">${req.employee.name}</div><div style="font-size:10px;color:var(--text2)">${req.employee.employee_id}</div></td>
      <td style="font-size:11px;text-transform:capitalize;">${req.leave_type}</td>
      <td style="font-size:11px;">${req.start_date} to ${req.end_date}</td>
      <td style="font-size:11px;"><strong>${req.days_requested}</strong></td>
      <td>${statusBadge}</td>
      <td>${actionBtn}</td>
    </tr>`;
  }).join('');
  
  document.querySelectorAll('.btn-approve').forEach(btn => {
    btn.addEventListener('click', async () => {
      await approveLeave(btn.getAttribute('data-id'));
    });
  });
  
  document.querySelectorAll('.btn-reject').forEach(btn => {
    btn.addEventListener('click', async () => {
      const reason = prompt('Reason for rejection:');
      if (reason !== null) {
        await rejectLeave(btn.getAttribute('data-id'), reason);
      }
    });
  });
}

async function approveLeave(requestId) {
  try {
    const data = await apiCall('/leave/approve', 'POST', { request_id: parseInt(requestId) });
    if (data.success) {
      await loadLeaveRequests();
    } else {
      alert('Error: ' + (data.message || 'Failed'));
    }
  } catch (e) {
    alert('Server error');
  }
}

async function rejectLeave(requestId, reason) {
  try {
    const data = await apiCall('/leave/reject', 'POST', { 
      request_id: parseInt(requestId),
      rejection_reason: reason
    });
    if (data.success) {
      await loadLeaveRequests();
    } else {
      alert('Error: ' + (data.message || 'Failed'));
    }
  } catch (e) {
    alert('Server error');
  }
}

try {
  $('leave-filter-status').addEventListener('change', async () => {
    const status = $('leave-filter-status').value;
    const data = await apiCall(`/leave/pending${status ? '?status=' + status : ''}`);
    renderLeaveRequests(data.requests || []);
  });
} catch (e) {}

// ===== LOGOUT =====
async function logout() {
  if (timerInterval) clearInterval(timerInterval);
  
  // Check if user is currently checked in
  try {
    const data = await apiCall('/attendance/today');
    const record = data.record;
    
    // If checked in but not checked out, show custom modal
    if (record && record.check_in && !record.check_out) {
      // Show custom logout modal
      const modal = $('logout-modal');
      modal.classList.remove('hidden');
      
      // Handle button clicks
      const cancelBtn = $('logout-modal-cancel');
      const confirmBtn = $('logout-modal-confirm');
      
      return new Promise((resolve) => {
        cancelBtn.onclick = () => {
          modal.classList.add('hidden');
          resolve(false);
        };
        
        confirmBtn.onclick = async () => {
          modal.classList.add('hidden');
          
          // Auto-checkout
          try {
            await apiCall('/attendance/checkout', 'POST');
            console.log('✅ Auto-checked out');
          } catch (e) {
            console.log('⚠️ Auto-checkout failed, but logging out anyway');
          }
          
          // Proceed with logout
          proceedWithLogout();
          resolve(true);
        };
      });
    }
  } catch (e) {
    console.log('Could not check status before logout');
  }
  
  // If not checked in, proceed directly
  proceedWithLogout();
}

function proceedWithLogout() {
  localStorage.removeItem('att_token');
  localStorage.removeItem('att_user');
  currentUser = null;
  $('login-id').value = '';
  $('login-pass').value = '';
  $('login-error').classList.add('hidden');
  showScreen('login');
}