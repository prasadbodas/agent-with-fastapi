// ============================================
// TOAST NOTIFICATION SYSTEM
// ============================================

class ToastManager {
    constructor() {
        this.container = null;
        this.toasts = [];
        this.init();
    }

    init() {
        // Create toast container
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.setAttribute('aria-live', 'polite');
        this.container.setAttribute('aria-atomic', 'true');
        this.container.style.cssText = `
            position: fixed;
            top: var(--space-4);
            right: var(--space-4);
            z-index: var(--z-toast);
            display: flex;
            flex-direction: column;
            gap: var(--space-2);
            max-width: 400px;
            pointer-events: none;
        `;
        
        // Add to body when DOM is ready
        if (document.body) {
            document.body.appendChild(this.container);
        } else {
            document.addEventListener('DOMContentLoaded', () => {
                document.body.appendChild(this.container);
            });
        }
    }

    /**
     * Show a toast notification
     * @param {string} message - The message to display
     * @param {string} type - Type: 'success', 'error', 'warning', 'info'
     * @param {number} duration - Duration in ms (0 = no auto-dismiss)
     * @param {object} options - Additional options (dismissible, icon, action)
     */
    show(message, type = 'info', duration = 3000, options = {}) {
        const toast = this.createToast(message, type, duration, options);
        this.toasts.push(toast);
        this.container.appendChild(toast.element);

        // Trigger animation
        requestAnimationFrame(() => {
            toast.element.style.opacity = '1';
            toast.element.style.transform = 'translateX(0)';
        });

        // Auto-dismiss if duration > 0
        if (duration > 0) {
            toast.timeout = setTimeout(() => {
                this.dismiss(toast);
            }, duration);
        }

        return toast;
    }

    createToast(message, type, duration, options) {
        const toast = {
            id: Date.now() + Math.random(),
            element: null,
            timeout: null,
            type: type
        };

        // Create toast element
        const element = document.createElement('div');
        element.className = `toast toast-${type}`;
        element.setAttribute('role', 'alert');
        element.setAttribute('aria-live', 'assertive');
        element.style.cssText = `
            background: var(--bg-elevated);
            border: 1px solid var(--border-primary);
            border-radius: var(--radius-lg);
            padding: var(--space-4);
            box-shadow: var(--shadow-xl);
            display: flex;
            align-items: flex-start;
            gap: var(--space-3);
            min-width: 300px;
            max-width: 400px;
            pointer-events: auto;
            opacity: 0;
            transform: translateX(100px);
            transition: all var(--transition-base);
            position: relative;
            overflow: hidden;
        `;

        // Add colored left border
        const colorMap = {
            success: 'var(--color-success)',
            error: 'var(--color-error)',
            warning: 'var(--color-warning)',
            info: 'var(--color-info)'
        };
        element.style.borderLeftWidth = '4px';
        element.style.borderLeftColor = colorMap[type];

        // Icon
        const iconMap = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const iconElement = document.createElement('div');
        iconElement.className = 'toast-icon';
        iconElement.textContent = options.icon || iconMap[type];
        iconElement.style.cssText = `
            font-size: 20px;
            font-weight: bold;
            color: ${colorMap[type]};
            flex-shrink: 0;
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: var(--radius-full);
            background: ${colorMap[type]}15;
        `;
        element.appendChild(iconElement);

        // Content
        const contentElement = document.createElement('div');
        contentElement.className = 'toast-content';
        contentElement.style.cssText = `
            flex: 1;
            color: var(--text-primary);
            font-size: var(--font-size-sm);
            line-height: var(--line-height-normal);
        `;
        contentElement.textContent = message;
        element.appendChild(contentElement);

        // Action button (optional)
        if (options.action) {
            const actionBtn = document.createElement('button');
            actionBtn.className = 'toast-action';
            actionBtn.textContent = options.action.text;
            actionBtn.style.cssText = `
                background: transparent;
                border: none;
                color: var(--color-primary);
                font-weight: var(--font-weight-semibold);
                cursor: pointer;
                padding: var(--space-1) var(--space-2);
                border-radius: var(--radius-sm);
                transition: all var(--transition-fast);
                font-size: var(--font-size-sm);
            `;
            actionBtn.addEventListener('click', () => {
                options.action.onClick();
                this.dismiss(toast);
            });
            actionBtn.addEventListener('mouseenter', () => {
                actionBtn.style.background = 'var(--bg-tertiary)';
            });
            actionBtn.addEventListener('mouseleave', () => {
                actionBtn.style.background = 'transparent';
            });
            contentElement.appendChild(actionBtn);
        }

        // Close button (if dismissible or no duration)
        if (options.dismissible !== false || duration === 0) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'toast-close';
            closeBtn.innerHTML = '×';
            closeBtn.setAttribute('aria-label', 'Close notification');
            closeBtn.style.cssText = `
                background: transparent;
                border: none;
                color: var(--text-secondary);
                font-size: 24px;
                line-height: 1;
                cursor: pointer;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: var(--radius-sm);
                transition: all var(--transition-fast);
                flex-shrink: 0;
            `;
            closeBtn.addEventListener('click', () => {
                this.dismiss(toast);
            });
            closeBtn.addEventListener('mouseenter', () => {
                closeBtn.style.background = 'var(--bg-tertiary)';
                closeBtn.style.color = 'var(--text-primary)';
            });
            closeBtn.addEventListener('mouseleave', () => {
                closeBtn.style.background = 'transparent';
                closeBtn.style.color = 'var(--text-secondary)';
            });
            element.appendChild(closeBtn);
        }

        // Progress bar (if has duration)
        if (duration > 0) {
            const progressBar = document.createElement('div');
            progressBar.className = 'toast-progress';
            progressBar.style.cssText = `
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background: ${colorMap[type]};
                width: 100%;
                transform-origin: left;
                animation: toast-progress ${duration}ms linear forwards;
            `;
            element.appendChild(progressBar);

            // Add animation keyframes if not exists
            if (!document.getElementById('toast-animations')) {
                const style = document.createElement('style');
                style.id = 'toast-animations';
                style.textContent = `
                    @keyframes toast-progress {
                        from { transform: scaleX(1); }
                        to { transform: scaleX(0); }
                    }
                `;
                document.head.appendChild(style);
            }
        }

        toast.element = element;
        return toast;
    }

    dismiss(toast) {
        if (!toast || !toast.element) return;

        // Clear timeout
        if (toast.timeout) {
            clearTimeout(toast.timeout);
        }

        // Animate out
        toast.element.style.opacity = '0';
        toast.element.style.transform = 'translateX(100px)';

        // Remove after animation
        setTimeout(() => {
            if (toast.element && toast.element.parentNode) {
                toast.element.parentNode.removeChild(toast.element);
            }
            this.toasts = this.toasts.filter(t => t.id !== toast.id);
        }, 300);
    }

    /**
     * Dismiss all toasts
     */
    dismissAll() {
        this.toasts.forEach(toast => this.dismiss(toast));
    }

    /**
     * Shorthand methods
     */
    success(message, duration = 3000, options = {}) {
        return this.show(message, 'success', duration, options);
    }

    error(message, duration = 5000, options = {}) {
        return this.show(message, 'error', duration, options);
    }

    warning(message, duration = 4000, options = {}) {
        return this.show(message, 'warning', duration, options);
    }

    info(message, duration = 3000, options = {}) {
        return this.show(message, 'info', duration, options);
    }
}

// Create global instance
const toast = new ToastManager();

// Export for use in other scripts
if (typeof window !== 'undefined') {
    window.toast = toast;
    window.ToastManager = ToastManager;
}
