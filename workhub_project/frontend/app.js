// WorkHub HR App - Frontend Logic

window.store = (typeof mockData !== 'undefined' && mockData) ? {
    employees: mockData.employees || [],
    expenses: mockData.expenses || [],
    leaves: mockData.leaves || [],
    benefits: mockData.benefits || [],
    tasks: mockData.tasks || [],
    emails: mockData.emails || [],
    documents: mockData.documents || []
} : {
    employees: [], expenses: [], leaves: [], benefits: [], tasks: [], emails: [], documents: []
};

const API_BASE = 'http://localhost:8000/api/hr';

async function fetchStore() {
    const endpoints = ['employees', 'expenses', 'leaves', 'benefits', 'tasks', 'emails', 'documents'];
    let apiSuccess = false;
    for (const ep of endpoints) {
        try {
            const res = await fetch(`${API_BASE}/${ep}/`, { cache: 'no-store' });
            if (res.ok) {
                window.store[ep] = await res.json();
                apiSuccess = true;
            }
        } catch (e) {
            // Silently handle offline API
        }
    }
    // If API endpoint was unreachable, sync from mockData if available
    if (!apiSuccess && typeof mockData !== 'undefined' && mockData) {
        for (const ep of endpoints) {
            if (mockData[ep]) {
                window.store[ep] = mockData[ep];
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    // Navigation Routing
    const navItems = document.querySelectorAll('.nav-item');
    const viewContainer = document.getElementById('view-container');
    
    viewContainer.innerHTML = '<h2>Loading data...</h2>';
    await fetchStore();
    
    let currentView = 'dashboard';

    // View templates
    const views = {
        dashboard: renderDashboard,
        employees: renderEmployees,
        expenses: renderExpenses,
        leaves: renderLeaves,
        benefits: renderBenefits,
        tasks: renderTasks,
        emails: renderEmails,
        documents: renderDocuments
    };

    function switchView(viewName, data = null) {
        currentView = viewName;
        navItems.forEach(item => item.classList.remove('active'));
        const activeItem = document.querySelector(`.nav-item[data-view="${viewName}"]`);
        if (activeItem) activeItem.classList.add('active');

        if (views[viewName]) {
            viewContainer.innerHTML = views[viewName](data);
            attachEventListeners(viewName);
        } else {
            viewContainer.innerHTML = `<h2>Not Found</h2>`;
        }
    }

    // Real-time synchronization polling
    setInterval(async () => {
        await fetchStore();
        // Silently re-render the current view with the new data
        if (views[currentView]) {
            viewContainer.innerHTML = views[currentView]();
            attachEventListeners(currentView);
        }
    }, 3000);

    // Event Delegation for Navigation
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(item.dataset.view);
        });
    });

    // --- View Renderers ---

    function renderDashboard() {
        const totalEmployees = store.employees.length;
        const pendingExpenses = store.expenses.filter(e => e.status === 'pending').length;
        const pendingLeaves = store.leaves.filter(l => l.status === 'pending').length;
        const pendingApprovals = pendingExpenses + pendingLeaves;
        const openTasks = store.tasks.filter(t => t.status !== 'completed').length;
        
        let totalExpAmount = 0;
        store.expenses.filter(e => e.status === 'approved').forEach(e => {
            let num = parseInt(e.amount.replace(/[^0-9]/g, ''), 10);
            if (!isNaN(num)) totalExpAmount += num;
        });

        return `
            <div class="card-header">
                <h2>Overview Dashboard</h2>
                <button class="btn-primary"><i class="fa-solid fa-download"></i> Generate Report</button>
            </div>
            
            <div class="dashboard-grid">
                <div class="stat-card">
                    <div class="stat-icon blue"><i class="fa-solid fa-users"></i></div>
                    <div class="stat-details">
                        <h3>Total Employees</h3>
                        <p>${totalEmployees}</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon orange"><i class="fa-solid fa-clock-rotate-left"></i></div>
                    <div class="stat-details">
                        <h3>Pending Approvals</h3>
                        <p>${pendingApprovals}</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon red"><i class="fa-solid fa-ticket"></i></div>
                    <div class="stat-details">
                        <h3>Open HR Tasks</h3>
                        <p>${openTasks}</p>
                    </div>
                </div>
                <div class="stat-card">
                    <div class="stat-icon green"><i class="fa-solid fa-indian-rupee-sign"></i></div>
                    <div class="stat-details">
                        <h3>Expenses Processed</h3>
                        <p>₹${totalExpAmount.toLocaleString('en-IN')}</p>
                    </div>
                </div>
            </div>

            <div class="card-header" style="margin-top: 2rem;">
                <h2>Recent Activity</h2>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Event</th>
                        <th>User</th>
                        <th>Time</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${store.expenses.slice(0, 2).map(exp => `
                        <tr>
                            <td>Expense Submitted (${exp.id})</td>
                            <td>${exp.employee}</td>
                            <td>Recently</td>
                            <td><span class="status-tag ${exp.status}">${exp.status.charAt(0).toUpperCase() + exp.status.slice(1)}</span></td>
                        </tr>
                    `).join('')}
                    ${store.leaves.slice(0, 2).map(lv => `
                        <tr>
                            <td>Leave Request (${lv.id})</td>
                            <td>${lv.employee}</td>
                            <td>Recently</td>
                            <td><span class="status-tag ${lv.status}">${lv.status.charAt(0).toUpperCase() + lv.status.slice(1)}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    function renderEmployees() {
        let filteredData = window.currentSearchTerm ? 
            store.employees.filter(e => e.name.toLowerCase().includes(window.currentSearchTerm) || e.id.toLowerCase().includes(window.currentSearchTerm)) 
            : store.employees;

        let rows = filteredData.map(emp => `
            <tr data-emp-id="${emp.id}" class="employee-row" style="cursor: pointer;">
                <td><strong>${emp.name}</strong><br><small style="color: #6b7280">${emp.email}</small></td>
                <td>${emp.id}</td>
                <td>${emp.department}</td>
                <td>${emp.role}</td>
                <td><span class="status-tag ${emp.status === 'active' ? 'active' : 'pending'}">${(emp.status || '').replace('_', ' ').toUpperCase()}</span></td>
                <td>
                    <button class="icon-btn btn-view-emp" data-id="${emp.id}"><i class="fa-solid fa-chevron-right"></i></button>
                </td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Employee Directory</h2>
                <div style="display: flex; gap: 1rem;">
                    <input type="text" id="emp-search" placeholder="Search employees..." style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    <button class="btn-primary" id="btn-add-employee"><i class="fa-solid fa-user-plus"></i> Add Employee</button>
                </div>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Employee</th>
                        <th>ID</th>
                        <th>Department</th>
                        <th>Role</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }

    // Register a specific view for detailed employee profile
    views['employee_profile'] = function(empId) {
        const emp = store.employees.find(e => e.id === empId);
        if (!emp) return `<h2>Employee Not Found</h2>`;

        return `
            <div class="card-header">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <button class="btn-secondary" id="btn-back-employees"><i class="fa-solid fa-arrow-left"></i> Back</button>
                    <h2>Employee Profile: ${emp.name}</h2>
                </div>
                <button class="btn-primary" id="btn-save-emp"><i class="fa-solid fa-save"></i> Save Changes</button>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-top: 2rem;">
                <!-- Profile Form -->
                <div style="background: var(--card-bg); padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border);">
                    <h3 style="margin-bottom: 1.5rem; font-size: 1.1rem;">Personal Information</h3>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Full Name</label>
                        <input type="text" id="emp-name" value="${emp.name}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" disabled>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Email Address</label>
                        <input type="email" id="emp-email" value="${emp.email}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" disabled>
                    </div>

                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Phone Number</label>
                        <input type="text" id="emp-phone" value="${emp.phone}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Emergency Contact (Name & Phone)</label>
                        <!-- ID specifies this field so the agent can find it -->
                        <input type="text" id="emp-emergency-contact" value="${emp.emergencyContact}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    </div>
                </div>

                <!-- Employment Details -->
                <div style="background: var(--card-bg); padding: 1.5rem; border-radius: var(--radius); border: 1px solid var(--border);">
                    <h3 style="margin-bottom: 1.5rem; font-size: 1.1rem;">Employment Details</h3>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Employee ID</label>
                        <input type="text" value="${emp.id}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;" disabled>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Department</label>
                        <select id="emp-dept" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="Engineering" ${emp.department === 'Engineering' ? 'selected' : ''}>Engineering</option>
                            <option value="HR" ${emp.department === 'HR' ? 'selected' : ''}>HR</option>
                            <option value="Finance" ${emp.department === 'Finance' ? 'selected' : ''}>Finance</option>
                            <option value="Marketing" ${emp.department === 'Marketing' ? 'selected' : ''}>Marketing</option>
                        </select>
                    </div>
                    
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Status</label>
                        <select id="emp-status" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                            <option value="active" ${emp.status === 'active' ? 'selected' : ''}>Active</option>
                            <option value="on_leave" ${emp.status === 'on_leave' ? 'selected' : ''}>On Leave</option>
                            <option value="inactive" ${emp.status === 'inactive' ? 'selected' : ''}>Inactive</option>
                        </select>
                    </div>
                </div>
            </div>
        `;
    };

    function renderExpenses() {
        const filterVal = window.expenseFilter || 'all';
        let rows = store.expenses
            .filter(e => filterVal === 'all' || e.status === filterVal)
            .map(exp => `
            <tr>
                <td><strong>${exp.id}</strong></td>
                <td>${exp.employee}</td>
                <td>${exp.category}</td>
                <td><strong>${exp.amount}</strong></td>
                <td>${exp.date}</td>
                <td><span class="status-tag ${exp.status}" id="status-${exp.id}">${(exp.status || '').toUpperCase()}</span></td>
                <td>
                    ${exp.status === 'pending' ? 
                        `<button class="btn-primary btn-sm btn-review-expense" id="review-${exp.id}" data-id="${exp.id}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Review</button>` : 
                        `<button class="btn-secondary btn-sm" disabled style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Processed</button>`
                    }
                </td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Expense Management</h2>
                <div style="display: flex; gap: 1rem;">
                    <button class="btn-primary" id="btn-add-expense"><i class="fa-solid fa-plus"></i> Add Expense</button>
                    <button class="btn-secondary" id="btn-filter-expenses"><i class="fa-solid fa-filter"></i> Filter</button>
                </div>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Employee</th>
                        <th>Category</th>
                        <th>Amount</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }

    function renderDocuments() {
        let rows = store.documents.map(doc => `
            <tr>
                <td><i class="fa-solid ${doc.type === 'Policy' ? 'fa-file-lines text-primary' : 'fa-file-pdf text-danger'}"></i></td>
                <td><strong>${doc.id}</strong></td>
                <td>${doc.name}</td>
                <td><span class="status-tag ${doc.type === 'Policy' ? 'active' : 'pending'}">${doc.type}</span></td>
                <td>${doc.relatedTo}</td>
                <td>
                    <button class="btn-secondary btn-sm btn-view-doc" data-id="${doc.id}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Read Document</button>
                </td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Company Documents & Evidence</h2>
                <div style="display: flex; gap: 1rem;">
                    <input type="text" placeholder="Search documents..." style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
                    <button class="btn-primary" id="btn-upload-doc"><i class="fa-solid fa-upload"></i> Upload</button>
                    <input type="file" id="file-upload-input" style="display: none;">
                </div>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th></th>
                        <th>Doc ID</th>
                        <th>File Name</th>
                        <th>Type</th>
                        <th>Related Record</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }

    function renderLeaves() {
        let rows = store.leaves.map(lv => `
            <tr>
                <td><strong>${lv.id}</strong></td>
                <td>${lv.employee}</td>
                <td>${lv.type}</td>
                <td>${lv.dates}</td>
                <td><span class="status-tag ${lv.status}">${(lv.status || '').toUpperCase()}</span></td>
                <td>
                    ${lv.status === 'pending' ? 
                        `<button class="btn-primary btn-sm btn-action-leave" data-id="${lv.id}" data-action="approve" style="padding: 0.25rem 0.75rem; font-size: 0.8rem; margin-right: 0.25rem;">Approve</button>
                         <button class="btn-secondary btn-sm btn-action-leave" data-id="${lv.id}" data-action="reject" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Reject</button>` : 
                        `<button class="btn-secondary btn-sm" disabled style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Processed</button>`
                    }
                </td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Leave Requests</h2>
                <button class="btn-secondary" id="btn-view-calendar"><i class="fa-solid fa-calendar"></i> View Calendar</button>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Request ID</th>
                        <th>Employee</th>
                        <th>Type</th>
                        <th>Dates</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }

    function renderEmails() {
        let rows = store.emails.map(msg => `
            <div class="email-row" data-id="${msg.id}" style="padding: 1rem; border-bottom: 1px solid var(--border); display: flex; gap: 1rem; cursor: pointer; background: ${msg.read ? 'transparent' : '#f0f4f8'};">
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                        <strong style="font-size: 0.95rem; color: ${msg.read ? 'var(--text-muted)' : 'var(--text-main)'};">${msg.from}</strong>
                        <span style="font-size: 0.8rem; color: var(--text-muted);">${msg.date}</span>
                    </div>
                    <div style="font-weight: ${msg.read ? '400' : '600'}; font-size: 0.95rem; margin-bottom: 0.25rem;">${msg.subject}</div>
                    <div style="font-size: 0.85rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${msg.body}</div>
                </div>
            </div>
        `).join('');

        return `
            <div class="card-header">
                <h2>Admin Inbox</h2>
                <div style="display: flex; gap: 1rem;">
                    <input type="text" placeholder="Search emails..." style="padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px; width: 300px;">
                    <button class="btn-primary" id="btn-compose-email"><i class="fa-solid fa-pen"></i> Compose</button>
                </div>
            </div>
            <div style="background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius); overflow: hidden; margin-top: 1rem;">
                ${rows}
            </div>
            <div id="email-reader-area" style="margin-top: 2rem; display: none; background: var(--card-bg); padding: 1.5rem; border: 1px solid var(--border); border-radius: var(--radius);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem;">
                    <div>
                        <h3 id="email-reader-subject" style="margin-bottom: 0.5rem;"></h3>
                        <div id="email-reader-from" style="font-size: 0.85rem; color: var(--text-muted);"></div>
                    </div>
                    <button class="btn-secondary" id="btn-reply-email"><i class="fa-solid fa-reply"></i> Reply</button>
                </div>
                <div id="email-reader-body" style="font-size: 0.95rem; line-height: 1.6; white-space: pre-wrap; margin-bottom: 2rem;"></div>
                
                <!-- Reply Editor (Hidden by default) -->
                <div id="email-reply-editor" style="display: none; border-top: 1px dashed var(--border); padding-top: 1.5rem;">
                    <h4 style="margin-bottom: 1rem; color: var(--text-muted);"><i class="fa-solid fa-reply"></i> Draft Reply</h4>
                    <textarea id="email-reply-textarea" style="width: 100%; height: 120px; padding: 1rem; border: 1px solid var(--border); border-radius: var(--radius); margin-bottom: 1rem; font-family: inherit;" placeholder="Type your reply here..."></textarea>
                    <div style="display: flex; justify-content: flex-end; gap: 1rem;">
                        <button class="btn-secondary" id="btn-cancel-reply">Cancel</button>
                        <button class="btn-primary" id="btn-send-reply"><i class="fa-solid fa-paper-plane"></i> Send Reply</button>
                    </div>
                </div>
            </div>
        `;
    }

    function renderBenefits() {
        let rows = store.benefits.map(ben => `
            <tr>
                <td><strong>${ben.id}</strong></td>
                <td>${ben.name}</td>
                <td>${ben.provider}</td>
                <td>${ben.coverage}</td>
                <td>${ben.enrolled}</td>
                <td><span class="status-tag ${ben.status === 'active' ? 'active' : 'pending'}">${(ben.status || '').toUpperCase()}</span></td>
                <td><button class="btn-secondary btn-sm btn-manage-benefit" data-id="${ben.id}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Manage</button></td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>Employee Benefits</h2>
                <button class="btn-primary" id="btn-add-benefit"><i class="fa-solid fa-plus"></i> Add Benefit</button>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Benefit Name</th>
                        <th>Provider</th>
                        <th>Coverage</th>
                        <th>Enrolled</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }

    function renderTasks() {
        let rows = store.tasks.map(tsk => `
            <tr>
                <td><strong>${tsk.id}</strong></td>
                <td>${tsk.title}</td>
                <td>${tsk.assignedTo}</td>
                <td>${tsk.dueDate}</td>
                <td><span class="status-tag pending">${(tsk.priority || '').toUpperCase()}</span></td>
                <td><span class="status-tag ${tsk.status === 'pending' ? 'pending' : (tsk.status === 'completed' ? 'active' : 'approved')}">${(tsk.status || '').replace('_', ' ').toUpperCase()}</span></td>
                <td>
                    <button class="btn-secondary btn-sm btn-open-task" data-id="${tsk.id}" style="padding: 0.25rem 0.75rem; font-size: 0.8rem;">Open Task</button>
                </td>
            </tr>
        `).join('');

        return `
            <div class="card-header">
                <h2>HR Tasks</h2>
                <button class="btn-primary" id="btn-new-task"><i class="fa-solid fa-plus"></i> New Task</button>
            </div>
            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Task</th>
                        <th>Assigned To</th>
                        <th>Due Date</th>
                        <th>Priority</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                </tbody>
            </table>
        `;
    }

    // --- Event Attachments & Interactions ---

    function attachEventListeners(viewName) {
        if (viewName === 'expenses') {
            document.querySelectorAll('.btn-review-expense').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.target.getAttribute('data-id');
                    openExpenseApproval(id);
                });
            });
            document.getElementById('btn-filter-expenses')?.addEventListener('click', () => {
                openGenericModal("Filter Expenses", `
                    <div style="margin-bottom: 1rem;">
                        <label style="display: block; margin-bottom: 0.5rem; font-size: 0.85rem;">Status</label>
                        <select id="expense-status-filter" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);">
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
        }
        
        if (viewName === 'employees') {
            document.querySelectorAll('.employee-row').forEach(row => {
                row.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-emp-id');
                    switchView('employee_profile', id);
                });
            });
            document.getElementById('btn-add-employee')?.addEventListener('click', () => {
                openGenericModal("Add New Employee", `
                    <div style="margin-bottom: 1rem;"><input type="text" id="new-emp-name" placeholder="Full Name" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <div style="margin-bottom: 1rem;"><input type="email" id="new-emp-email" placeholder="Email" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <div style="margin-bottom: 1rem;"><select id="new-emp-dept" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"><option>Engineering</option><option>HR</option><option>Marketing</option><option>Sales</option><option>Finance</option></select></div>
                `, "Create Employee", () => {
                    const name = document.getElementById('new-emp-name').value;
                    const email = document.getElementById('new-emp-email').value;
                    const dept = document.getElementById('new-emp-dept').value;
                    if (name && email) {
                        store.employees.unshift({
                            id: "EMP-" + String(store.employees.length + 1).padStart(3, '0'),
                            name: name,
                            department: dept,
                            role: "New Hire",
                            status: "active",
                            email: email,
                            joined: new Date().toISOString().split('T')[0],
                            emergencyContact: "Pending",
                            phone: "Pending",
                            manager: "Admin"
                        });
                        switchView('employees');
                    }
                });
            });
        }

        if (viewName === 'employee_profile') {
            document.getElementById('btn-back-employees').addEventListener('click', () => {
                switchView('employees');
            });

            document.getElementById('btn-save-emp').addEventListener('click', () => {
                showToast("Employee profile updated successfully.");
                // Note: In a real app we would update the store here.
            });
        }

        if (viewName === 'documents') {
            document.querySelectorAll('.btn-view-doc').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    openDocumentReader(id);
                });
            });
            
            document.getElementById('btn-upload-doc')?.addEventListener('click', () => {
                document.getElementById('file-upload-input').click();
            });
            document.getElementById('file-upload-input')?.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    showToast(`File "${e.target.files[0].name}" uploaded successfully!`);
                }
            });
        }
        
        if (viewName === 'leaves') {
            document.querySelectorAll('.btn-action-leave').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    const action = e.currentTarget.getAttribute('data-action');
                    const lv = store.leaves.find(l => l.id === id);
                    if (lv) {
                        lv.status = action === 'approve' ? 'approved' : 'rejected';
                        switchView('leaves');
                        showToast(`Leave ${id} successfully ${action}d.`);
                    }
                });
            });
            document.getElementById('btn-view-calendar')?.addEventListener('click', () => {
                const upcomingLeaves = store.leaves.filter(l => l.status === 'approved').map(l => `
                    <div style="padding: 0.5rem; border-bottom: 1px solid var(--border);">
                        <strong>${l.employee}</strong> - ${l.type} (${l.dates})
                    </div>
                `).join('');
                openGenericModal("Upcoming Leave Calendar", `
                    <div style="max-height: 200px; overflow-y: auto; background: var(--bg-alt); padding: 0.5rem; border-radius: 4px;">
                        ${upcomingLeaves || '<p style="color: var(--text-muted); padding: 0.5rem;">No upcoming approved leaves.</p>'}
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
                        openGenericModal(`Manage Benefit: ${ben.name}`, `
                            <p>Change coverage details or enrollment limits here.</p>
                            <div style="margin-bottom: 1rem; margin-top: 1rem;"><input type="text" id="edit-ben-cov" value="${ben.coverage}" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                            <select id="edit-ben-status" style="width: 100%; padding: 0.5rem;"><option value="active" ${ben.status==='active'?'selected':''}>Active</option><option value="inactive" ${ben.status==='inactive'?'selected':''}>Inactive</option></select>
                        `, "Save Changes", () => {
                            ben.coverage = document.getElementById('edit-ben-cov').value;
                            ben.status = document.getElementById('edit-ben-status').value;
                            switchView('benefits');
                        });
                    }
                });
            });
            document.getElementById('btn-add-benefit')?.addEventListener('click', () => {
                openGenericModal("Add New Benefit", `
                    <div style="margin-bottom: 1rem;"><input type="text" id="new-ben-name" placeholder="Benefit Name (e.g. Dental)" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <div style="margin-bottom: 1rem;"><input type="text" id="new-ben-prov" placeholder="Provider Name" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <div style="margin-bottom: 1rem;"><input type="text" id="new-ben-cov" placeholder="Coverage Details" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                `, "Create Benefit", () => {
                    const name = document.getElementById('new-ben-name').value;
                    const prov = document.getElementById('new-ben-prov').value;
                    const cov = document.getElementById('new-ben-cov').value;
                    if (name && prov) {
                        store.benefits.push({
                            id: "BEN-" + String(store.benefits.length + 1).padStart(2, '0'),
                            name: name,
                            provider: prov,
                            coverage: cov || "Standard",
                            enrolled: 0,
                            status: "active"
                        });
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
            document.getElementById('btn-new-task')?.addEventListener('click', () => {
                openGenericModal("Create New HR Task", `
                    <div style="margin-bottom: 1rem;"><input type="text" id="new-tsk-title" placeholder="Task Title" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <div style="margin-bottom: 1rem;"><input type="date" id="new-tsk-date" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                `, "Assign Task", () => {
                    const title = document.getElementById('new-tsk-title').value;
                    const date = document.getElementById('new-tsk-date').value;
                    if (title) {
                        store.tasks.unshift({
                            id: "TSK-00" + (store.tasks.length + 1),
                            title: title,
                            assignedTo: "Admin",
                            dueDate: date || new Date().toISOString().split('T')[0],
                            priority: "medium",
                            status: "pending"
                        });
                        switchView('tasks');
                    }
                });
            });
        }

        if (viewName === 'emails') {
            document.querySelectorAll('.email-row').forEach(row => {
                row.addEventListener('click', (e) => {
                    const id = e.currentTarget.getAttribute('data-id');
                    const msg = store.emails.find(m => m.id === id);
                    if (msg) {
                        msg.read = true;
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.querySelector('strong').style.color = 'var(--text-muted)';
                        
                        const readerArea = document.getElementById('email-reader-area');
                        document.getElementById('email-reader-subject').innerText = msg.subject;
                        document.getElementById('email-reader-from').innerText = `From: ${msg.from} on ${msg.date}`;
                        document.getElementById('email-reader-body').innerText = msg.body;
                        readerArea.style.display = 'block';
                    }
                });
            });

            document.getElementById('btn-reply-email')?.addEventListener('click', () => {
                document.getElementById('email-reply-editor').style.display = 'block';
            });
            document.getElementById('btn-cancel-reply')?.addEventListener('click', () => {
                document.getElementById('email-reply-editor').style.display = 'none';
                document.getElementById('email-reply-textarea').value = '';
            });
            document.getElementById('btn-send-reply')?.addEventListener('click', () => {
                showToast("Reply sent successfully.");
                document.getElementById('email-reply-editor').style.display = 'none';
                document.getElementById('email-reply-textarea').value = '';
            });
            document.getElementById('btn-compose-email')?.addEventListener('click', () => {
                openGenericModal("Compose New Email", `
                    <div style="margin-bottom: 1rem;"><input type="email" id="new-msg-to" placeholder="To: email@workhub.local" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <div style="margin-bottom: 1rem;"><input type="text" id="new-msg-sub" placeholder="Subject" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border);"></div>
                    <textarea id="new-msg-body" style="width: 100%; height: 150px; padding: 0.5rem; border: 1px solid var(--border);" placeholder="Message body..."></textarea>
                `, "Send Email", () => {
                    const to = document.getElementById('new-msg-to').value;
                    const sub = document.getElementById('new-msg-sub').value;
                    const body = document.getElementById('new-msg-body').value;
                    if (to && sub) {
                        store.emails.unshift({
                            id: "MSG-00" + (store.emails.length + 1),
                            from: to,
                            subject: sub,
                            date: new Date().toISOString().split('T')[0],
                            read: true,
                            body: body
                        });
                        switchView('emails');
                    }
                });
            });
        }
    }

    // --- Global Search Bar ---
    const searchBar = document.querySelector('.search-bar input');
    window.currentSearchTerm = '';
    if (searchBar) {
        searchBar.addEventListener('input', (e) => {
            window.currentSearchTerm = e.target.value.toLowerCase().trim();
            const activeView = document.querySelector('.nav-item.active')?.dataset.view;
            if (activeView) {
                switchView(activeView); // Re-render active view with filter
            }
        });
    }

    // --- Approval & Reader Modal Logic (Agent Target) ---
    const modal = document.getElementById('approval-modal');
    const modalContent = document.getElementById('approval-content');
    
    function openExpenseApproval(expId) {
        const exp = store.expenses.find(e => e.id === expId);
        if (!exp) return;

        // Change modal header back to normal
        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-shield-halved text-warning"></i> Action Requires Approval`;
        
        modalContent.innerHTML = `
            <div class="approval-details">
                <div class="detail-row"><span>Expense ID:</span> <span>${exp.id}</span></div>
                <div class="detail-row"><span>Employee:</span> <span>${exp.employee}</span></div>
                <div class="detail-row"><span>Category:</span> <span>${exp.category}</span></div>
                <div class="detail-row"><span>Amount:</span> <span style="color: var(--primary); font-size: 1.1rem;">${exp.amount}</span></div>
                <div class="detail-row"><span>Date:</span> <span>${exp.date}</span></div>
                <div class="detail-row"><span>Description:</span> <span>${exp.description}</span></div>
                <div class="detail-row" style="margin-top: 1rem; padding-top: 0.5rem; border-top: 1px dashed var(--border);">
                    <span>Receipt Evidence:</span> 
                    <a href="#" onclick="alert('In real app, this downloads ${exp.receiptId}')" style="color: var(--primary); text-decoration: none;"><i class="fa-solid fa-file-pdf"></i> ${exp.receiptId}</a>
                </div>
            </div>
            <p style="font-size: 0.85rem; color: var(--text-muted);">
                By approving this, the amount will be processed for payroll refund. Do you wish to proceed?
            </p>
        `;

        modal.classList.remove('hidden');

        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        
        const newApprove = btnApprove.cloneNode(true);
        const newReject = btnReject.cloneNode(true);
        btnApprove.parentNode.replaceChild(newApprove, btnApprove);
        btnReject.parentNode.replaceChild(newReject, btnReject);

        // Ensure buttons are visible
        newApprove.style.display = 'block';
        newReject.style.display = 'block';
        
        newApprove.innerText = 'Approve';
        newReject.innerText = 'Reject';

        newApprove.addEventListener('click', () => {
            exp.status = 'approved';
            modal.classList.add('hidden');
            if (document.querySelector('.nav-item.active')?.dataset.view === 'expenses') {
                switchView('expenses');
            }
            showToast(`Expense ${exp.id} successfully approved.`);
        });

        newReject.addEventListener('click', () => {
            exp.status = 'rejected';
            modal.classList.add('hidden');
            if (document.querySelector('.nav-item.active')?.dataset.view === 'expenses') {
                switchView('expenses');
            }
        });
    }

    function openDocumentReader(docId) {
        const doc = store.documents.find(d => d.id === docId);
        if (!doc) return;

        // Change modal header
        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-file-lines text-primary"></i> Document Viewer`;
        
        // This is a plain text area so the AI agent can read it using inner_text
        modalContent.innerHTML = `
            <div style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
                <h4 style="margin-bottom: 0.5rem;">${doc.name}</h4>
                <div style="font-size: 0.8rem; color: var(--text-muted);">Type: ${doc.type} | ID: ${doc.id} | Related: ${doc.relatedTo}</div>
            </div>
            <div id="document-content-area" style="background: #f9fafb; padding: 1rem; border-radius: var(--radius); border: 1px solid var(--border); font-family: monospace; font-size: 0.9rem; line-height: 1.5; white-space: pre-wrap; height: 250px; overflow-y: auto;">${doc.content}</div>
        `;

        modal.classList.remove('hidden');

        // Hide approve/reject buttons, add a close button
        const btnApprove = document.getElementById('btn-approve');
        const btnReject = document.getElementById('btn-reject');
        btnApprove.style.display = 'none';
        btnReject.innerText = 'Close Document';
        
        const newReject = btnReject.cloneNode(true);
        btnReject.parentNode.replaceChild(newReject, btnReject);
        
        newReject.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }

    // A generic modal factory for simple forms
    function openGenericModal(title, htmlContent, approveText, onApprove = null) {
        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-layer-group text-primary"></i> ${title}`;
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
        newReject.innerText = 'Cancel';

        newApprove.addEventListener('click', () => {
            if (onApprove) onApprove();
            modal.classList.add('hidden');
            showToast(`${title} completed successfully.`);
        });

        newReject.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }

    function openTaskModal(tsk) {
        modal.querySelector('.modal-header h3').innerHTML = `<i class="fa-solid fa-clipboard-check text-primary"></i> Task Details`;
        
        modalContent.innerHTML = `
            <div class="approval-details">
                <div class="detail-row"><span>Task ID:</span> <span>${tsk.id}</span></div>
                <div class="detail-row"><span>Title:</span> <strong>${tsk.title}</strong></div>
                <div class="detail-row"><span>Assigned To:</span> <span>${tsk.assignedTo}</span></div>
                <div class="detail-row"><span>Due Date:</span> <span style="color: var(--danger);">${tsk.dueDate}</span></div>
                <div class="detail-row"><span>Priority:</span> <span>${tsk.priority.toUpperCase()}</span></div>
                <div class="detail-row"><span>Status:</span> <span>${tsk.status.replace('_', ' ').toUpperCase()}</span></div>
            </div>
            <div style="margin-top: 1.5rem; border-top: 1px solid var(--border); padding-top: 1rem;">
                <label style="display: block; font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.25rem;">Update Status</label>
                <select id="task-status-update" style="width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px;">
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

        newApprove.innerText = 'Save Task';
        newReject.innerText = 'Cancel';

        newApprove.addEventListener('click', () => {
            tsk.status = document.getElementById('task-status-update').value;
            modal.classList.add('hidden');
            switchView('tasks');
            showToast(`Task ${tsk.id} updated to ${tsk.status.replace('_', ' ')}.`);
        });

        newReject.addEventListener('click', () => {
            modal.classList.add('hidden');
        });
    }

    document.querySelector('.close-modal').addEventListener('click', () => {
        modal.classList.add('hidden');
    });

    function showToast(message) {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed; bottom: 20px; right: 20px;
            background: var(--text-main); color: white;
            padding: 1rem 1.5rem; border-radius: var(--radius);
            box-shadow: var(--shadow-md); font-weight: 500; font-size: 0.9rem;
            z-index: 9999; animation: slideUp 0.3s ease;
        `;
        toast.innerHTML = `<i class="fa-solid fa-check-circle" style="color: var(--success); margin-right: 0.5rem;"></i> ${message}`;
        document.body.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 3000);
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
            
            aiChatHistory.innerHTML += `<div style="padding: 0.5rem; background: #e5e7eb; border-radius: 0.5rem; align-self: flex-end; max-width: 80%;">${task}</div>`;
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
                document.getElementById(loadingId).innerText = "Task submitted! Run ID: " + data.run_id + ". I am processing it in the background!";
            } catch (err) {
                document.getElementById(loadingId).innerText = "Error contacting AI Agent. Make sure the backend on port 8001 is running!";
                document.getElementById(loadingId).style.background = "#fee2e2";
            }
        });
    }

    // Initialize Default View
    switchView('dashboard');
});
