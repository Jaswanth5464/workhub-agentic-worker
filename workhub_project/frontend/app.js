// WorkHub HR App - Clean Architecture Directly Connected to SQLite Database API

window.store = {
    employees: [],
    expenses: [],
    leaves: [],
    benefits: [],
    tasks: [],
    emails: [],
    documents: [],
    activities: []
};

// Dynamically determine the backend API base URL
const API_BASE = (window.location.port === '8000') ? '/api/hr' : 'http://localhost:8000/api/hr';

// Utility: HTML Escaping
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// Utility: Parse Amount for Summary
function parseAmount(amtStr) {
    if (typeof amtStr === 'number') return amtStr;
    if (!amtStr) return 0;
    const num = parseInt(String(amtStr).replace(/[^0-9]/g, ''), 10);
    return isNaN(num) ? 0 : num;
}

// Utility: Build Employee Select Dropdown Options dynamically from SQLite database
function getEmployeeOptionsHtml(selectedVal = '', includeAdmin = true) {
    let options = '';
    if (includeAdmin) {
        options += `<option value="Admin" ${selectedVal === 'Admin' ? 'selected' : ''}>Admin (HR Manager)</option>`;
    }
    if (window.store && window.store.employees && window.store.employees.length > 0) {
        const sorted = [...window.store.employees].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        sorted.forEach(emp => {
            const val = emp.name || emp.id;
            const isSel = (selectedVal === val || selectedVal === emp.id || selectedVal === emp.name) ? 'selected' : '';
            const dept = emp.department ? ` - ${emp.department}` : '';
            options += `<option value="${escapeHtml(val)}" ${isSel}>${escapeHtml(emp.name)} (${escapeHtml(emp.id)}${escapeHtml(dept)})</option>`;
        });
    }
    return options;
}

// Utility: Build Employee Email Options dynamically
function getEmployeeEmailOptionsHtml(selectedEmail = '') {
    let options = '<option value="all@workhub.local">All Staff &lt;all@workhub.local&gt;</option>';
    if (window.store && window.store.employees && window.store.employees.length > 0) {
        const sorted = [...window.store.employees].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        sorted.forEach(emp => {
            const email = emp.email || `${(emp.name || 'emp').toLowerCase().replace(/\\s+/g, '.')}@workhub.local`;
            const isSel = (selectedEmail === email) ? 'selected' : '';
            options += `<option value="${escapeHtml(email)}" ${isSel}>${escapeHtml(emp.name)} &lt;${escapeHtml(email)}&gt;</option>`;
        });
    }
    return options;
}

// Update sidebar badge numbers in real-time
function updateSidebarBadges() {
    const pendingExpenses = (store.expenses || []).filter(e => e.status === 'pending').length;
    const pendingLeaves = (store.leaves || []).filter(l => l.status === 'pending').length;
    const totalPendingApprovals = pendingExpenses + pendingLeaves;
    const openTasks = (store.tasks || []).filter(t => t.status !== 'completed').length;
    const unreadEmails = (store.emails || []).filter(m => !m.read || m.read === 0).length;

    const leavesBadge = document.querySelector('.nav-item[data-view="leaves"] .badge') || document.getElementById('badge-leaves');
    if (leavesBadge) {
        leavesBadge.innerText = pendingLeaves;
        leavesBadge.style.display = pendingLeaves > 0 ? 'inline-block' : 'none';
    }

    const expBadge = document.querySelector('.nav-item[data-view="expenses"] .badge') || document.getElementById('badge-expenses');
    if (expBadge) {
        expBadge.innerText = pendingExpenses;
        expBadge.style.display = pendingExpenses > 0 ? 'inline-block' : 'none';
    }

    const taskBadge = document.querySelector('.nav-item[data-view="tasks"] .badge') || document.getElementById('badge-tasks');
    if (taskBadge) {
        taskBadge.innerText = openTasks;
        taskBadge.style.display = openTasks > 0 ? 'inline-block' : 'none';
    }

    const approvalsBadge = document.querySelector('.nav-item[data-view="approvals"] .badge') || document.getElementById('badge-approvals');
    if (approvalsBadge) {
        approvalsBadge.innerText = totalPendingApprovals;
        approvalsBadge.style.display = totalPendingApprovals > 0 ? 'inline-block' : 'none';
    }

    const emailBadge = document.querySelector('.nav-item[data-view="emails"] .badge') || document.getElementById('badge-emails');
    if (emailBadge) {
        emailBadge.innerText = unreadEmails;
        emailBadge.style.display = unreadEmails > 0 ? 'inline-block' : 'none';
    }
}

// Fetch all database tables directly from SQLite backend API
async function fetchStore() {
    const endpoints = ['employees', 'expenses', 'leaves', 'benefits', 'tasks', 'emails', 'documents', 'activities'];
    
    await Promise.all(endpoints.map(async (ep) => {
        try {
            const res = await fetch(`${API_BASE}/${ep}/`, { cache: 'no-store' });
            if (res.ok) {
                const data = await res.json();
                if (ep === 'emails') {
                    window.store[ep] = data.map(m => ({
                        ...m,
                        from: m.from || m.from_email || 'HR System',
                        from_email: m.from_email || m.from || 'hr@workhub.local'
                    }));
                } else {
                    window.store[ep] = data;
                }
            }
        } catch (e) {
            // Silently handle temporary network hiccups during reload
        }
    }));

    updateSidebarBadges();
}

// Generate state key to prevent unnecessary DOM destruction during polling
function getViewStateKey(viewName) {
    if (!window.store) return '';
    switch (viewName) {
        case 'dashboard':
            return `dash-${store.employees.length}-${store.expenses.length}-${store.leaves.length}-${store.tasks.length}-${(store.activities || []).length}`;
        case 'employees':
            return `emp-${store.employees.length}-${JSON.stringify(store.employees.map(e => [e.id, e.status, e.role]))}-${window.currentSearchTerm || ''}`;
        case 'employee_profile':
            const emp = store.employees.find(e => String(e.id).toUpperCase() === String(window.currentEmpId).toUpperCase());
            return `emp-prof-${window.currentEmpId}-${JSON.stringify(emp || {})}`;
        case 'expenses':
            return `exp-${store.expenses.length}-${JSON.stringify(store.expenses.map(e => [e.id, e.status]))}-${window.expenseFilter || 'all'}-${window.currentExpenseSearchTerm || ''}`;
        case 'leaves':
            return `lv-${store.leaves.length}-${JSON.stringify(store.leaves.map(l => [l.id, l.status]))}-${window.currentLeaveSearchTerm || ''}`;
        case 'benefits':
            return `ben-${store.benefits.length}-${JSON.stringify(store.benefits.map(b => [b.id, b.status, b.coverage]))}`;
        case 'tasks':
            return `tsk-${store.tasks.length}-${JSON.stringify(store.tasks.map(t => [t.id, t.status, t.priority]))}-${window.currentTaskSearchTerm || ''}`;
        case 'approvals':
            const pLeaves = store.leaves.filter(l => l.status === 'pending').map(l => l.id);
            const pExps = store.expenses.filter(e => e.status === 'pending').map(e => e.id);
            return `appr-${pLeaves.join(',')}-${pExps.join(',')}`;
        case 'emails':
            return `eml-${store.emails.length}-${store.emails.filter(m => !m.read).map(m => m.id).join(',')}-${window.currentEmailSearchTerm || ''}`;
        case 'documents':
            return `doc-${store.documents.length}-${store.documents.map(d => d.id).join(',')}-${window.currentDocSearchTerm || ''}`;
        case 'departments':
            return `dept-${store.employees.length}-${window.currentDeptSearchTerm || ''}`;
        case 'reports':
            return `rep-${store.employees.length}-${store.expenses.length}-${store.tasks.length}`;
        case 'settings':
            return 'settings';
        default:
            return `${viewName}`;
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    const navItems = document.querySelectorAll('.nav-item');
    const viewContainer = document.getElementById('view-container');
    
    viewContainer.innerHTML = '<div style="padding: 2rem; text-align: center;"><i class="fa-solid fa-spinner fa-spin fa-2x text-primary"></i><p style="margin-top: 1rem;">Loading database records from SQLite...</p></div>';
    
    await fetchStore();
    
    let currentView = 'dashboard';
    let lastRenderedStateKey = '';
    window.currentEmpId = null;
    window.currentSearchTerm = '';
    window.expenseFilter = 'all';

    // View templates mapping
    const views = {
        dashboard: renderDashboard,
        employees: renderEmployees,
        employee_profile: renderEmployeeProfile,
        departments: renderDepartments,
        expenses: renderExpenses,
        leaves: renderLeaves,
        benefits: renderBenefits,
        tasks: renderTasks,
        approvals: renderApprovals,
        emails: renderEmails,
        documents: renderDocuments,
        reports: renderReports,
        settings: renderSettings
    };

    function switchView(viewName, data = null) {
        currentView = viewName;
        if (viewName === 'employee_profile' && data) {
            window.currentEmpId = data;
        }

        navItems.forEach(item => item.classList.remove('active'));
        const activeNavName = (viewName === 'employee_profile') ? 'employees' : viewName;
        const activeItem = document.querySelector(`.nav-item[data-view="${activeNavName}"]`);
        if (activeItem) activeItem.classList.add('active');

        if (views[viewName]) {
            viewContainer.innerHTML = views[viewName](data);
            attachEventListeners(viewName);
            lastRenderedStateKey = getViewStateKey(viewName);
        } else {
            viewContainer.innerHTML = `<h2>View Not Found</h2>`;
        }
    }

    // Real-time synchronization polling (safeguarded against disrupting active user input, modals, or unchanged state)
    setInterval(async () => {
        const isEditing = document.activeElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);
        const modalEl = document.getElementById('approval-modal');
        const aiModalEl = document.getElementById('ai-modal');
        const confirmModalEl = document.getElementById('confirm-dialog-modal');
        const isModalOpen = (modalEl && !modalEl.classList.contains('hidden')) || 
                            (aiModalEl && !aiModalEl.classList.contains('hidden')) ||
                            (confirmModalEl && !confirmModalEl.classList.contains('hidden'));
        
        await fetchStore();
        
        if (!isEditing && !isModalOpen && views[currentView]) {
            const newStateKey = getViewStateKey(currentView);
            // ONLY re-render if the state has genuinely mutated to protect Playwright locator stability
            if (newStateKey !== lastRenderedStateKey) {
                lastRenderedStateKey = newStateKey;
                if (currentView === 'employee_profile') {
                    if (window.currentEmpId) {
                        viewContainer.innerHTML = views['employee_profile'](window.currentEmpId);
                        attachEventListeners('employee_profile');
                    }
                } else {
                    viewContainer.innerHTML = views[currentView]();
                    attachEventListeners(currentView);
                }
            }
        }
    }, 3000);

    // Event Delegation for Navigation
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const targetView = item.dataset.view;
            if (targetView) {
                switchView(targetView);
            }
        });
    });

    // ==========================================
    // --- View Renderers ---
    // ==========================================

    function renderDashboard() {
        const totalEmployees = store.employees.length;
        const pendingExpenses = store.expenses.filter(e => e.status === 'pending').length;
        const pendingLeaves = store.leaves.filter(l => l.status === 'pending').length;
        const pendingApprovals = pendingExpenses + pendingLeaves;
        const openTasks = store.tasks.filter(t => t.status !== 'completed').length;
        
        let totalExpAmount = 0;
        store.expenses.filter(e => e.status === 'approved').forEach(e => {
            totalExpAmount += parseAmount(e.amount);
        });

        // Compute dynamic live recent activities from audit logs + latest transactions
        let activityRows = [];
        if (store.activities && store.activities.length > 0) {
            activityRows = store.activities.slice(0, 5).map((act, index) => {
                let eventText = `${act.action} in ${act.table_name} (${act.record_id})`;
                let userText = "System Admin";
                let statusText = "COMPLETED";
                let statusClass = "approved";

                try {
                    const parsed = JSON.parse(act.details);
                    if (act.table_name === 'expenses' && parsed.employee) userText = parsed.employee;
                    if (act.table_name === 'leaves' && parsed.employee) userText = parsed.employee;
                    if (act.table_name === 'employees' && parsed.name) userText = parsed.name;
                    if (parsed.status) {
                        statusText = parsed.status.toUpperCase();
                        statusClass = parsed.status === 'pending' ? 'pending' : (parsed.status === 'rejected' ? 'rejected' : 'approved');
                    }
                } catch (e) {}

                const rowName = act.name || userText || eventText;
                const actId = act.id || `act-${index}`;
                return `
                    <tr data-testid="row-activity-${escapeHtml(actId)}" aria-label="${escapeHtml(rowName)}">
                        <td><strong>${escapeHtml(eventText)}</strong></td>
                        <td>${escapeHtml(userText)}</td>
                        <td>${act.timestamp ? act.timestamp.replace('T', ' ').substring(0, 19) : 'Recently'}</td>
                        <td><span class="status-tag ${statusClass}">${statusText}</span></td>
                    </tr>
                `;
            });
        }

        // Fallback or additional live events from expenses and leaves
        if (activityRows.length === 0) {
            const expRecent = store.expenses.slice(-3).reverse().map(exp => `
                <tr data-testid="row-activity-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(exp.name || exp.employee || exp.id)}">
                    <td>Expense Submitted (${escapeHtml(exp.id)})</td>
                    <td>${escapeHtml(exp.employee)}</td>
                    <td>${escapeHtml(exp.date || 'Recently')}</td>
                    <td><span class="status-tag ${exp.status}">${(exp.status || '').toUpperCase()}</span></td>
                </tr>
            `);
            const leaveRecent = store.leaves.slice(-3).reverse().map(lv => `
                <tr data-testid="row-activity-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lv.name || lv.employee || lv.id)}">
                    <td>Leave Request (${escapeHtml(lv.id)})</td>
                    <td>${escapeHtml(lv.employee)}</td>
                    <td>${escapeHtml(lv.dates || 'Recently')}</td>
                    <td><span class="status-tag ${lv.status}">${(lv.status || '').toUpperCase()}</span></td>
                </tr>
            `);
            activityRows = [...expRecent, ...leaveRecent];
        }

        return `
            <div class="card-header">
                <h2>Overview Dashboard</h2>
                <button class="btn-primary" id="btn-generate-report" data-testid="btn-generate-report" aria-label="Generate Overview Report"><i class="fa-solid fa-download" aria-hidden="true"></i> Generate Report</button>
            </div>
            
            <div class="dashboard-grid">
                <div class="stat-card">
                    <div class="stat-icon blue"><i class="fa-solid fa-users" aria-hidden="true"></i></div>
                    <div class="stat-details">
                        <h3>Total Employees</h3>
                        <p id="stat-total-employees" data-testid="stat-total-employees">${totalEmployees}</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon orange"><i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i></div>
                    <div class="stat-details">
                        <h3>Pending Approvals</h3>
                        <p id="stat-pending-approvals" data-testid="stat-pending-approvals">${pendingApprovals}</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon red"><i class="fa-solid fa-ticket" aria-hidden="true"></i></div>
                    <div class="stat-details">
                        <h3>Open HR Tasks</h3>
                        <p id="stat-open-tasks" data-testid="stat-open-tasks">${openTasks}</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon green"><i class="fa-solid fa-indian-rupee-sign" aria-hidden="true"></i></div>
                    <div class="stat-details">
                        <h3>Expenses Processed</h3>
                        <p id="stat-expenses-processed" data-testid="stat-expenses-processed">₹${totalExpAmount.toLocaleString('en-IN')}</p>
                    </div>
                </div>
            </div>

            <div class="card-header" style="margin-top: 2rem;">
                <h2>Recent Activity</h2>
            </div>
            <table class="data-table" aria-label="Recent Activities Table">
                <thead>
                    <tr>
                        <th scope="col">EVENT</th>
                        <th scope="col">USER</th>
                        <th scope="col">TIME</th>
                        <th scope="col">STATUS</th>
                    </tr>
                </thead>
                <tbody>
                    ${activityRows.length > 0 ? activityRows.join('') : '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No recent activities found in database.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderEmployees() {
        let filteredData = window.currentSearchTerm ? 
            store.employees.filter(e => 
                (e.name && e.name.toLowerCase().includes(window.currentSearchTerm)) || 
                (e.id && e.id.toLowerCase().includes(window.currentSearchTerm)) ||
                (e.department && e.department.toLowerCase().includes(window.currentSearchTerm)) ||
                (e.role && e.role.toLowerCase().includes(window.currentSearchTerm)) ||
                (e.email && e.email.toLowerCase().includes(window.currentSearchTerm))
            ) 
            : store.employees;

        let rows = filteredData.map(emp => `
            <tr data-emp-id="${escapeHtml(emp.id)}" data-testid="row-emp-${escapeHtml(emp.id)}" class="employee-row" style="cursor: pointer;" aria-label="${escapeHtml(emp.name)}">
                <td><strong>${escapeHtml(emp.name)}</strong><br><small style="color: #6b7280">${escapeHtml(emp.email)}</small></td>
                <td><strong>${escapeHtml(emp.id)}</strong></td>
                <td>${escapeHtml(emp.department)}</td>
                <td>${escapeHtml(emp.role)}</td>
                <td><span class="status-tag ${emp.status === 'active' ? 'active' : 'pending'}">${escapeHtml((emp.status || '').replace('_', ' ').toUpperCase())}</span></td>
                <td>
                    <button class="icon-btn btn-view-emp" data-id="${escapeHtml(emp.id)}" data-testid="btn-view-emp-${escapeHtml(emp.id)}" aria-label="${escapeHtml(emp.name)}" title="View Profile for ${escapeHtml(emp.name)}"><i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>
                </td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Employee Directory (${store.employees.length} Total)</h2>
                <div style="display: flex; gap: 1rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="emp-search" name="emp-search" class="inner-search-input" data-testid="emp-search-input" value="${escapeHtml(window.currentSearchTerm || '')}" placeholder="Search employees by name, ID, role..." aria-label="Search employees by name, ID, or role" autocomplete="off">
                    </div>
                    <button class="btn-primary" id="btn-add-employee" data-testid="btn-add-employee" aria-label="Add New Employee"><i class="fa-solid fa-user-plus" aria-hidden="true"></i> Add Employee</button>
                </div>
            </div>
            <table class="data-table" aria-label="Employee Directory Table">
                <thead>
                    <tr>
                        <th scope="col">Employee</th>
                        <th scope="col">ID</th>
                        <th scope="col">Department</th>
                        <th scope="col">Role</th>
                        <th scope="col">Status</th>
                        <th scope="col">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length > 0 ? rows : '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No employees match the search filter.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderEmployeeProfile(empId) {
        if (!empId && window.currentEmpId) empId = window.currentEmpId;
        window.currentEmpId = empId;
        
        const emp = store.employees.find(e => String(e.id).trim().toUpperCase() === String(empId).trim().toUpperCase());
        if (!emp) {
            return `
                <div class="card-header">
                    <button class="btn-secondary" id="btn-back-employees" data-testid="btn-back-employees" aria-label="Back to Directory"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i> Back to Directory</button>
                    <h2>Employee Not Found (${escapeHtml(empId || 'Unknown')})</h2>
                </div>
                <div style="padding: 2rem; background: var(--card-bg); border-radius: var(--radius); border: 1px solid var(--border); margin-top: 1rem;">
                    <p>The requested employee record could not be loaded from SQLite. Please verify the ID or return to the directory.</p>
                </div>
            `;
        }

        return `
            <div class="card-header">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <button class="btn-secondary" id="btn-back-employees" data-testid="btn-back-employees" aria-label="Back to Directory"><i class="fa-solid fa-arrow-left" aria-hidden="true"></i> Back</button>
                    <h2>Employee Profile: ${escapeHtml(emp.name)}</h2>
                </div>
                <button class="btn-primary" id="btn-save-emp" data-testid="btn-save-emp" aria-label="Save Employee Profile Changes"><i class="fa-solid fa-save" aria-hidden="true"></i> Save Changes</button>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-top: 2rem;">
                <!-- Personal Information -->
                <div style="background: var(--card-bg); padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border);">
                    <h3 style="margin-bottom: 1.5rem; font-size: 1.1rem;"><i class="fa-solid fa-user text-primary" style="margin-right: 0.5rem;" aria-hidden="true"></i> Personal Information</h3>
                    
                    <div style="margin-bottom: 1rem;">
                        <label for="emp-name" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Full Name</label>
                        <input type="text" id="emp-name" data-testid="emp-profile-name" aria-label="Full Name" value="${escapeHtml(emp.name)}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" disabled>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label for="emp-email" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Email Address</label>
                        <input type="email" id="emp-email" data-testid="emp-profile-email" aria-label="Email Address" value="${escapeHtml(emp.email)}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" disabled>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label for="emp-phone" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Phone Number</label>
                        <input type="text" id="emp-phone" data-testid="emp-profile-phone" aria-label="Phone Number" value="${escapeHtml(emp.phone || '')}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label for="emp-emergency-contact" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Emergency Contact (Name & Phone)</label>
                        <input type="text" id="emp-emergency-contact" data-testid="emp-profile-emergency-contact" aria-label="Emergency Contact" value="${escapeHtml(emp.emergencyContact || '')}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                </div>

                <!-- Employment Details -->
                <div style="background: var(--card-bg); padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border);">
                    <h3 style="margin-bottom: 1.5rem; font-size: 1.1rem;"><i class="fa-solid fa-briefcase text-primary" style="margin-right: 0.5rem;" aria-hidden="true"></i> Employment Details</h3>
                    
                    <div style="margin-bottom: 1rem;">
                        <label for="emp-id-field" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Employee ID</label>
                        <input type="text" id="emp-id-field" data-testid="emp-profile-id" aria-label="Employee ID" value="${escapeHtml(emp.id)}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" disabled>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label for="emp-role" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Role / Position</label>
                        <input type="text" id="emp-role" data-testid="emp-profile-role" aria-label="Role or Position" value="${escapeHtml(emp.role || '')}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label for="emp-dept" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Department</label>
                        <select id="emp-dept" data-testid="emp-profile-dept" aria-label="Department" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="Engineering" ${emp.department === 'Engineering' ? 'selected' : ''}>Engineering</option>
                            <option value="HR" ${emp.department === 'HR' ? 'selected' : ''}>HR</option>
                            <option value="Finance" ${emp.department === 'Finance' ? 'selected' : ''}>Finance</option>
                            <option value="Marketing" ${emp.department === 'Marketing' ? 'selected' : ''}>Marketing</option>
                            <option value="Sales" ${emp.department === 'Sales' ? 'selected' : ''}>Sales</option>
                            <option value="Design" ${emp.department === 'Design' ? 'selected' : ''}>Design</option>
                        </select>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label for="emp-status" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Status</label>
                        <select id="emp-status" data-testid="emp-profile-status" aria-label="Employment Status" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="active" ${emp.status === 'active' ? 'selected' : ''}>Active</option>
                            <option value="on_leave" ${emp.status === 'on_leave' ? 'selected' : ''}>On Leave</option>
                            <option value="inactive" ${emp.status === 'inactive' ? 'selected' : ''}>Inactive</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    }

    function renderExpenses() {
        const filterVal = window.expenseFilter || 'all';
        const search = (window.currentExpenseSearchTerm || '').toLowerCase().trim();
        let filteredExpenses = store.expenses.filter(e => {
            const matchesStatus = (filterVal === 'all' || e.status === filterVal);
            const matchesSearch = !search || 
                (e.id && e.id.toLowerCase().includes(search)) ||
                (e.employee && e.employee.toLowerCase().includes(search)) ||
                (e.category && e.category.toLowerCase().includes(search)) ||
                (e.amount && String(e.amount).toLowerCase().includes(search)) ||
                (e.date && e.date.toLowerCase().includes(search));
            return matchesStatus && matchesSearch;
        });

        let rows = filteredExpenses.map(exp => {
            const expName = exp.name || exp.employee || exp.id;
            return `
            <tr data-testid="row-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(expName)}">
                <td><strong>${escapeHtml(exp.id)}</strong></td>
                <td>${escapeHtml(exp.employee)}</td>
                <td>${escapeHtml(exp.category)}</td>
                <td><strong>${escapeHtml(exp.amount)}</strong></td>
                <td>${escapeHtml(exp.date)}</td>
                <td><span class="status-tag ${exp.status}" id="status-${escapeHtml(exp.id)}">${escapeHtml((exp.status || '').toUpperCase())}</span></td>
                <td>
                    ${exp.status === 'pending' ? 
                        `<button class="btn-primary btn-sm btn-review-expense" id="review-${escapeHtml(exp.id)}" data-id="${escapeHtml(exp.id)}" data-testid="btn-review-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(expName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Review</button>` : 
                        `<button class="btn-secondary btn-sm" disabled data-testid="btn-processed-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(expName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Processed</button>`
                    }
                </td>
            </tr>
        `;}).join('');

        return `
            <div class="card-header">
                <h2>Expense Management (${filteredExpenses.length} Total)</h2>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="exp-search" name="exp-search" class="inner-search-input" data-testid="exp-search-input" value="${escapeHtml(window.currentExpenseSearchTerm || '')}" placeholder="Search expenses by employee, category, ID..." aria-label="Search expenses by employee, category, or ID" autocomplete="off">
                    </div>
                    <button class="btn-primary" id="btn-add-expense" data-testid="btn-add-expense" aria-label="Add New Expense"><i class="fa-solid fa-plus" aria-hidden="true"></i> Add Expense</button>
                    <button class="btn-secondary" id="btn-filter-expenses" data-testid="btn-filter-expenses" aria-label="Filter Expenses by Status"><i class="fa-solid fa-filter" aria-hidden="true"></i> Filter (${filterVal.toUpperCase()})</button>
                </div>
            </div>
            <table class="data-table" aria-label="Expense Management Table">
                <thead>
                    <tr>
                        <th scope="col">Expense ID</th>
                        <th scope="col">Employee</th>
                        <th scope="col">Category</th>
                        <th scope="col">Amount</th>
                        <th scope="col">Date</th>
                        <th scope="col">Status</th>
                        <th scope="col">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length > 0 ? rows : '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No expenses match the search filter.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderLeaves() {
        const search = (window.currentLeaveSearchTerm || '').toLowerCase().trim();
        let filteredLeaves = store.leaves.filter(lv => {
            return !search ||
                (lv.id && lv.id.toLowerCase().includes(search)) ||
                (lv.employee && lv.employee.toLowerCase().includes(search)) ||
                (lv.type && lv.type.toLowerCase().includes(search)) ||
                (lv.dates && lv.dates.toLowerCase().includes(search)) ||
                (lv.status && lv.status.toLowerCase().includes(search));
        });

        let rows = filteredLeaves.map(lv => {
            const lvName = lv.name || lv.employee || lv.id;
            return `
            <tr data-testid="row-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}">
                <td><strong>${escapeHtml(lv.id)}</strong></td>
                <td>${escapeHtml(lv.employee)}</td>
                <td>${escapeHtml(lv.type)}</td>
                <td>${escapeHtml(lv.dates)}</td>
                <td><span class="status-tag ${lv.status}">${escapeHtml((lv.status || '').toUpperCase())}</span></td>
                <td>
                    ${lv.status === 'pending' ? 
                        `<button class="btn-primary btn-sm btn-action-leave" data-id="${escapeHtml(lv.id)}" data-action="approve" data-testid="btn-approve-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem; margin-right: 0.25rem;">Approve</button>
                         <button class="btn-secondary btn-sm btn-action-leave" data-id="${escapeHtml(lv.id)}" data-action="reject" data-testid="btn-reject-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Reject</button>` : 
                        `<button class="btn-secondary btn-sm" disabled data-testid="btn-processed-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Processed</button>`
                    }
                </td>
            </tr>
        `;}).join('');

        return `
            <div class="card-header">
                <h2>Leave Requests (${filteredLeaves.length} Total)</h2>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="leave-search" name="leave-search" class="inner-search-input" data-testid="leave-search-input" value="${escapeHtml(window.currentLeaveSearchTerm || '')}" placeholder="Search leaves by employee, type, ID..." aria-label="Search leaves by employee, type, or ID" autocomplete="off">
                    </div>
                    <button class="btn-primary" id="btn-add-leave" data-testid="btn-add-leave" aria-label="Request Leave"><i class="fa-solid fa-plus" aria-hidden="true"></i> Request Leave</button>
                    <button class="btn-secondary" id="btn-view-calendar" data-testid="btn-view-calendar" aria-label="View Leave Calendar"><i class="fa-solid fa-calendar" aria-hidden="true"></i> View Calendar</button>
                </div>
            </div>
            <table class="data-table" aria-label="Leave Requests Table">
                <thead>
                    <tr>
                        <th scope="col">Request ID</th>
                        <th scope="col">Employee</th>
                        <th scope="col">Type</th>
                        <th scope="col">Dates</th>
                        <th scope="col">Status</th>
                        <th scope="col">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length > 0 ? rows : '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No leave requests match the search filter.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderBenefits() {
        let rows = store.benefits.map(ben => `
            <tr data-testid="row-benefit-${escapeHtml(ben.id)}" aria-label="${escapeHtml(ben.name)}">
                <td><strong>${escapeHtml(ben.id)}</strong></td>
                <td>${escapeHtml(ben.name)}</td>
                <td>${escapeHtml(ben.provider)}</td>
                <td>${escapeHtml(ben.coverage)}</td>
                <td>${escapeHtml(String(ben.enrolled || 0))}</td>
                <td><span class="status-tag ${ben.status === 'active' ? 'active' : 'pending'}">${escapeHtml((ben.status || '').toUpperCase())}</span></td>
                <td><button class="btn-secondary btn-sm btn-manage-benefit" data-id="${escapeHtml(ben.id)}" data-testid="btn-manage-benefit-${escapeHtml(ben.id)}" aria-label="${escapeHtml(ben.name)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Manage</button></td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Employee Benefits</h2>
                <button class="btn-primary" id="btn-add-benefit" data-testid="btn-add-benefit" aria-label="Add New Benefit"><i class="fa-solid fa-plus" aria-hidden="true"></i> Add Benefit</button>
            </div>
            <table class="data-table" aria-label="Employee Benefits Table">
                <thead>
                    <tr>
                        <th scope="col">ID</th>
                        <th scope="col">Benefit Name</th>
                        <th scope="col">Provider</th>
                        <th scope="col">Coverage</th>
                        <th scope="col">Enrolled</th>
                        <th scope="col">Status</th>
                        <th scope="col">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length > 0 ? rows : '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No benefits found in SQLite database.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderTasks() {
        const search = (window.currentTaskSearchTerm || '').toLowerCase().trim();
        let filteredTasks = store.tasks.filter(tsk => {
            return !search ||
                (tsk.id && tsk.id.toLowerCase().includes(search)) ||
                (tsk.title && tsk.title.toLowerCase().includes(search)) ||
                (tsk.assignedTo && tsk.assignedTo.toLowerCase().includes(search)) ||
                (tsk.priority && tsk.priority.toLowerCase().includes(search)) ||
                (tsk.status && tsk.status.toLowerCase().includes(search));
        });

        let rows = filteredTasks.map(tsk => {
            const taskName = tsk.name || tsk.title || tsk.id;
            return `
            <tr data-testid="row-task-${escapeHtml(tsk.id)}" aria-label="${escapeHtml(taskName)}">
                <td><strong>${escapeHtml(tsk.id)}</strong></td>
                <td>${escapeHtml(tsk.title)}</td>
                <td>${escapeHtml(tsk.assignedTo)}</td>
                <td>${escapeHtml(tsk.dueDate)}</td>
                <td><span class="status-tag pending">${escapeHtml((tsk.priority || '').toUpperCase())}</span></td>
                <td><span class="status-tag ${tsk.status === 'pending' ? 'pending' : (tsk.status === 'completed' ? 'active' : 'approved')}">${escapeHtml((tsk.status || '').replace('_', ' ').toUpperCase())}</span></td>
                <td>
                    <button class="btn-secondary btn-sm btn-open-task" data-id="${escapeHtml(tsk.id)}" data-testid="btn-open-task-${escapeHtml(tsk.id)}" aria-label="${escapeHtml(taskName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Open Task</button>
                </td>
            </tr>
        `;}).join('');

        const openTasks = (store.tasks || []).filter(t => t.status !== 'completed').length;
        return `
            <div class="card-header">
                <h2>HR Tasks <span class="badge ${openTasks > 0 ? 'danger' : 'primary'}" style="margin-left: 0.5rem; font-size: 0.8rem;">${openTasks} Open</span></h2>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="task-search" name="task-search" class="inner-search-input" data-testid="task-search-input" value="${escapeHtml(window.currentTaskSearchTerm || '')}" placeholder="Search tasks by title, assignee, ID..." aria-label="Search tasks by title, assignee, or ID" autocomplete="off">
                    </div>
                    <button class="btn-primary" id="btn-new-task" data-testid="btn-new-task" aria-label="Create New HR Task"><i class="fa-solid fa-plus" aria-hidden="true"></i> New Task</button>
                </div>
            </div>
            <table class="data-table" aria-label="HR Tasks Table">
                <thead>
                    <tr>
                        <th scope="col">ID</th>
                        <th scope="col">Task</th>
                        <th scope="col">Assigned To</th>
                        <th scope="col">Due Date</th>
                        <th scope="col">Priority</th>
                        <th scope="col">Status</th>
                        <th scope="col">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length > 0 ? rows : '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No tasks match the search filter.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderEmails() {
        const search = (window.currentEmailSearchTerm || '').toLowerCase().trim();
        let filteredEmails = store.emails.filter(msg => {
            return !search ||
                (msg.from && msg.from.toLowerCase().includes(search)) ||
                (msg.from_email && msg.from_email.toLowerCase().includes(search)) ||
                (msg.subject && msg.subject.toLowerCase().includes(search)) ||
                (msg.body && msg.body.toLowerCase().includes(search));
        });

        let rows = filteredEmails.map(msg => {
            const emailName = msg.name || msg.from || msg.from_email || msg.subject;
            return `
            <div class="email-row" data-id="${escapeHtml(msg.id)}" data-testid="row-email-${escapeHtml(msg.id)}" aria-label="${escapeHtml(emailName)}" style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; gap: 1rem; cursor: pointer; background: ${msg.read ? 'transparent' : '#f0f4f8'};">
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                        <strong style="font-size: 0.95rem; color: ${msg.read ? 'var(--text-muted)' : 'var(--text-main)'};">${escapeHtml(msg.from || msg.from_email)}</strong>
                        <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(msg.date)}</span>
                    </div>
                    <div style="font-weight: ${msg.read ? '400' : '600'}; font-size: 0.95rem; margin-bottom: 0.25rem;">${escapeHtml(msg.subject)}</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(msg.body)}</div>
                </div>
            </div>
        `;}).join('');

        return `
            <div class="card-header">
                <h2>Admin Inbox (${filteredEmails.length} Messages)</h2>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="email-search" name="email-search" class="inner-search-input" data-testid="email-search-input" value="${escapeHtml(window.currentEmailSearchTerm || '')}" placeholder="Search emails by sender, subject, body..." aria-label="Search emails by sender, subject, or body" autocomplete="off">
                    </div>
                    <button class="btn-primary" id="btn-compose-email" data-testid="btn-compose-email" aria-label="Compose New Email"><i class="fa-solid fa-pen" aria-hidden="true"></i> Compose</button>
                </div>
            </div>
            <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin-top: 1rem;" aria-label="Admin Inbox List">
                ${rows.length > 0 ? rows : '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No emails match the search filter.</div>'}
            </div>
            <div id="email-reader-area" style="margin-top: 2rem; display: none; background: var(--card-bg); padding: 1.5rem; border: 1px solid var(--border); border-radius: var(--radius);" aria-label="Email Reader">
                <div style="display: flex; justify-content: space-between; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem;">
                    <div>
                        <h3 id="email-reader-subject" style="margin-bottom: 0.5rem;"></h3>
                        <div id="email-reader-from" style="font-size: 0.85rem; color: var(--text-muted);"></div>
                    </div>
                    <button class="btn-secondary" id="btn-reply-email" data-testid="btn-reply-email" aria-label="Reply to Email"><i class="fa-solid fa-reply" aria-hidden="true"></i> Reply</button>
                </div>
                <div id="email-reader-body" style="font-size: 0.95rem; line-height: 1.6; white-space: pre-wrap; margin-bottom: 2rem;"></div>
                
                <!-- Reply Editor -->
                <div id="email-reply-editor" style="display: none; border-top: 1px dashed var(--border); padding-top: 1.5rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-muted);"><i class="fa-solid fa-reply" aria-hidden="true"></i> Draft Reply</h4>
                    <label for="email-reply-textarea" style="display:none;">Draft Reply</label>
                    <textarea id="email-reply-textarea" data-testid="email-reply-textarea" aria-label="Draft Email Reply" style="width: 100%; height: 120px; padding: 1rem; border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 1rem; font-family: inherit;" placeholder="Type your reply here..."></textarea>
                    <div style="display: flex; justify-content: flex-end; gap: 1rem;">
                        <button class="btn-secondary" id="btn-cancel-reply" data-testid="btn-cancel-reply" aria-label="Cancel Reply">Cancel</button>
                        <button class="btn-primary" id="btn-send-reply" data-testid="btn-send-reply" aria-label="Send Email Reply"><i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Send Reply</button>
                    </div>
                </div>
            </div>
        `;
    }

    function renderDocuments() {
        const search = (window.currentDocSearchTerm || '').toLowerCase().trim();
        let filteredDocs = store.documents.filter(doc => {
            return !search ||
                (doc.id && doc.id.toLowerCase().includes(search)) ||
                (doc.name && doc.name.toLowerCase().includes(search)) ||
                (doc.type && doc.type.toLowerCase().includes(search)) ||
                (doc.relatedTo && doc.relatedTo.toLowerCase().includes(search));
        });

        let rows = filteredDocs.map(doc => `
            <tr data-testid="row-doc-${escapeHtml(doc.id)}" aria-label="${escapeHtml(doc.name)}">
                <td><strong>${escapeHtml(doc.id)}</strong></td>
                <td>${escapeHtml(doc.name)}</td>
                <td><span class="status-tag active">${escapeHtml(doc.type)}</span></td>
                <td>${escapeHtml(doc.relatedTo || 'General')}</td>
                <td><button class="btn-secondary btn-sm btn-view-doc" data-id="${escapeHtml(doc.id)}" data-testid="btn-view-doc-${escapeHtml(doc.id)}" aria-label="${escapeHtml(doc.name)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">View Document</button></td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Document Center (${filteredDocs.length} Total)</h2>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="doc-search" name="doc-search" class="inner-search-input" data-testid="doc-search-input" value="${escapeHtml(window.currentDocSearchTerm || '')}" placeholder="Search documents by name, type, related to..." aria-label="Search documents by name, type, or related to" autocomplete="off">
                    </div>
                    <button class="btn-primary" id="btn-upload-doc" data-testid="btn-upload-doc" aria-label="Upload or Create Document"><i class="fa-solid fa-upload" aria-hidden="true"></i> Upload / Create Document</button>
                </div>
            </div>
            <table class="data-table" aria-label="Document Center Table">
                <thead>
                    <tr>
                        <th scope="col">ID</th>
                        <th scope="col">Document Name</th>
                        <th scope="col">Type</th>
                        <th scope="col">Related To</th>
                        <th scope="col">Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.length > 0 ? rows : '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No documents match the search filter.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderDepartments() {
        const search = (window.currentDeptSearchTerm || '').toLowerCase().trim();
        const allDepts = ["Engineering", "HR", "Finance", "Marketing", "Product", "Operations", "Sales", "Customer Support"];
        const depts = allDepts.filter(d => !search || d.toLowerCase().includes(search));
        
        const cards = depts.map(d => {
            const empsInDept = store.employees.filter(e => (e.department || '').toLowerCase() === d.toLowerCase());
            const activeCount = empsInDept.filter(e => e.status === 'active').length;
            const manager = empsInDept.find(e => (e.role || '').toLowerCase().includes('lead') || (e.role || '').toLowerCase().includes('director') || (e.role || '').toLowerCase().includes('manager')) || empsInDept[0];
            const deptKey = d.toLowerCase().replace(/\s+/g, '-');
            
            return `
                <div class="stat-card" data-testid="dept-card-${escapeHtml(deptKey)}" aria-label="${escapeHtml(d)} Department" style="display: flex; flex-direction: column; justify-content: space-between; min-height: 180px;">
                    <div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <h3 style="font-size: 1.1rem; color: var(--text-main); font-weight: 700;">${escapeHtml(d)}</h3>
                            <span class="badge ${activeCount > 0 ? 'success' : 'warning'}">${activeCount} Active</span>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                            Lead: <strong>${escapeHtml(manager ? manager.name : 'Unassigned')}</strong>
                        </p>
                    </div>
                    <div style="border-top: 1px solid var(--border); padding-top: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 0.8rem; color: var(--text-muted);">Total Team: ${empsInDept.length}</span>
                        <button class="btn-secondary btn-sm btn-filter-dept" data-dept="${escapeHtml(d)}" data-testid="btn-dept-${escapeHtml(deptKey)}" aria-label="View Members of ${escapeHtml(d)} Department" style="font-size: 0.75rem; padding: 0.2rem 0.5rem;">View Members</button>
                    </div>
                </div>
            `;
        }).join('');

        return `
            <div class="card-header">
                <h2>Company Departments</h2>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <div class="inner-search-box">
                        <i class="fa-solid fa-magnifying-glass" aria-hidden="true"></i>
                        <input type="text" id="dept-search" name="dept-search" class="inner-search-input" data-testid="dept-search-input" value="${escapeHtml(window.currentDeptSearchTerm || '')}" placeholder="Search departments..." aria-label="Search departments" autocomplete="off">
                    </div>
                    <span class="badge primary">${depts.length} Total Departments</span>
                </div>
            </div>
            <div class="dashboard-grid" style="margin-top: 1.5rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));" aria-label="Company Departments Grid">
                ${cards.length > 0 ? cards : '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">No departments match the search filter.</div>'}
            </div>
        `;
    }

    function renderApprovals() {
        const pendingLeaves = store.leaves.filter(l => l.status === 'pending');
        const pendingExpenses = store.expenses.filter(e => e.status === 'pending');

        const leaveRows = pendingLeaves.map(l => {
            const lName = l.name || l.employee || l.id;
            return `
            <tr data-testid="row-approval-leave-${escapeHtml(l.id)}" aria-label="${escapeHtml(lName)}">
                <td><strong>${escapeHtml(l.id)}</strong></td>
                <td><span class="badge warning">Leave Request</span></td>
                <td>${escapeHtml(l.employee)}</td>
                <td>${escapeHtml(l.startDate || l.dates)} (${escapeHtml(l.leaveType || l.type)})</td>
                <td><span class="status-tag pending">PENDING</span></td>
                <td>
                    <button class="btn-primary btn-sm btn-approve-leave-direct" data-id="${escapeHtml(l.id)}" data-testid="btn-approve-leave-${escapeHtml(l.id)}" aria-label="${escapeHtml(lName)}" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Approve</button>
                    <button class="btn-secondary btn-sm btn-reject-leave-direct" data-id="${escapeHtml(l.id)}" data-testid="btn-reject-leave-${escapeHtml(l.id)}" aria-label="${escapeHtml(lName)}" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Reject</button>
                </td>
            </tr>
        `;}).join('');

        const expenseRows = pendingExpenses.map(e => {
            const eName = e.name || e.employee || e.id;
            return `
            <tr data-testid="row-approval-exp-${escapeHtml(e.id)}" aria-label="${escapeHtml(eName)}">
                <td><strong>${escapeHtml(e.id)}</strong></td>
                <td><span class="badge warning">Expense Claim</span></td>
                <td>${escapeHtml(e.employee)}</td>
                <td>${escapeHtml(e.category)} - <strong>${escapeHtml(e.amount)}</strong></td>
                <td><span class="status-tag pending">PENDING</span></td>
                <td>
                    <button class="btn-primary btn-sm btn-approve-exp-direct" data-id="${escapeHtml(e.id)}" data-testid="btn-approve-exp-${escapeHtml(e.id)}" aria-label="${escapeHtml(eName)}" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Approve</button>
                    <button class="btn-secondary btn-sm btn-reject-exp-direct" data-id="${escapeHtml(e.id)}" data-testid="btn-reject-exp-${escapeHtml(e.id)}" aria-label="${escapeHtml(eName)}" style="padding: 0.25rem 0.6rem; font-size: 0.75rem;">Reject</button>
                </td>
            </tr>
        `;}).join('');

        return `
            <div class="card-header">
                <h2>Central Approval Center</h2>
                <span class="badge warning">${pendingLeaves.length + pendingExpenses.length} Pending Actions</span>
            </div>
            <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1.5rem;">
                Review and authorize operations before database mutation. High-risk actions require explicit verification.
            </p>
            <table class="data-table" aria-label="Central Approval Center Table">
                <thead>
                    <tr>
                        <th scope="col">ID</th>
                        <th scope="col">Type</th>
                        <th scope="col">Requester</th>
                        <th scope="col">Details</th>
                        <th scope="col">Status</th>
                        <th scope="col">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${(leaveRows || expenseRows) ? (leaveRows + expenseRows) : '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No pending approvals at this time.</td></tr>'}
                </tbody>
            </table>
        `;
    }

    function renderReports() {
        const totalEmployees = store.employees.length;
        const activeEmployees = store.employees.filter(e => e.status === 'active').length;
        const totalExpensesCount = store.expenses.length;
        const approvedExpenses = store.expenses.filter(e => e.status === 'approved');
        
        let totalExpenseSum = 0;
        approvedExpenses.forEach(e => {
            totalExpenseSum += parseAmount(e.amount);
        });

        return `
            <div class="card-header">
                <h2>Reports & Real-Time Analytics</h2>
                <button class="btn-primary" id="btn-export-audit" data-testid="btn-export-audit" aria-label="Export Compliance Audit Log"><i class="fa-solid fa-download" aria-hidden="true"></i> Export Audit Log</button>
            </div>
            <div class="dashboard-grid" style="margin-top: 1.5rem;">
                <div class="stat-card">
                    <div class="stat-title">Active Headcount Ratio</div>
                    <div class="stat-value">${activeEmployees} / ${totalEmployees}</div>
                    <div class="stat-change positive"><i class="fa-solid fa-check" aria-hidden="true"></i> ${Math.round((activeEmployees/totalEmployees)*100 || 100)}% Operational</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Total Approved Claims</div>
                    <div class="stat-value">₹${totalExpenseSum.toLocaleString()}</div>
                    <div class="stat-change positive"><i class="fa-solid fa-file-invoice" aria-hidden="true"></i> ${approvedExpenses.length} Claims Approved</div>
                </div>
                <div class="stat-card">
                    <div class="stat-title">Pending Tasks</div>
                    <div class="stat-value">${store.tasks.filter(t => t.status === 'pending').length}</div>
                    <div class="stat-change warning"><i class="fa-solid fa-clock" aria-hidden="true"></i> Action Required</div>
                </div>
            </div>
            <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; margin-top: 1.5rem;">
                <h3>Department Staffing Breakdown</h3>
                <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 0.75rem;">
                    ${["Engineering", "HR", "Product", "Operations", "Marketing", "Finance", "Sales", "Customer Support"].map(dept => {
                        const cnt = store.employees.filter(e => (e.department || '').toLowerCase() === dept.toLowerCase() && e.status === 'active').length;
                        const pct = Math.round((cnt / (activeEmployees || 1)) * 100);
                        return `
                            <div>
                                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.25rem;">
                                    <span>${dept}</span>
                                    <strong>${cnt} employees (${pct}%)</strong>
                                </div>
                                <div style="width: 100%; height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden;">
                                    <div style="width: ${pct}%; height: 100%; background: var(--primary); border-radius: 4px;"></div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    function renderSettings() {
        return `
            <div class="card-header">
                <h2>Settings & Chaos Mode Simulator</h2>
                <span class="badge primary">Configuration</span>
            </div>
            <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.5rem; margin-top: 1.5rem; max-width: 650px;">
                <h3 style="margin-bottom: 1rem;"><i class="fa-solid fa-bolt text-warning" aria-hidden="true"></i> Edge Case & Recovery Testing Controls</h3>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.5rem;">
                    Toggle simulated network latencies, session expirations, and validation traps to test the AI Agent's autonomous recovery layer.
                </p>
                <div class="form-group">
                    <label for="chaos-enable" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="chaos-enable" data-testid="chaos-enable-checkbox" aria-label="Enable Chaos Simulator" style="width: 18px; height: 18px;">
                        <strong>Enable Chaos / Edge Case Simulation Mode</strong>
                    </label>
                </div>
                <div class="form-group">
                    <label class="form-label" for="chaos-delay">Simulated Network Delay (Milliseconds)</label>
                    <input type="number" id="chaos-delay" data-testid="chaos-delay-input" aria-label="Simulated Network Delay in Milliseconds" class="form-control" value="0" placeholder="e.g. 1500">
                </div>
                <div class="form-group">
                    <label for="chaos-session-expire" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="chaos-session-expire" data-testid="chaos-session-expire-checkbox" aria-label="Simulate Session Expiration" style="width: 18px; height: 18px;">
                        <span>Simulate 401 Session Expiration on next mutation</span>
                    </label>
                </div>
                <div class="form-group">
                    <label for="chaos-stale-dom" style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                        <input type="checkbox" id="chaos-stale-dom" data-testid="chaos-stale-dom-checkbox" aria-label="Simulate Stale DOM" style="width: 18px; height: 18px;">
                        <span>Simulate Stale DOM elements (delayed re-render)</span>
                    </label>
                </div>
                <button class="btn-primary" id="btn-save-chaos-settings" data-testid="btn-save-chaos-settings" aria-label="Save Simulator Config" style="margin-top: 1rem;"><i class="fa-solid fa-save" aria-hidden="true"></i> Save Simulator Config</button>
            </div>
        `;
    }

    // ==========================================
    // --- Event Attachments & Handlers ---
    // ==========================================

    function attachEventListeners(viewName) {
        if (viewName === 'dashboard') {
            document.getElementById('btn-generate-report')?.addEventListener('click', () => {
                showToast("Overview summary report generated from SQLite records.");
            });
        }

        if (viewName === 'employees') {
            document.querySelectorAll('.employee-row').forEach(row => {
                row.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-emp-id');
                    if (id) {
                        window.currentEmpId = id;
                        switchView('employee_profile', id);
                    }
                });
            });

            document.querySelectorAll('.btn-view-emp').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const id = e.currentTarget.getAttribute('data-id');
                    if (id) {
                        window.currentEmpId = id;
                        switchView('employee_profile', id);
                    }
                });
            });

            const searchInput = document.getElementById('emp-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    window.currentSearchTerm = e.target.value.toLowerCase().trim();
                    const tbody = document.querySelector('.data-table tbody');
                    if (tbody) {
                        const filtered = window.currentSearchTerm ? 
                            store.employees.filter(emp => 
                                (emp.name && emp.name.toLowerCase().includes(window.currentSearchTerm)) || 
                                (emp.id && emp.id.toLowerCase().includes(window.currentSearchTerm)) ||
                                (emp.department && emp.department.toLowerCase().includes(window.currentSearchTerm)) ||
                                (emp.role && emp.role.toLowerCase().includes(window.currentSearchTerm)) ||
                                (emp.email && emp.email.toLowerCase().includes(window.currentSearchTerm))
                            ) : store.employees;
                        
                        if (filtered.length > 0) {
                            tbody.innerHTML = filtered.map(emp => `
                                <tr data-emp-id="${escapeHtml(emp.id)}" data-testid="row-emp-${escapeHtml(emp.id)}" class="employee-row" style="cursor: pointer;" aria-label="${escapeHtml(emp.name)}">
                                    <td><strong>${escapeHtml(emp.name)}</strong><br><small style="color: #6b7280">${escapeHtml(emp.email)}</small></td>
                                    <td><strong>${escapeHtml(emp.id)}</strong></td>
                                    <td>${escapeHtml(emp.department)}</td>
                                    <td>${escapeHtml(emp.role)}</td>
                                    <td><span class="status-tag ${emp.status === 'active' ? 'active' : 'pending'}">${escapeHtml((emp.status || '').replace('_', ' ').toUpperCase())}</span></td>
                                    <td>
                                        <button class="icon-btn btn-view-emp" data-id="${escapeHtml(emp.id)}" data-testid="btn-view-emp-${escapeHtml(emp.id)}" aria-label="${escapeHtml(emp.name)}" title="View Profile for ${escapeHtml(emp.name)}"><i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>
                                    </td>
                                </tr>
                            `).join('');
                            
                            // Re-bind row click handlers
                            tbody.querySelectorAll('.employee-row').forEach(row => {
                                row.addEventListener('click', (ev) => {
                                    const id = ev.currentTarget.getAttribute('data-emp-id');
                                    if (id) {
                                        window.currentEmpId = id;
                                        switchView('employee_profile', id);
                                    }
                                });
                            });
                            tbody.querySelectorAll('.btn-view-emp').forEach(btn => {
                                btn.addEventListener('click', (ev) => {
                                    ev.stopPropagation();
                                    const id = ev.currentTarget.getAttribute('data-id');
                                    if (id) {
                                        window.currentEmpId = id;
                                        switchView('employee_profile', id);
                                    }
                                });
                            });
                        } else {
                            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No employees match the search filter.</td></tr>';
                        }
                    }
                });
            }

            document.getElementById('btn-add-employee')?.addEventListener('click', () => {
                openGenericModal("Add New Employee", `
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-name" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Full Name</label>
                        <input type="text" id="new-emp-name" name="new-emp-name" data-testid="modal-emp-name" aria-label="Full Name" placeholder="Full Name (e.g. Sarah Connor)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-email" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Email Address</label>
                        <input type="email" id="new-emp-email" name="new-emp-email" data-testid="modal-emp-email" aria-label="Email Address" placeholder="Email (e.g. sarah@workhub.local)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-role" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Role</label>
                        <input type="text" id="new-emp-role" name="new-emp-role" data-testid="modal-emp-role" aria-label="Role" placeholder="Role (e.g. Senior Software Engineer)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-dept" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Department</label>
                        <select id="new-emp-dept" name="new-emp-dept" data-testid="modal-emp-dept" aria-label="Department" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="Engineering">Engineering</option>
                            <option value="HR">HR</option>
                            <option value="Finance">Finance</option>
                            <option value="Marketing">Marketing</option>
                            <option value="Sales">Sales</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-salary" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Salary</label>
                        <input type="number" id="new-emp-salary" name="new-emp-salary" data-testid="modal-emp-salary" aria-label="Salary" placeholder="Annual Salary (e.g. 145000)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-phone" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Phone Number</label>
                        <input type="text" id="new-emp-phone" name="new-emp-phone" data-testid="modal-emp-phone" aria-label="Phone Number" placeholder="Phone Number" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-emp-contact" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Emergency Contact</label>
                        <input type="text" id="new-emp-contact" name="new-emp-contact" data-testid="modal-emp-contact" aria-label="Emergency Contact" placeholder="Emergency Contact" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                `, "Create Employee", async () => {
                    const name = document.getElementById('new-emp-name')?.value?.trim();
                    const email = document.getElementById('new-emp-email')?.value?.trim();
                    const role = document.getElementById('new-emp-role')?.value?.trim() || 'Staff';
                    const dept = document.getElementById('new-emp-dept')?.value || 'Engineering';
                    const salary = parseInt(document.getElementById('new-emp-salary')?.value || '0', 10);
                    const phone = document.getElementById('new-emp-phone')?.value?.trim() || '555-0100';
                    const emergencyContact = document.getElementById('new-emp-contact')?.value?.trim() || 'HR Department';

                    if (name && email) {
                        const newEmp = {
                            name,
                            department: dept,
                            role,
                            salary: salary || undefined,
                            status: "active",
                            email,
                            joined: new Date().toISOString().split('T')[0],
                            emergencyContact,
                            phone,
                            manager: "Admin"
                        };

                        try {
                            const res = await fetch(`${API_BASE}/employees/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newEmp)
                            });
                            if (res.ok) {
                                const created = await res.json();
                                showToast(`Employee "${created.name || name}" added to SQLite database.`);
                            }
                        } catch (e) {
                            showToast(`Failed to add employee: ${e}`);
                        }
                        await fetchStore();
                        switchView('employees');
                    }
                });
            });
        }

        if (viewName === 'employee_profile') {
            document.getElementById('btn-back-employees')?.addEventListener('click', (e) => {
                e.preventDefault();
                switchView('employees');
            });

            document.getElementById('btn-save-emp')?.addEventListener('click', async (e) => {
                e.preventDefault();
                const empId = window.currentEmpId;
                if (!empId) {
                    showToast("No employee ID selected to save.");
                    return;
                }

                const role = document.getElementById('emp-role')?.value;
                const phone = document.getElementById('emp-phone')?.value;
                const emergencyContact = document.getElementById('emp-emergency-contact')?.value;
                const dept = document.getElementById('emp-dept')?.value;
                const status = document.getElementById('emp-status')?.value;
                
                const updatePayload = { role, phone, emergencyContact, department: dept, status };
                
                try {
                    const res = await fetch(`${API_BASE}/employees/${empId}`, {
                        method: 'PATCH',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updatePayload)
                    });
                    if (res.ok) {
                        showToast(`Employee ${empId} saved to SQLite database successfully!`);
                    } else {
                        const err = await res.json();
                        showToast(`Update error: ${err.detail || 'Failed to update'}`);
                    }
                } catch (e) {
                    showToast(`Network error updating employee: ${e}`);
                }
                await fetchStore();
                switchView('employee_profile', empId);
            });
        }

        if (viewName === 'expenses') {
            document.querySelectorAll('.btn-review-expense').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    openExpenseApproval(id);
                });
            });

            const expSearchInput = document.getElementById('exp-search');
            if (expSearchInput) {
                expSearchInput.addEventListener('input', (e) => {
                    window.currentExpenseSearchTerm = e.target.value.toLowerCase().trim();
                    const tbody = document.querySelector('.data-table tbody');
                    if (tbody) {
                        const filterVal = window.expenseFilter || 'all';
                        const search = window.currentExpenseSearchTerm;
                        const filtered = store.expenses.filter(exp => {
                            const matchesStatus = (filterVal === 'all' || exp.status === filterVal);
                            const matchesSearch = !search ||
                                (exp.id && exp.id.toLowerCase().includes(search)) ||
                                (exp.employee && exp.employee.toLowerCase().includes(search)) ||
                                (exp.category && exp.category.toLowerCase().includes(search)) ||
                                (exp.amount && String(exp.amount).toLowerCase().includes(search)) ||
                                (exp.date && exp.date.toLowerCase().includes(search));
                            return matchesStatus && matchesSearch;
                        });

                        if (filtered.length > 0) {
                            tbody.innerHTML = filtered.map(exp => {
                                const expName = exp.name || exp.employee || exp.id;
                                return `
                                <tr data-testid="row-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(expName)}">
                                    <td><strong>${escapeHtml(exp.id)}</strong></td>
                                    <td>${escapeHtml(exp.employee)}</td>
                                    <td>${escapeHtml(exp.category)}</td>
                                    <td><strong>${escapeHtml(exp.amount)}</strong></td>
                                    <td>${escapeHtml(exp.date)}</td>
                                    <td><span class="status-tag ${exp.status}" id="status-${escapeHtml(exp.id)}">${escapeHtml((exp.status || '').toUpperCase())}</span></td>
                                    <td>
                                        ${exp.status === 'pending' ? 
                                            `<button class="btn-primary btn-sm btn-review-expense" id="review-${escapeHtml(exp.id)}" data-id="${escapeHtml(exp.id)}" data-testid="btn-review-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(expName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Review</button>` : 
                                            `<button class="btn-secondary btn-sm" disabled data-testid="btn-processed-exp-${escapeHtml(exp.id)}" aria-label="${escapeHtml(expName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Processed</button>`
                                        }
                                    </td>
                                </tr>
                            `;}).join('');

                            tbody.querySelectorAll('.btn-review-expense').forEach(btn => {
                                btn.addEventListener('click', (ev) => {
                                    const id = ev.currentTarget.getAttribute('data-id');
                                    openExpenseApproval(id);
                                });
                            });
                        } else {
                            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No expenses match the search filter.</td></tr>';
                        }
                    }
                });
            }

            document.getElementById('btn-filter-expenses')?.addEventListener('click', () => {
                openGenericModal("Filter Expenses", `
                    <div style="margin-bottom: 1rem;">
                        <label for="expense-status-filter" style="display: block; margin-bottom: 0.5rem; font-size: 0.85rem;">Status Filter</label>
                        <select id="expense-status-filter" data-testid="modal-expense-filter" aria-label="Filter Expenses by Status" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="all" ${window.expenseFilter === 'all' ? 'selected' : ''}>All</option>
                            <option value="pending" ${window.expenseFilter === 'pending' ? 'selected' : ''}>Pending</option>
                            <option value="approved" ${window.expenseFilter === 'approved' ? 'selected' : ''}>Approved</option>
                            <option value="rejected" ${window.expenseFilter === 'rejected' ? 'selected' : ''}>Rejected</option>
                        </select>
                    </div>
                `, "Apply Filter", () => {
                    window.expenseFilter = document.getElementById('expense-status-filter').value;
                    switchView('expenses');
                });
            });

            document.getElementById('btn-add-expense')?.addEventListener('click', () => {
                openGenericModal("Add New Expense", `
                    <div class="form-group">
                        <label class="form-label" for="new-exp-emp">Employee</label>
                        <select id="new-exp-emp" name="new-exp-emp" data-testid="modal-exp-emp" aria-label="Employee" class="form-control">
                            ${getEmployeeOptionsHtml()}
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-exp-cat">Category</label>
                        <select id="new-exp-cat" name="new-exp-cat" data-testid="modal-exp-cat" aria-label="Category" class="form-control">
                            <option value="Travel">Travel</option>
                            <option value="Software">Software & Cloud</option>
                            <option value="Equipment & Hardware">Equipment & Hardware</option>
                            <option value="Office Supplies">Office Supplies</option>
                            <option value="Internet">Internet & Mobile</option>
                            <option value="Meals">Meals & Client Entertainment</option>
                            <option value="General">General / Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-exp-amt">Amount</label>
                        <input type="text" id="new-exp-amt" name="new-exp-amt" data-testid="modal-exp-amt" aria-label="Amount" class="form-control" placeholder="e.g. 3250">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-exp-desc">Title</label>
                        <input type="text" id="new-exp-desc" name="new-exp-desc" data-testid="modal-exp-desc" aria-label="Title" class="form-control" placeholder="Expense description / title">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-exp-date">Date</label>
                        <input type="date" id="new-exp-date" name="new-exp-date" data-testid="modal-exp-date" aria-label="Date" class="form-control">
                    </div>
                `, "Submit Expense", async () => {
                    const emp = document.getElementById('new-exp-emp')?.value?.trim() || 'Admin';
                    const cat = document.getElementById('new-exp-cat')?.value?.trim() || 'General';
                    const amt = document.getElementById('new-exp-amt')?.value?.trim() || '₹0';
                    const desc = document.getElementById('new-exp-desc')?.value?.trim() || 'General Expense';
                    const expDate = document.getElementById('new-exp-date')?.value || new Date().toISOString().split('T')[0];

                    if (emp) {
                        const newExp = {
                            employee: emp,
                            category: cat,
                            amount: amt.startsWith('₹') ? amt : `₹${amt}`,
                            description: desc,
                            date: expDate,
                            status: "pending",
                            receiptId: "REC-" + Math.floor(1000 + Math.random() * 9000)
                        };

                        try {
                            const res = await fetch(`${API_BASE}/expenses/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newExp)
                            });
                            if (res.ok) {
                                showToast(`Expense for ${emp} successfully saved in SQLite database!`);
                            }
                        } catch (e) {
                            showToast(`Failed to add expense: ${e}`);
                        }
                        await fetchStore();
                        switchView('expenses');
                    }
                });
            });
        }

        if (viewName === 'leaves') {
            document.querySelectorAll('.btn-action-leave').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    const action = e.currentTarget.getAttribute('data-action');
                    const newStatus = (action === 'approve') ? 'approved' : 'rejected';

                    try {
                        const res = await fetch(`${API_BASE}/leaves/${id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: newStatus })
                        });
                        if (res.ok) {
                            showToast(`Leave ${id} successfully ${action}d in SQLite database.`);
                        } else {
                            showToast(`Error updating leave ${id}.`);
                        }
                    } catch (e) {
                        showToast(`Network error: ${e}`);
                    }
                    await fetchStore();
                    switchView('leaves');
                });
            });

            const leaveSearchInput = document.getElementById('leave-search');
            if (leaveSearchInput) {
                leaveSearchInput.addEventListener('input', (e) => {
                    window.currentLeaveSearchTerm = e.target.value.toLowerCase().trim();
                    const tbody = document.querySelector('.data-table tbody');
                    if (tbody) {
                        const search = window.currentLeaveSearchTerm;
                        const filtered = store.leaves.filter(lv => {
                            return !search ||
                                (lv.id && lv.id.toLowerCase().includes(search)) ||
                                (lv.employee && lv.employee.toLowerCase().includes(search)) ||
                                (lv.type && lv.type.toLowerCase().includes(search)) ||
                                (lv.dates && lv.dates.toLowerCase().includes(search)) ||
                                (lv.status && lv.status.toLowerCase().includes(search));
                        });

                        if (filtered.length > 0) {
                            tbody.innerHTML = filtered.map(lv => {
                                const lvName = lv.name || lv.employee || lv.id;
                                return `
                                <tr data-testid="row-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}">
                                    <td><strong>${escapeHtml(lv.id)}</strong></td>
                                    <td>${escapeHtml(lv.employee)}</td>
                                    <td>${escapeHtml(lv.type)}</td>
                                    <td>${escapeHtml(lv.dates)}</td>
                                    <td><span class="status-tag ${lv.status}">${escapeHtml((lv.status || '').toUpperCase())}</span></td>
                                    <td>
                                        ${lv.status === 'pending' ? 
                                            `<button class="btn-primary btn-sm btn-action-leave" data-id="${escapeHtml(lv.id)}" data-action="approve" data-testid="btn-approve-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem; margin-right: 0.25rem;">Approve</button>
                                             <button class="btn-secondary btn-sm btn-action-leave" data-id="${escapeHtml(lv.id)}" data-action="reject" data-testid="btn-reject-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Reject</button>` : 
                                            `<button class="btn-secondary btn-sm" disabled data-testid="btn-processed-leave-${escapeHtml(lv.id)}" aria-label="${escapeHtml(lvName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Processed</button>`
                                        }
                                    </td>
                                </tr>
                            `;}).join('');

                            tbody.querySelectorAll('.btn-action-leave').forEach(btn => {
                                btn.addEventListener('click', async (ev) => {
                                    const id = ev.currentTarget.getAttribute('data-id');
                                    const action = ev.currentTarget.getAttribute('data-action');
                                    const newStatus = (action === 'approve') ? 'approved' : 'rejected';

                                    try {
                                        const res = await fetch(`${API_BASE}/leaves/${id}`, {
                                            method: 'PATCH',
                                            headers: { 'Content-Type': 'application/json' },
                                            body: JSON.stringify({ status: newStatus })
                                        });
                                        if (res.ok) {
                                            showToast(`Leave ${id} successfully ${action}d in SQLite database.`);
                                        } else {
                                            showToast(`Error updating leave ${id}.`);
                                        }
                                    } catch (err) {
                                        showToast(`Network error: ${err}`);
                                    }
                                    await fetchStore();
                                    switchView('leaves');
                                });
                            });
                        } else {
                            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 2rem;">No leave requests match the search filter.</td></tr>';
                        }
                    }
                });
            }

            document.getElementById('btn-add-leave')?.addEventListener('click', () => {
                openGenericModal("Request Leave", `
                    <div class="form-group">
                        <label class="form-label" for="new-lv-emp">Select Employee</label>
                        <select id="new-lv-emp" name="new-lv-emp" data-testid="modal-lv-emp" aria-label="Select Employee for Leave" class="form-control">
                            ${getEmployeeOptionsHtml()}
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-lv-type">Leave Type</label>
                        <select id="new-lv-type" name="new-lv-type" data-testid="modal-lv-type" aria-label="Leave Type" class="form-control">
                            <option value="Annual Leave">Annual Leave</option>
                            <option value="Sick Leave">Sick Leave</option>
                            <option value="PTO">PTO</option>
                            <option value="Parental Leave">Parental Leave</option>
                            <option value="Casual Leave">Casual Leave</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-lv-dates">Leave Dates</label>
                        <input type="text" id="new-lv-dates" name="new-lv-dates" data-testid="modal-lv-dates" aria-label="Leave Dates" class="form-control" placeholder="e.g. Nov 10 - Nov 15">
                    </div>
                `, "Submit Leave Request", async () => {
                    const emp = document.getElementById('new-lv-emp')?.value?.trim();
                    const type = document.getElementById('new-lv-type')?.value || 'Annual Leave';
                    const dates = document.getElementById('new-lv-dates')?.value?.trim() || 'Upcoming';

                    if (emp) {
                        const newLv = {
                            employee: emp,
                            type: type,
                            dates: dates,
                            status: "pending"
                        };
                        try {
                            const res = await fetch(`${API_BASE}/leaves/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newLv)
                            });
                            if (res.ok) {
                                showToast(`Leave request for ${emp} created in SQLite database!`);
                            }
                        } catch (e) {
                            showToast(`Failed to submit leave: ${e}`);
                        }
                        await fetchStore();
                        switchView('leaves');
                    }
                });
            });

            document.getElementById('btn-view-calendar')?.addEventListener('click', () => {
                const upcomingLeaves = store.leaves.filter(l => l.status === 'approved').map(l => `
                    <div style="padding: 0.5rem; border-bottom: 1px solid var(--border);">
                        <strong>${escapeHtml(l.employee)}</strong> - ${escapeHtml(l.type)} (${escapeHtml(l.dates)})
                    </div>
                `).join('');

                openGenericModal("Upcoming Approved Leave Calendar", `
                    <div style="max-height: 250px; overflow-y: auto; background: var(--bg-alt); padding: 0.5rem; border-radius: 4px;" aria-label="Approved Leaves List">
                        ${upcomingLeaves || '<p style="color: var(--text-muted); padding: 0.5rem;">No upcoming approved leaves in database.</p>'}
                    </div>
                `, "Close");
            });
        }

        if (viewName === 'benefits') {
            document.querySelectorAll('.btn-manage-benefit').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    const ben = store.benefits.find(b => b.id === id);
                    if (ben) {
                        openGenericModal(`Manage Benefit: ${escapeHtml(ben.name)}`, `
                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">Update coverage details or active status in SQLite database.</p>
                            <div style="margin-bottom: 1rem;">
                                <label for="edit-ben-cov" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Coverage</label>
                                <input type="text" id="edit-ben-cov" data-testid="modal-ben-cov" aria-label="Benefit Coverage Details" value="${escapeHtml(ben.coverage)}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            </div>
                            <div style="margin-bottom: 1rem;">
                                <label for="edit-ben-status" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Status</label>
                                <select id="edit-ben-status" data-testid="modal-ben-status" aria-label="Benefit Active Status" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                                    <option value="active" ${ben.status === 'active' ? 'selected' : ''}>Active</option>
                                    <option value="inactive" ${ben.status === 'inactive' ? 'selected' : ''}>Inactive</option>
                                </select>
                            </div>
                        `, "Save Changes", async () => {
                            const cov = document.getElementById('edit-ben-cov')?.value;
                            const st = document.getElementById('edit-ben-status')?.value;
                            try {
                                const res = await fetch(`${API_BASE}/benefits/${id}`, {
                                    method: 'PATCH',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ coverage: cov, status: st })
                                });
                                if (res.ok) {
                                    showToast(`Benefit ${ben.name} updated in SQLite database.`);
                                }
                            } catch (e) {
                                showToast(`Error updating benefit: ${e}`);
                            }
                            await fetchStore();
                            switchView('benefits');
                        });
                    }
                });
            });

            document.getElementById('btn-add-benefit')?.addEventListener('click', () => {
                openGenericModal("Add New Benefit", `
                    <div style="margin-bottom: 1rem;">
                        <label for="new-ben-name" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Benefit Name</label>
                        <input type="text" id="new-ben-name" data-testid="modal-ben-name" aria-label="Benefit Name" placeholder="Benefit Name (e.g. Dental Care)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-ben-prov" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Provider</label>
                        <input type="text" id="new-ben-prov" data-testid="modal-ben-prov" aria-label="Benefit Provider" placeholder="Provider Name (e.g. MetLife)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-ben-cov" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Coverage</label>
                        <input type="text" id="new-ben-cov" data-testid="modal-ben-cov" aria-label="Coverage Details" placeholder="Coverage Details (e.g. 80% Coverage)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                `, "Create Benefit", async () => {
                    const name = document.getElementById('new-ben-name')?.value?.trim();
                    const prov = document.getElementById('new-ben-prov')?.value?.trim();
                    const cov = document.getElementById('new-ben-cov')?.value?.trim();
                    if (name && prov) {
                        const newBen = {
                            name: name,
                            provider: prov,
                            coverage: cov || "Standard",
                            enrolled: 0,
                            status: "active"
                        };
                        try {
                            const res = await fetch(`${API_BASE}/benefits/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newBen)
                            });
                            if (res.ok) {
                                showToast(`Benefit "${name}" added to SQLite database.`);
                            }
                        } catch (e) {
                            showToast(`Failed to add benefit: ${e}`);
                        }
                        await fetchStore();
                        switchView('benefits');
                    }
                });
            });
        }

        if (viewName === 'tasks') {
            document.querySelectorAll('.btn-open-task').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    const tsk = store.tasks.find(t => t.id === id);
                    if (tsk) {
                        openTaskModal(tsk);
                    }
                });
            });

            const taskSearchInput = document.getElementById('task-search');
            if (taskSearchInput) {
                taskSearchInput.addEventListener('input', (e) => {
                    window.currentTaskSearchTerm = e.target.value.toLowerCase().trim();
                    const tbody = document.querySelector('.data-table tbody');
                    if (tbody) {
                        const search = window.currentTaskSearchTerm;
                        const filtered = store.tasks.filter(tsk => {
                            return !search ||
                                (tsk.id && tsk.id.toLowerCase().includes(search)) ||
                                (tsk.title && tsk.title.toLowerCase().includes(search)) ||
                                (tsk.assignedTo && tsk.assignedTo.toLowerCase().includes(search)) ||
                                (tsk.priority && tsk.priority.toLowerCase().includes(search)) ||
                                (tsk.status && tsk.status.toLowerCase().includes(search));
                        });

                        if (filtered.length > 0) {
                            tbody.innerHTML = filtered.map(tsk => {
                                const taskName = tsk.name || tsk.title || tsk.id;
                                return `
                                <tr data-testid="row-task-${escapeHtml(tsk.id)}" aria-label="${escapeHtml(taskName)}">
                                    <td><strong>${escapeHtml(tsk.id)}</strong></td>
                                    <td>${escapeHtml(tsk.title)}</td>
                                    <td>${escapeHtml(tsk.assignedTo)}</td>
                                    <td>${escapeHtml(tsk.dueDate)}</td>
                                    <td><span class="status-tag pending">${escapeHtml((tsk.priority || '').toUpperCase())}</span></td>
                                    <td><span class="status-tag ${tsk.status === 'pending' ? 'pending' : (tsk.status === 'completed' ? 'active' : 'approved')}">${escapeHtml((tsk.status || '').replace('_', ' ').toUpperCase())}</span></td>
                                    <td>
                                        <button class="btn-secondary btn-sm btn-open-task" data-id="${escapeHtml(tsk.id)}" data-testid="btn-open-task-${escapeHtml(tsk.id)}" aria-label="${escapeHtml(taskName)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Open Task</button>
                                    </td>
                                </tr>
                            `;}).join('');

                            tbody.querySelectorAll('.btn-open-task').forEach(btn => {
                                btn.addEventListener('click', (ev) => {
                                    const id = ev.currentTarget.getAttribute('data-id');
                                    const tsk = store.tasks.find(t => t.id === id);
                                    if (tsk) {
                                        openTaskModal(tsk);
                                    }
                                });
                            });
                        } else {
                            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">No tasks match the search filter.</td></tr>';
                        }
                    }
                });
            }

            document.getElementById('btn-new-task')?.addEventListener('click', () => {
                openGenericModal("Create New HR Task", `
                    <div class="form-group">
                        <label class="form-label" for="new-tsk-title">Title</label>
                        <input type="text" id="new-tsk-title" name="new-tsk-title" data-testid="modal-tsk-title" aria-label="Title" class="form-control" placeholder="e.g. Review Probation for Alice">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-tsk-assign">Assignee</label>
                        <select id="new-tsk-assign" name="new-tsk-assign" data-testid="modal-tsk-assign" aria-label="Assignee" class="form-control">
                            ${getEmployeeOptionsHtml()}
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-tsk-date">Due Date</label>
                        <input type="date" id="new-tsk-date" name="new-tsk-date" data-testid="modal-tsk-date" aria-label="Due Date" class="form-control">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-tsk-priority">Priority</label>
                        <select id="new-tsk-priority" name="new-tsk-priority" data-testid="modal-tsk-priority" aria-label="Priority" class="form-control">
                            <option value="medium">Medium Priority</option>
                            <option value="high">High Priority</option>
                            <option value="low">Low Priority</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-tsk-desc">Description</label>
                        <textarea id="new-tsk-desc" name="new-tsk-desc" data-testid="modal-tsk-desc" aria-label="Description" class="form-control" placeholder="Task description and details..." style="height: 80px;"></textarea>
                    </div>
                `, "Assign Task", async () => {
                    const title = document.getElementById('new-tsk-title')?.value?.trim();
                    const assign = document.getElementById('new-tsk-assign')?.value?.trim() || 'Admin';
                    const date = document.getElementById('new-tsk-date')?.value || new Date().toISOString().split('T')[0];
                    const priority = document.getElementById('new-tsk-priority')?.value || 'medium';
                    const description = document.getElementById('new-tsk-desc')?.value?.trim() || '';

                    if (title) {
                        const newTsk = {
                            title: title,
                            assignedTo: assign,
                            dueDate: date,
                            priority: priority,
                            description: description,
                            status: "pending"
                        };
                        try {
                            const res = await fetch(`${API_BASE}/tasks/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newTsk)
                            });
                            if (res.ok) {
                                showToast(`Task "${title}" created in SQLite database.`);
                            }
                        } catch (e) {
                            showToast(`Failed to create task: ${e}`);
                        }
                        await fetchStore();
                        switchView('tasks');
                    }
                });
            });
        }

        if (viewName === 'emails') {
            document.querySelectorAll('.email-row').forEach(row => {
                row.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    const msg = store.emails.find(m => m.id === id);
                    if (msg) {
                        msg.read = 1;
                        try {
                            await fetch(`${API_BASE}/emails/${id}`, {
                                method: 'PATCH',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ read: 1 })
                            });
                        } catch (e) {}

                        e.currentTarget.style.background = 'transparent';
                        const readerArea = document.getElementById('email-reader-area');
                        document.getElementById('email-reader-subject').innerText = msg.subject;
                        document.getElementById('email-reader-from').innerText = `From: ${msg.from || msg.from_email} on ${msg.date}`;
                        document.getElementById('email-reader-body').innerText = msg.body;
                        readerArea.style.display = 'block';
                        updateSidebarBadges();
                    }
                });
            });

            const emailSearchInput = document.getElementById('email-search');
            if (emailSearchInput) {
                emailSearchInput.addEventListener('input', (e) => {
                    window.currentEmailSearchTerm = e.target.value.toLowerCase().trim();
                    const container = document.querySelector('[aria-label="Admin Inbox List"]');
                    if (container) {
                        const search = window.currentEmailSearchTerm;
                        const filtered = store.emails.filter(msg => {
                            return !search ||
                                (msg.from && msg.from.toLowerCase().includes(search)) ||
                                (msg.from_email && msg.from_email.toLowerCase().includes(search)) ||
                                (msg.subject && msg.subject.toLowerCase().includes(search)) ||
                                (msg.body && msg.body.toLowerCase().includes(search));
                        });

                        if (filtered.length > 0) {
                            container.innerHTML = filtered.map(msg => {
                                const emailName = msg.name || msg.from || msg.from_email || msg.subject;
                                return `
                                <div class="email-row" data-id="${escapeHtml(msg.id)}" data-testid="row-email-${escapeHtml(msg.id)}" aria-label="${escapeHtml(emailName)}" style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; gap: 1rem; cursor: pointer; background: ${msg.read ? 'transparent' : '#f0f4f8'};">
                                    <div style="flex: 1;">
                                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                                            <strong style="font-size: 0.95rem; color: ${msg.read ? 'var(--text-muted)' : 'var(--text-main)'};">${escapeHtml(msg.from || msg.from_email)}</strong>
                                            <span style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(msg.date)}</span>
                                        </div>
                                        <div style="font-weight: ${msg.read ? '400' : '600'}; font-size: 0.95rem; margin-bottom: 0.25rem;">${escapeHtml(msg.subject)}</div>
                                        <div style="font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(msg.body)}</div>
                                    </div>
                                </div>
                            `;}).join('');

                            container.querySelectorAll('.email-row').forEach(row => {
                                row.addEventListener('click', async (ev) => {
                                    const id = ev.currentTarget.getAttribute('data-id');
                                    const msg = store.emails.find(m => m.id === id);
                                    if (msg) {
                                        msg.read = 1;
                                        try {
                                            await fetch(`${API_BASE}/emails/${id}`, {
                                                method: 'PATCH',
                                                headers: { 'Content-Type': 'application/json' },
                                                body: JSON.stringify({ read: 1 })
                                            });
                                        } catch (err) {}

                                        ev.currentTarget.style.background = 'transparent';
                                        const readerArea = document.getElementById('email-reader-area');
                                        document.getElementById('email-reader-subject').innerText = msg.subject;
                                        document.getElementById('email-reader-from').innerText = `From: ${msg.from || msg.from_email} on ${msg.date}`;
                                        document.getElementById('email-reader-body').innerText = msg.body;
                                        readerArea.style.display = 'block';
                                        updateSidebarBadges();
                                    }
                                });
                            });
                        } else {
                            container.innerHTML = '<div style="padding: 2rem; text-align: center; color: var(--text-muted);">No emails match the search filter.</div>';
                        }
                    }
                });
            }

            document.getElementById('btn-reply-email')?.addEventListener('click', () => {
                document.getElementById('email-reply-editor').style.display = 'block';
            });

            document.getElementById('btn-cancel-reply')?.addEventListener('click', () => {
                document.getElementById('email-reply-editor').style.display = 'none';
                document.getElementById('email-reply-textarea').value = '';
            });

            document.getElementById('btn-send-reply')?.addEventListener('click', async () => {
                const replyText = document.getElementById('email-reply-textarea').value.trim();
                if (replyText) {
                    const to = document.getElementById('email-reader-from').innerText.replace('From: ', '').split(' on ')[0];
                    const sub = 'Re: ' + document.getElementById('email-reader-subject').innerText;
                    try {
                        await fetch(`${API_BASE}/emails/`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                from_email: to,
                                subject: sub,
                                date: new Date().toISOString().split('T')[0],
                                read: 1,
                                body: replyText
                            })
                        });
                        showToast("Reply recorded in SQLite database.");
                    } catch (e) {}
                    await fetchStore();
                    document.getElementById('email-reply-editor').style.display = 'none';
                    document.getElementById('email-reply-textarea').value = '';
                }
            });

            document.getElementById('btn-compose-email')?.addEventListener('click', () => {
                openGenericModal("Compose New Email", `
                    <div class="form-group">
                        <label class="form-label" for="new-msg-to">To (Select Employee)</label>
                        <select id="new-msg-to" name="new-msg-to" data-testid="modal-email-to" aria-label="Recipient Employee Email" class="form-control">
                            ${getEmployeeEmailOptionsHtml()}
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-msg-sub">Subject</label>
                        <input type="text" id="new-msg-sub" name="new-msg-sub" data-testid="modal-email-sub" aria-label="Email Subject" class="form-control" placeholder="Subject">
                    </div>
                    <div class="form-group">
                        <label class="form-label" for="new-msg-body">Message</label>
                        <textarea id="new-msg-body" name="new-msg-body" data-testid="modal-email-body" aria-label="Email Message Body" class="form-control" style="height: 140px;" placeholder="Message body..."></textarea>
                    </div>
                `, "Send Email", async () => {
                    const to = document.getElementById('new-msg-to')?.value?.trim();
                    const sub = document.getElementById('new-msg-sub')?.value?.trim();
                    const body = document.getElementById('new-msg-body')?.value?.trim();
                    if (to && sub) {
                        const newMsg = {
                            from_email: to,
                            subject: sub,
                            date: new Date().toISOString().split('T')[0],
                            read: 1,
                            body: body
                        };
                        try {
                            const res = await fetch(`${API_BASE}/emails/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newMsg)
                            });
                            if (res.ok) {
                                showToast("Email saved to SQLite database successfully!");
                            }
                        } catch (e) {
                            showToast(`Failed to send email: ${e}`);
                        }
                        await fetchStore();
                        switchView('emails');
                    }
                });
            });
        }

        if (viewName === 'documents') {
            document.querySelectorAll('.btn-view-doc').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    openDocumentReader(id);
                });
            });

            const docSearchInput = document.getElementById('doc-search');
            if (docSearchInput) {
                docSearchInput.addEventListener('input', (e) => {
                    window.currentDocSearchTerm = e.target.value.toLowerCase().trim();
                    const tbody = document.querySelector('.data-table tbody');
                    if (tbody) {
                        const search = window.currentDocSearchTerm;
                        const filtered = store.documents.filter(doc => {
                            return !search ||
                                (doc.id && doc.id.toLowerCase().includes(search)) ||
                                (doc.name && doc.name.toLowerCase().includes(search)) ||
                                (doc.type && doc.type.toLowerCase().includes(search)) ||
                                (doc.relatedTo && doc.relatedTo.toLowerCase().includes(search));
                        });

                        if (filtered.length > 0) {
                            tbody.innerHTML = filtered.map(doc => `
                                <tr data-testid="row-doc-${escapeHtml(doc.id)}" aria-label="${escapeHtml(doc.name)}">
                                    <td><strong>${escapeHtml(doc.id)}</strong></td>
                                    <td>${escapeHtml(doc.name)}</td>
                                    <td><span class="status-tag active">${escapeHtml(doc.type)}</span></td>
                                    <td>${escapeHtml(doc.relatedTo || 'General')}</td>
                                    <td><button class="btn-secondary btn-sm btn-view-doc" data-id="${escapeHtml(doc.id)}" data-testid="btn-view-doc-${escapeHtml(doc.id)}" aria-label="${escapeHtml(doc.name)}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">View Document</button></td>
                                </tr>
                            `).join('');

                            tbody.querySelectorAll('.btn-view-doc').forEach(btn => {
                                btn.addEventListener('click', (ev) => {
                                    const id = ev.currentTarget.getAttribute('data-id');
                                    openDocumentReader(id);
                                });
                            });
                        } else {
                            tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 2rem;">No documents match the search filter.</td></tr>';
                        }
                    }
                });
            }
            
            document.getElementById('btn-upload-doc')?.addEventListener('click', () => {
                openGenericModal("Upload / Create Document", `
                    <div style="margin-bottom: 1rem;">
                        <label for="new-doc-name" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Document Name</label>
                        <input type="text" id="new-doc-name" data-testid="modal-doc-name" aria-label="Document Name" placeholder="Document Name (e.g. Employee Handbook 2026.pdf)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-doc-type" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Document Type</label>
                        <select id="new-doc-type" data-testid="modal-doc-type" aria-label="Document Type" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="Policy">Policy</option>
                            <option value="Report">Report</option>
                            <option value="Receipt">Receipt</option>
                            <option value="Contract">Contract</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-doc-rel" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Related To</label>
                        <input type="text" id="new-doc-rel" data-testid="modal-doc-rel" aria-label="Related To Entity" placeholder="Related To (e.g. All Staff, EMP-002)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="new-doc-content" style="display:block; font-size:0.8rem; margin-bottom:0.25rem;">Document Content</label>
                        <textarea id="new-doc-content" data-testid="modal-doc-content" aria-label="Document Content" style="width: 100%; height: 120px; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" placeholder="Document text content..."></textarea>
                    </div>
                `, "Save Document", async () => {
                    const name = document.getElementById('new-doc-name')?.value?.trim();
                    const type = document.getElementById('new-doc-type')?.value || 'Policy';
                    const rel = document.getElementById('new-doc-rel')?.value?.trim() || 'General';
                    const content = document.getElementById('new-doc-content')?.value?.trim() || '';

                    if (name) {
                        const newDoc = {
                            name: name,
                            type: type,
                            relatedTo: rel,
                            content: content
                        };
                        try {
                            const res = await fetch(`${API_BASE}/documents/`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(newDoc)
                            });
                            if (res.ok) {
                                showToast(`Document "${name}" saved in SQLite database.`);
                            }
                        } catch (e) {
                            showToast(`Failed to upload document: ${e}`);
                        }
                        await fetchStore();
                        switchView('documents');
                    }
                });
            });
        }

        if (viewName === 'departments') {
            const deptSearchInput = document.getElementById('dept-search');
            if (deptSearchInput) {
                deptSearchInput.addEventListener('input', (e) => {
                    window.currentDeptSearchTerm = e.target.value.toLowerCase().trim();
                    const grid = document.querySelector('[aria-label="Company Departments Grid"]');
                    if (grid) {
                        const search = window.currentDeptSearchTerm;
                        const allDepts = ["Engineering", "HR", "Finance", "Marketing", "Product", "Operations", "Sales", "Customer Support"];
                        const depts = allDepts.filter(d => !search || d.toLowerCase().includes(search));

                        if (depts.length > 0) {
                            grid.innerHTML = depts.map(d => {
                                const empsInDept = store.employees.filter(emp => (emp.department || '').toLowerCase() === d.toLowerCase());
                                const activeCount = empsInDept.filter(emp => emp.status === 'active').length;
                                const manager = empsInDept.find(emp => (emp.role || '').toLowerCase().includes('lead') || (emp.role || '').toLowerCase().includes('director') || (emp.role || '').toLowerCase().includes('manager')) || empsInDept[0];
                                const deptKey = d.toLowerCase().replace(/\s+/g, '-');
                                
                                return `
                                    <div class="stat-card" data-testid="dept-card-${escapeHtml(deptKey)}" aria-label="${escapeHtml(d)} Department" style="display: flex; flex-direction: column; justify-content: space-between; min-height: 180px;">
                                        <div>
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                                <h3 style="font-size: 1.1rem; color: var(--text-main); font-weight: 700;">${escapeHtml(d)}</h3>
                                                <span class="badge ${activeCount > 0 ? 'success' : 'warning'}">${activeCount} Active</span>
                                            </div>
                                            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.75rem;">
                                                Lead: <strong>${escapeHtml(manager ? manager.name : 'Unassigned')}</strong>
                                            </p>
                                        </div>
                                        <div style="border-top: 1px solid var(--border); padding-top: 0.75rem; display: flex; justify-content: space-between; align-items: center;">
                                            <span style="font-size: 0.8rem; color: var(--text-muted);">Total Team: ${empsInDept.length}</span>
                                            <button class="btn-secondary btn-sm btn-filter-dept" data-dept="${escapeHtml(d)}" data-testid="btn-dept-${escapeHtml(deptKey)}" aria-label="View Members of ${escapeHtml(d)} Department" style="font-size: 0.75rem; padding: 0.2rem 0.5rem;">View Members</button>
                                        </div>
                                    </div>
                                `;
                            }).join('');

                            grid.querySelectorAll('.btn-filter-dept').forEach(btn => {
                                btn.addEventListener('click', (ev) => {
                                    const dept = ev.currentTarget.getAttribute('data-dept');
                                    window.currentSearchTerm = dept;
                                    switchView('employees');
                                });
                            });
                        } else {
                            grid.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 2rem;">No departments match the search filter.</div>';
                        }
                    }
                });
            }

            document.querySelectorAll('.btn-filter-dept').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const dept = e.currentTarget.getAttribute('data-dept');
                    window.currentSearchTerm = dept;
                    switchView('employees');
                });
            });
        }

        if (viewName === 'approvals') {
            document.querySelectorAll('.btn-approve-leave-direct').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    try {
                        const res = await fetch(`${API_BASE}/leaves/${id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: 'approved' })
                        });
                        if (res.ok) {
                            showToast(`Leave request ${id} approved in SQLite database.`);
                        }
                    } catch (err) {
                        showToast(`Failed to approve leave: ${err}`);
                    }
                    await fetchStore();
                    switchView('approvals');
                });
            });

            document.querySelectorAll('.btn-reject-leave-direct').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    try {
                        const res = await fetch(`${API_BASE}/leaves/${id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: 'rejected' })
                        });
                        if (res.ok) {
                            showToast(`Leave request ${id} rejected in SQLite database.`);
                        }
                    } catch (err) {
                        showToast(`Failed to reject leave: ${err}`);
                    }
                    await fetchStore();
                    switchView('approvals');
                });
            });

            document.querySelectorAll('.btn-approve-exp-direct').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    try {
                        const res = await fetch(`${API_BASE}/expenses/${id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: 'approved' })
                        });
                        if (res.ok) {
                            showToast(`Expense claim ${id} approved in SQLite database.`);
                        }
                    } catch (err) {
                        showToast(`Failed to approve expense: ${err}`);
                    }
                    await fetchStore();
                    switchView('approvals');
                });
            });

            document.querySelectorAll('.btn-reject-exp-direct').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    try {
                        const res = await fetch(`${API_BASE}/expenses/${id}`, {
                            method: 'PATCH',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ status: 'rejected' })
                        });
                        if (res.ok) {
                            showToast(`Expense claim ${id} rejected in SQLite database.`);
                        }
                    } catch (err) {
                        showToast(`Failed to reject expense: ${err}`);
                    }
                    await fetchStore();
                    switchView('approvals');
                });
            });
        }

        if (viewName === 'reports') {
            document.getElementById('btn-export-audit')?.addEventListener('click', () => {
                showToast("Full compliance audit report exported to runs/reports/.");
            });
        }

        if (viewName === 'settings') {
            document.getElementById('btn-save-chaos-settings')?.addEventListener('click', async () => {
                const enabled = document.getElementById('chaos-enable')?.checked || false;
                const delay = parseInt(document.getElementById('chaos-delay')?.value || '0', 10);
                const sessionExpire = document.getElementById('chaos-session-expire')?.checked || false;
                const staleDom = document.getElementById('chaos-stale-dom')?.checked || false;

                try {
                    await fetch('/api/edge-cases/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            enabled: enabled,
                            network_delay_ms: delay,
                            simulate_session_expiry: sessionExpire,
                            stale_dom_simulation: staleDom
                        })
                    });
                    showToast("Chaos & Edge Case Simulator configuration saved.");
                } catch (e) {
                    showToast("Configuration saved locally.");
                }
            });
        }
    }

    // ==========================================
    // --- Modals & Approvals ---
    // ==========================================

    const modal = document.getElementById('approval-modal');
    const modalContent = document.getElementById('approval-content');
    
    function openExpenseApproval(expId) {
        const exp = store.expenses.find(e => e.id === expId);
        if (!exp) return;

        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-shield-halved text-warning" aria-hidden="true"></i> Action Requires Approval`;
        
        modalContent.innerHTML = `
            <div class="approval-details">
                <div class="detail-row"><span>Expense ID:</span> <span data-testid="modal-exp-detail-id">${escapeHtml(exp.id)}</span></div>
                <div class="detail-row"><span>Employee:</span> <span data-testid="modal-exp-detail-emp">${escapeHtml(exp.employee)}</span></div>
                <div class="detail-row"><span>Category:</span> <span>${escapeHtml(exp.category)}</span></div>
                <div class="detail-row"><span>Amount:</span> <span style="color: var(--primary); font-size: 1.1rem; font-weight: 700;">${escapeHtml(exp.amount)}</span></div>
                <div class="detail-row"><span>Date:</span> <span>${escapeHtml(exp.date)}</span></div>
                <div class="detail-row"><span>Description:</span> <span>${escapeHtml(exp.description)}</span></div>
                <div class="detail-row" style="margin-top: 1rem; padding-top: 0.5rem; border-top: 1px dashed var(--border);">
                    <span>Receipt Evidence:</span> 
                    <span style="color: var(--primary);"><i class="fa-solid fa-file-pdf" aria-hidden="true"></i> ${escapeHtml(exp.receiptId || 'REC-NONE')}</span>
                </div>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-top: 1rem;">
                By approving this, the expense amount will be recorded as approved in the SQLite database and processed for payroll refund.
            </p>
        `;

        modal.classList.remove('hidden');

        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        
        const newApprove = btnApprove.cloneNode(true);
        const newReject = btnReject.cloneNode(true);
        btnApprove.parentNode.replaceChild(newApprove, btnApprove);
        btnReject.parentNode.replaceChild(newReject, btnReject);

        newApprove.style.display = 'block';
        newReject.style.display = 'block';
        newApprove.innerText = 'Approve Expense';
        newApprove.setAttribute('data-testid', 'btn-modal-approve-exp');
        newApprove.setAttribute('aria-label', `Approve Expense ${exp.id}`);
        newReject.innerText = 'Reject Expense';
        newReject.setAttribute('data-testid', 'btn-modal-reject-exp');
        newReject.setAttribute('aria-label', `Reject Expense ${exp.id}`);

        newApprove.addEventListener('click', async () => {
            try {
                const res = await fetch(`${API_BASE}/expenses/${exp.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'approved' })
                });
                if (res.ok) {
                    showToast(`Expense ${exp.id} successfully APPROVED in SQLite database!`);
                }
            } catch (e) {
                showToast(`Failed to approve expense: ${e}`);
            }
            modal.classList.add('hidden');
            await fetchStore();
            if (currentView === 'expenses') switchView('expenses');
            if (currentView === 'dashboard') switchView('dashboard');
        });

        newReject.addEventListener('click', async () => {
            try {
                const res = await fetch(`${API_BASE}/expenses/${exp.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: 'rejected' })
                });
                if (res.ok) {
                    showToast(`Expense ${exp.id} marked as REJECTED in SQLite database.`);
                }
            } catch (e) {
                showToast(`Failed to reject expense: ${e}`);
            }
            modal.classList.add('hidden');
            await fetchStore();
            if (currentView === 'expenses') switchView('expenses');
            if (currentView === 'dashboard') switchView('dashboard');
        });
    }

    function openDocumentReader(docId) {
        const doc = store.documents.find(d => d.id === docId);
        if (!doc) return;

        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-file-lines text-primary" aria-hidden="true"></i> Document Viewer`;
        
        modalContent.innerHTML = `
            <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
                <h4 style="margin-bottom: 0.5rem;">${escapeHtml(doc.name)}</h4>
                <div style="font-size: 0.8rem; color: var(--text-muted);">Type: ${escapeHtml(doc.type)} | ID: ${escapeHtml(doc.id)} | Related: ${escapeHtml(doc.relatedTo)}</div>
            </div>
            <div id="document-content-area" data-testid="document-content-area" aria-label="Document text content" style="background: #f9fafb; padding: 1rem; border-radius: var(--radius); border: 1px solid var(--border); font-family: monospace; font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; height: 250px; overflow-y: auto;">${escapeHtml(doc.content)}</div>
        `;

        modal.classList.remove('hidden');

        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        btnApprove.style.display = 'none';
        btnReject.innerText = 'Close Document';
        btnReject.setAttribute('data-testid', 'btn-modal-close-doc');
        btnReject.setAttribute('aria-label', 'Close Document Viewer');
        
        const newReject = btnReject.cloneNode(true);
        btnReject.parentNode.replaceChild(newReject, btnReject);
        
        newReject.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }

    function openGenericModal(title, htmlContent, approveText, onApprove = null) {
        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-layer-group text-primary" aria-hidden="true"></i> ${title}`;
        modalContent.innerHTML = htmlContent;
        modal.classList.remove('hidden');

        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        
        btnApprove.style.display = 'block';
        btnReject.style.display = 'block';
        
        const newApprove = btnApprove.cloneNode(true);
        const newReject = btnReject.cloneNode(true);
        btnApprove.parentNode.replaceChild(newApprove, btnApprove);
        btnReject.parentNode.replaceChild(newReject, btnReject);

        newApprove.innerText = approveText;
        newApprove.setAttribute('data-testid', 'btn-modal-submit');
        newApprove.setAttribute('data-action', approveText.toLowerCase().replace(/\s+/g, '-'));
        newApprove.setAttribute('aria-label', approveText);
        newReject.innerText = 'Cancel';
        newReject.setAttribute('data-testid', 'btn-modal-cancel');
        newReject.setAttribute('aria-label', 'Cancel');

        newApprove.addEventListener('click', async () => {
            if (onApprove) await onApprove();
            modal.classList.add('hidden');
        });

        newReject.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }

    function openTaskModal(tsk) {
        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-clipboard-check text-primary" aria-hidden="true"></i> Task Details`;
        
        modalContent.innerHTML = `
            <div class="approval-details">
                <div class="detail-row"><span>Task ID:</span> <span data-testid="modal-task-detail-id">${escapeHtml(tsk.id)}</span></div>
                <div class="detail-row"><span>Title:</span> <strong>${escapeHtml(tsk.title)}</strong></div>
                <div class="detail-row"><span>Assigned To:</span> <span>${escapeHtml(tsk.assignedTo)}</span></div>
                <div class="detail-row"><span>Due Date:</span> <span style="color: var(--danger);">${escapeHtml(tsk.dueDate)}</span></div>
                <div class="detail-row"><span>Priority:</span> <span>${escapeHtml((tsk.priority || '').toUpperCase())}</span></div>
                <div class="detail-row"><span>Current Status:</span> <span>${escapeHtml((tsk.status || '').replace('_', ' ').toUpperCase())}</span></div>
            </div>
            <div style="margin-top: 1.5rem; border-top: 1px solid var(--border); padding-top: 1rem;">
                <label for="task-status-update" style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Update Task Status in SQLite</label>
                <select id="task-status-update" name="task-status-update" data-testid="task-status-update" aria-label="Update Task Status in SQLite Database" class="form-control" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    <option value="pending" ${tsk.status === 'pending' ? 'selected' : ''}>Pending</option>
                    <option value="in_progress" ${tsk.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                    <option value="completed" ${tsk.status === 'completed' ? 'selected' : ''}>Completed</option>
                </select>
            </div>
        `;

        modal.classList.remove('hidden');

        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        
        btnApprove.style.display = 'block';
        btnReject.style.display = 'block';
        
        const newApprove = btnApprove.cloneNode(true);
        const newReject = btnReject.cloneNode(true);
        btnApprove.parentNode.replaceChild(newApprove, btnApprove);
        btnReject.parentNode.replaceChild(newReject, btnReject);

        newApprove.innerText = 'Save Status';
        newApprove.setAttribute('data-testid', 'btn-modal-save-task');
        newApprove.setAttribute('aria-label', 'Save Task Status');
        newReject.innerText = 'Cancel';
        newReject.setAttribute('data-testid', 'btn-modal-cancel-task');
        newReject.setAttribute('aria-label', 'Cancel');

        newApprove.addEventListener('click', async () => {
            const newStatus = document.getElementById('task-status-update').value;
            try {
                const res = await fetch(`${API_BASE}/tasks/${tsk.id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                if (res.ok) {
                    showToast(`Task ${tsk.id} status updated to "${newStatus.replace('_', ' ')}" in SQLite!`);
                }
            } catch (e) {
                showToast(`Failed to update task: ${e}`);
            }
            modal.classList.add('hidden');
            await fetchStore();
            switchView('tasks');
        });

        newReject.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }

    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    });

    function showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 20px; right: 20px;
            background: #1e293b; color: white;
            padding: 1rem 1.5rem; border-radius: 8px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); font-weight: 500; font-size: 0.9rem;
            z-index: 9999; animation: slideUp 0.3s ease; display: flex; align-items: center; gap: 0.5rem;
        `;
        toast.innerHTML = `<i class="fa-solid fa-circle-check" style="color: #10b981; font-size: 1.1rem;" aria-hidden="true"></i> <span>${escapeHtml(message)}</span>`;
        document.body.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 3500);
    }

    // Initialize AI Modal Logic
    const aiModal = document.getElementById('ai-modal');
    const aiHelpBtn = document.getElementById('ai-help-btn');
    const aiCloseBtn = document.getElementById('close-ai-modal');
    const aiSubmitBtn = document.getElementById('btn-submit-task');
    const aiTaskInput = document.getElementById('ai-task-input');
    const aiChatHistory = document.getElementById('ai-chat-history');

    if (aiHelpBtn && aiModal) {
        aiHelpBtn.addEventListener('click', () => {
            aiModal.classList.remove('hidden');
        });
        aiCloseBtn.addEventListener('click', () => {
            aiModal.classList.add('hidden');
        });
        aiSubmitBtn.addEventListener('click', async () => {
            const task = aiTaskInput.value.trim();
            if (!task) return;
            
            aiChatHistory.innerHTML += `<div style="padding: 0.5rem; background: #e5e7eb; border-radius: 0.5rem; align-self: flex-end; max-width: 80%;">${escapeHtml(task)}</div>`;
            aiTaskInput.value = '';
            
            const loadingId = 'loading-' + Date.now();
            aiChatHistory.innerHTML += `<div id="${loadingId}" style="padding: 0.5rem; background: #e0f2fe; border-radius: 0.5rem; align-self: flex-start; max-width: 80%;">Thinking...</div>`;
            aiChatHistory.scrollTop = aiChatHistory.scrollHeight;

            try {
                const res = await fetch('http://localhost:8001/api/runs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ task: task })
                });
                const data = await res.json();
                document.getElementById(loadingId).innerText = "Task submitted! Run ID: " + data.run_id + ". I am processing it directly against SQLite in the background!";
            } catch (err) {
                document.getElementById(loadingId).innerText = "Error contacting AI Agent. Make sure the backend on port 8001 is running!";
                document.getElementById(loadingId).style.background = "#fee2e2";
            }
        });
    }

    // Initialize Developer HUD / Watchdog Panel Minimization
    const debugPanel = document.getElementById('dev-debug-panel');
    const debugHeader = document.getElementById('debug-header');
    const toggleDebugBtn = document.getElementById('toggle-debug-hud');
    const debugBody = document.getElementById('debug-body');

    if (debugPanel && debugHeader) {
        const toggleHUD = (e) => {
            if (e) e.stopPropagation();
            const isCollapsed = debugPanel.classList.toggle('collapsed');
            if (debugBody) {
                debugBody.classList.toggle('hidden', isCollapsed);
            }
            if (toggleDebugBtn) {
                toggleDebugBtn.innerHTML = isCollapsed 
                    ? '<i class="fa-solid fa-chevron-up" aria-hidden="true"></i>' 
                    : '<i class="fa-solid fa-chevron-down" aria-hidden="true"></i>';
            }
        };
        debugHeader.addEventListener('click', toggleHUD);
        if (toggleDebugBtn) {
            toggleDebugBtn.addEventListener('click', toggleHUD);
        }
    }

    // Initialize Default View
    switchView('dashboard');
});
