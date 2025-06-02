// Main JavaScript functionality for GitHub Backup Manager

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize auto-refresh for running jobs
    initializeAutoRefresh();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize confirmation dialogs
    initializeConfirmations();
    
    // Initialize clipboard functionality
    initializeClipboard();
});

// Initialize Bootstrap tooltips
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Auto-refresh functionality for pages with running jobs
function initializeAutoRefresh() {
    const runningJobs = document.querySelectorAll('.badge');
    let hasRunningJobs = false;
    
    // Check if any badge contains "Running" text
    runningJobs.forEach(badge => {
        if (badge.textContent.includes('Running')) {
            hasRunningJobs = true;
        }
    });
    
    // Also check for data attribute
    hasRunningJobs = hasRunningJobs || document.querySelector('[data-status="running"]') !== null;
    
    if (hasRunningJobs || window.location.pathname.includes('/status') || window.location.pathname === '/') {
        // Refresh every 10 seconds if there are running jobs or on dashboard/status pages
        const refreshInterval = setInterval(function() {
            const currentPath = window.location.pathname;
            if (currentPath === '/status' || currentPath === '/') {
                // Only auto-refresh if user hasn't interacted recently
                if (document.hidden === false && 
                    (Date.now() - getLastUserInteraction()) > 8000) {
                    
                    // Check if we still have running jobs before refreshing
                    const currentlyRunning = Array.from(document.querySelectorAll('.badge')).some(badge => 
                        badge.textContent.includes('Running'));
                    
                    if (currentlyRunning || currentPath === '/status') {
                        location.reload();
                    } else if (currentPath === '/') {
                        // On dashboard, refresh once more to clear running status then stop
                        location.reload();
                        clearInterval(refreshInterval);
                    }
                }
            }
        }, 10000);
    }
}

// Track last user interaction for smart auto-refresh
let lastUserInteraction = Date.now();
function getLastUserInteraction() {
    return lastUserInteraction;
}

// Track user interactions
['click', 'keypress', 'scroll', 'mousemove'].forEach(event => {
    document.addEventListener(event, function() {
        lastUserInteraction = Date.now();
    }, { passive: true });
});

// Form validation enhancements
function initializeFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            
            form.classList.add('was-validated');
        });
    });
    
    // GitHub token validation and auto-save
    const githubTokenField = document.getElementById('github_token');
    if (githubTokenField) {
        let saveTimeout;
        
        githubTokenField.addEventListener('input', function() {
            validateGitHubToken(this.value);
            
            // Auto-save when token looks valid
            clearTimeout(saveTimeout);
            const token = this.value.trim();
            
            if (token && isValidGitHubTokenFormat(token)) {
                saveTimeout = setTimeout(() => {
                    autoSaveConfiguration();
                }, 2000); // Wait 2 seconds after user stops typing
            }
        });
    }
    
    // Cron expression validation
    const cronField = document.getElementById('schedule_cron');
    if (cronField) {
        cronField.addEventListener('input', function() {
            validateCronExpression(this.value);
        });
    }
}

// Check if token has valid GitHub format
function isValidGitHubTokenFormat(token) {
    const tokenPattern = /^gh[ps]_[A-Za-z0-9_]{36,255}$/;
    const classicPattern = /^[a-f0-9]{40}$/;
    return tokenPattern.test(token) || classicPattern.test(token);
}

// Validate GitHub token format
function validateGitHubToken(token) {
    const githubTokenField = document.getElementById('github_token');
    const feedback = githubTokenField.parentNode.querySelector('.invalid-feedback') || 
                    createFeedbackElement(githubTokenField.parentNode);
    
    if (!token) {
        setFieldValidation(githubTokenField, feedback, false, 'GitHub token is required');
        return false;
    }
    
    // Check basic GitHub token format
    const tokenPattern = /^gh[pousr]_[A-Za-z0-9_]{36,255}$/;
    const legacyPattern = /^[a-f0-9]{40}$/i;
    
    if (isValidGitHubTokenFormat(token)) {
        setFieldValidation(githubTokenField, feedback, true, 'Token format looks valid');
        return true;
    } else {
        setFieldValidation(githubTokenField, feedback, false, 'Invalid GitHub token format');
        return false;
    }
}

// Auto-save configuration when token is valid
function autoSaveConfiguration() {
    const configForm = document.getElementById('config-form');
    if (!configForm) return;
    
    const saveBtn = configForm.querySelector('button[type="submit"]');
    const originalText = saveBtn.textContent;
    
    // Show saving indicator
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Auto-saving...';
    saveBtn.disabled = true;
    
    // Submit form
    const formData = new FormData(configForm);
    fetch(configForm.action || '/config', {
        method: 'POST',
        body: formData
    })
    .then(response => response.text())
    .then(html => {
        // Check if save was successful by looking for success flash message
        if (html.includes('alert-success') || html.includes('Configuration saved')) {
            showNotification('Configuration saved and repositories synced!', 'success');
            // Refresh repositories count if on dashboard
            if (window.location.pathname === '/') {
                setTimeout(() => window.location.reload(), 1000);
            }
        } else if (html.includes('alert-danger') || html.includes('Invalid GitHub token')) {
            showNotification('Invalid GitHub token. Please check your token.', 'error');
        }
    })
    .catch(error => {
        console.error('Auto-save failed:', error);
        showNotification('Auto-save failed. Please try saving manually.', 'error');
    })
    .finally(() => {
        saveBtn.textContent = originalText;
        saveBtn.disabled = false;
    });
}

// Validate cron expression
function validateCronExpression(cron) {
    const cronField = document.getElementById('schedule_cron');
    const feedback = cronField.parentNode.querySelector('.invalid-feedback') || 
                    createFeedbackElement(cronField.parentNode);
    
    if (!cron) {
        setFieldValidation(cronField, feedback, false, 'Cron expression is required when scheduling is enabled');
        return false;
    }
    
    const cronParts = cron.trim().split(/\s+/);
    if (cronParts.length !== 5) {
        setFieldValidation(cronField, feedback, false, 'Cron expression must have 5 parts: minute hour day month day_of_week');
        return false;
    }
    
    // Basic validation for each part
    const ranges = [
        { min: 0, max: 59, name: 'minute' },      // minute
        { min: 0, max: 23, name: 'hour' },        // hour  
        { min: 1, max: 31, name: 'day' },         // day
        { min: 1, max: 12, name: 'month' },       // month
        { min: 0, max: 7, name: 'day_of_week' }   // day of week (0 and 7 = Sunday)
    ];
    
    for (let i = 0; i < cronParts.length; i++) {
        const part = cronParts[i];
        const range = ranges[i];
        
        if (part === '*' || part === '*/1') continue;
        
        // Check step values (*/n)
        if (part.startsWith('*/')) {
            const step = parseInt(part.substring(2));
            if (isNaN(step) || step <= 0) {
                setFieldValidation(cronField, feedback, false, `Invalid step value in ${range.name}: ${part}`);
                return false;
            }
            continue;
        }
        
        // Check ranges (n-m)
        if (part.includes('-')) {
            const rangeParts = part.split('-');
            if (rangeParts.length !== 2) {
                setFieldValidation(cronField, feedback, false, `Invalid range in ${range.name}: ${part}`);
                return false;
            }
            const start = parseInt(rangeParts[0]);
            const end = parseInt(rangeParts[1]);
            if (isNaN(start) || isNaN(end) || start > end || 
                start < range.min || end > range.max) {
                setFieldValidation(cronField, feedback, false, `Invalid range in ${range.name}: ${part}`);
                return false;
            }
            continue;
        }
        
        // Check lists (n,m,o)
        if (part.includes(',')) {
            const listParts = part.split(',');
            for (const listPart of listParts) {
                const num = parseInt(listPart);
                if (isNaN(num) || num < range.min || num > range.max) {
                    setFieldValidation(cronField, feedback, false, `Invalid value in ${range.name}: ${listPart}`);
                    return false;
                }
            }
            continue;
        }
        
        // Check single numbers
        const num = parseInt(part);
        if (isNaN(num) || num < range.min || num > range.max) {
            setFieldValidation(cronField, feedback, false, `Invalid value in ${range.name}: ${part} (must be ${range.min}-${range.max})`);
            return false;
        }
    }
    
    setFieldValidation(cronField, feedback, true, 'Valid cron expression');
    return true;
}

// Helper function to set field validation state
function setFieldValidation(field, feedback, isValid, message) {
    if (isValid) {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        feedback.className = 'valid-feedback';
        feedback.textContent = message;
    } else {
        field.classList.remove('is-valid');
        field.classList.add('is-invalid');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
    }
}

// Helper function to create feedback element
function createFeedbackElement(parent) {
    const feedback = document.createElement('div');
    feedback.className = 'invalid-feedback';
    parent.appendChild(feedback);
    return feedback;
}

// Initialize confirmation dialogs
function initializeConfirmations() {
    // Backup deletion confirmations - remove confirm dialogs, just process directly
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            // Show loading state
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Deleting...';
            this.disabled = true;
        });
    });
    
    // Backup now - remove confirmation dialog
    const backupButtons = document.querySelectorAll('form[action*="backup-now"] button[type="submit"]');
    backupButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const form = this.closest('form');
            // Show loading state immediately
            this.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Starting...';
            this.disabled = true;
            setTimeout(() => form.submit(), 500);
        });
    });
}

// Initialize clipboard functionality
function initializeClipboard() {
    // Add copy buttons to code blocks
    const codeBlocks = document.querySelectorAll('code, pre');
    codeBlocks.forEach(block => {
        if (block.textContent.length > 10) {
            addCopyButton(block);
        }
    });
}

// Add copy button to element
function addCopyButton(element) {
    const wrapper = document.createElement('div');
    wrapper.style.position = 'relative';
    wrapper.style.display = 'inline-block';
    
    const button = document.createElement('button');
    button.className = 'btn btn-outline-secondary btn-sm';
    button.style.position = 'absolute';
    button.style.top = '5px';
    button.style.right = '5px';
    button.style.fontSize = '0.75rem';
    button.innerHTML = '<i class="fas fa-copy"></i>';
    
    button.addEventListener('click', function() {
        copyToClipboard(element.textContent);
        button.innerHTML = '<i class="fas fa-check text-success"></i>';
        setTimeout(() => {
            button.innerHTML = '<i class="fas fa-copy"></i>';
        }, 2000);
    });
    
    element.parentNode.insertBefore(wrapper, element);
    wrapper.appendChild(element);
    wrapper.appendChild(button);
}

// Copy text to clipboard
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text);
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
    }
}

// Show loading state for buttons
function showButtonLoading(button, loadingText = 'Loading...') {
    const originalHTML = button.innerHTML;
    button.innerHTML = `<i class="fas fa-spinner fa-spin me-1"></i>${loadingText}`;
    button.disabled = true;
    
    return function() {
        button.innerHTML = originalHTML;
        button.disabled = false;
    };
}

// Format file sizes
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
}

// Format dates relative to now
function formatRelativeTime(date) {
    const now = new Date();
    const diff = now - date;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    return 'Just now';
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Handle network errors gracefully
window.addEventListener('online', function() {
    showNotification('Connection restored', 'success');
});

window.addEventListener('offline', function() {
    showNotification('Connection lost - some features may not work', 'warning');
});

// Progressive enhancement for forms
function enhanceForm(form) {
    // Add loading states to submit buttons
    const submitButton = form.querySelector('button[type="submit"]');
    if (submitButton) {
        form.addEventListener('submit', function() {
            showButtonLoading(submitButton);
        });
    }
    
    // Add real-time validation
    const inputs = form.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.checkValidity()) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-valid');
                this.classList.add('is-invalid');
            }
        });
    });
}

// Initialize enhanced forms
document.querySelectorAll('form').forEach(enhanceForm);

// Utility function to debounce function calls
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

// Export functions for external use
window.GitHubBackupManager = {
    showNotification,
    formatFileSize,
    formatRelativeTime,
    copyToClipboard,
    showButtonLoading,
    debounce
};
