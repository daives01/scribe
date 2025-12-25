// Scribe Utility Functions

// Generate consistent color for tags based on their value
function getTagColor(tag) {
    const colors = [
        { bg: 'bg-rose-100', text: 'text-rose-700', darkBg: 'dark:bg-rose-900/30', darkText: 'dark:text-rose-400' },
        { bg: 'bg-orange-100', text: 'text-orange-700', darkBg: 'dark:bg-orange-900/30', darkText: 'dark:text-orange-400' },
        { bg: 'bg-amber-100', text: 'text-amber-700', darkBg: 'dark:bg-amber-900/30', darkText: 'dark:text-amber-400' },
        { bg: 'bg-yellow-100', text: 'text-yellow-700', darkBg: 'dark:bg-yellow-900/30', darkText: 'dark:text-yellow-400' },
        { bg: 'bg-lime-100', text: 'text-lime-700', darkBg: 'dark:bg-lime-900/30', darkText: 'dark:text-lime-400' },
        { bg: 'bg-green-100', text: 'text-green-700', darkBg: 'dark:bg-green-900/30', darkText: 'dark:text-green-400' },
        { bg: 'bg-emerald-100', text: 'text-emerald-700', darkBg: 'dark:bg-emerald-900/30', darkText: 'dark:text-emerald-400' },
        { bg: 'bg-teal-100', text: 'text-teal-700', darkBg: 'dark:bg-teal-900/30', darkText: 'dark:text-teal-400' },
        { bg: 'bg-cyan-100', text: 'text-cyan-700', darkBg: 'dark:bg-cyan-900/30', darkText: 'dark:text-cyan-400' },
        { bg: 'bg-sky-100', text: 'text-sky-700', darkBg: 'dark:bg-sky-900/30', darkText: 'dark:text-sky-400' },
        { bg: 'bg-blue-100', text: 'text-blue-700', darkBg: 'dark:bg-blue-900/30', darkText: 'dark:text-blue-400' },
        { bg: 'bg-indigo-100', text: 'text-indigo-700', darkBg: 'dark:bg-indigo-900/30', darkText: 'dark:text-indigo-400' },
        { bg: 'bg-violet-100', text: 'text-violet-700', darkBg: 'dark:bg-violet-900/30', darkText: 'dark:text-violet-400' },
        { bg: 'bg-purple-100', text: 'text-purple-700', darkBg: 'dark:bg-purple-900/30', darkText: 'dark:text-purple-400' },
        { bg: 'bg-fuchsia-100', text: 'text-fuchsia-700', darkBg: 'dark:bg-fuchsia-900/30', darkText: 'dark:text-fuchsia-400' },
        { bg: 'bg-pink-100', text: 'text-pink-700', darkBg: 'dark:bg-pink-900/30', darkText: 'dark:text-pink-400' },
    ];

    let hash = 0;
    for (let i = 0; i < tag.length; i++) {
        hash = ((hash << 5) - hash) + tag.charCodeAt(i);
        hash = hash & hash;
    }

    const index = Math.abs(hash) % colors.length;
    return colors[index];
}

// Apply colors to tag badges
function initializeTagBadges(container = document) {
    container.querySelectorAll('.tag-badge[data-tag]').forEach(badge => {
        const tag = badge.dataset.tag;
        const colors = getTagColor(tag);
        badge.classList.add(colors.bg, colors.text, colors.darkBg, colors.darkText);
    });
}

// Initialize tag badges on page load and HTMX updates
initializeTagBadges();

// Handle Enter key for note creation
document.addEventListener('DOMContentLoaded', function() {
    const noteInput = document.getElementById('note-input');
    const noteForm = document.getElementById('note-form');

    if (noteInput && noteForm) {
        noteInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                const text = noteInput.value.trim();
                if (text) {
                    noteForm.requestSubmit();
                    noteInput.value = '';
                }
            }
        });
    }
});

// Close search results when clicking outside
document.addEventListener('click', function(event) {
    const searchContainer = document.getElementById('search-container');
    const searchResults = document.getElementById('search-results');

    if (searchContainer && searchResults &&
        !searchContainer.contains(event.target)) {
        searchResults.innerHTML = '';
    }
});

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

// HTMX Event Handlers (wrapped to ensure DOM is ready)
document.addEventListener('DOMContentLoaded', function() {
    if (document.body) {
        document.body.addEventListener('htmx:toast', function (event) {
            const { message, type } = event.detail;
            showToast(message, type || 'success');
        });

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
                }
            }

            // Reinitialize tag badges in swapped content
            initializeTagBadges(event.detail.target);

            // Reinitialize auto-resize textareas
            event.detail.target.querySelectorAll('textarea[data-auto-resize]').forEach(textarea => {
                textarea.addEventListener('input', () => autoResizeTextarea(textarea));
                autoResizeTextarea(textarea);
            });

            // Reinitialize reminders in swapped content
            initializeReminders(event.detail.target);
        });

        document.body.addEventListener('htmx:afterSettle', function(event) {
            const target = event.detail.target;
            if (target && target.nodeType === 1) {
                initializeTagBadges(target);
            }
        });

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
    if (isNaN(date.getTime())) return null;

    const now = new Date();
    const diffMs = date - now;

    if (diffMs < 0) return null;

    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'soon';
    if (diffMins < 60) return `in ${diffMins}m`;
    if (diffHours < 24) return `in ${diffHours}h`;
    if (diffDays < 7) return `in ${diffDays}d`;

    return date.toLocaleDateString();
}

// Make formatReminderTime available globally for Alpine components
window.formatReminderTime = formatReminderTime;

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

// Initialize reminder badges
function initializeReminders(container = document) {
    const reminders = container.querySelectorAll('.reminder-text[data-reminder]');
    reminders.forEach(element => {
        const reminderTime = element.dataset.reminder;
        if (!reminderTime) return;

        const formatted = formatReminderTime(reminderTime);
        if (formatted) {
            element.textContent = formatted;
        } else {
            const badge = element.closest('.reminder-badge');
            if (badge) {
                badge.remove();
            }
        }
    });
}

// Initialize reminders on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeReminders(document);

    // Update reminder times every minute
    setInterval(function() {
        document.querySelectorAll('.reminder-text[data-reminder]').forEach(element => {
            const reminderTime = element.dataset.reminder;
            const formatted = formatReminderTime(reminderTime);
            if (formatted) {
                element.textContent = formatted;
            } else {
                const badge = element.closest('.reminder-badge');
                if (badge) {
                    badge.remove();
                }
            }
        });
    }, 60000);
});

// Auto-resize textarea
function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

// Initialize auto-resize textareas on page load
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea[data-auto-resize]').forEach(textarea => {
        textarea.addEventListener('input', () => autoResizeTextarea(textarea));
        autoResizeTextarea(textarea);
    });
});
