// Scribe Utility Functions

// Toast Notifications
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// HTMX Event Handlers
document.body.addEventListener('htmx:afterSwap', function (event) {
    // Check for toast triggers in response headers
    const trigger = event.detail.xhr.getResponseHeader('HX-Trigger');
    if (trigger) {
        try {
            const parsed = JSON.parse(trigger);
            if (parsed.showToast) {
                showToast(parsed.showToast.message, parsed.showToast.type);
            }
        } catch (e) {
            // Not JSON, ignore
        }
    }
});

// Handle HTMX errors
document.body.addEventListener('htmx:responseError', function (event) {
    const status = event.detail.xhr.status;
    if (status === 401) {
        showToast('Please log in to continue', 'error');
        window.location.href = '/login';
    } else if (status === 404) {
        showToast('Resource not found', 'error');
    } else if (status >= 500) {
        showToast('Server error. Please try again.', 'error');
    }
});

// Format relative time
function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSecs < 60) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

// Format reminder time for future timestamps
function formatReminderTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = date - now;
    
    if (diffMs < 0) return 'overdue'; // Past reminder
    
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffSecs < 60) return 'in moments';
    if (diffMins < 60) return `in ${diffMins}m`;
    if (diffHours < 24) return `in ${diffHours}h`;
    if (diffDays < 7) return `in ${diffDays}d`;
    
    return date.toLocaleDateString();
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Auto-resize textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Initialize auto-resize textareas
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea[data-auto-resize]').forEach(textarea => {
        textarea.addEventListener('input', () => autoResizeTextarea(textarea));
        autoResizeTextarea(textarea);
    });
});

// HTMX after swap - reinitialize components
document.body.addEventListener('htmx:afterSwap', function (event) {
    // Reinitialize auto-resize textareas
    event.detail.target.querySelectorAll('textarea[data-auto-resize]').forEach(textarea => {
        textarea.addEventListener('input', () => autoResizeTextarea(textarea));
        autoResizeTextarea(textarea);
    });
    
    // Initialize reminder times
    event.detail.target.querySelectorAll('.reminder-text[data-reminder]').forEach(element => {
        const reminderTime = element.dataset.reminder;
        if (reminderTime) {
            element.textContent = formatReminderTime(reminderTime);
        }
    });
});

// Initialize reminder times on page load
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.reminder-text[data-reminder]').forEach(element => {
        const reminderTime = element.dataset.reminder;
        if (reminderTime) {
            element.textContent = formatReminderTime(reminderTime);
        }
    });
});


