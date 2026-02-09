// ============================================
// LOADING STATES & SKELETON SCREENS
// ============================================

/**
 * Add loading spinner to a button
 */
function addButtonLoading(button, loadingText = 'Loading...') {
    if (!button || button.dataset.loading === 'true') return;
    
    // Store original content
    button.dataset.originalContent = button.innerHTML;
    button.dataset.loading = 'true';
    button.disabled = true;
    
    // Add spinner
    button.innerHTML = `
        <span style="display: flex; align-items: center; gap: var(--space-2); justify-content: center;">
            <span class="spinner"></span>
            <span>${loadingText}</span>
        </span>
    `;
}

/**
 * Remove loading spinner from button
 */
function removeButtonLoading(button) {
    if (!button || button.dataset.loading !== 'true') return;
    
    button.innerHTML = button.dataset.originalContent || button.innerHTML;
    button.disabled = false;
    button.dataset.loading = 'false';
    delete button.dataset.originalContent;
}

/**
 * Create a skeleton loader element
 */
function createSkeleton(type = 'text', options = {}) {
    const skeleton = document.createElement('div');
    skeleton.className = 'skeleton';
    skeleton.setAttribute('aria-busy', 'true');
    skeleton.setAttribute('aria-label', 'Loading...');
    
    const styles = {
        text: {
            width: options.width || '100%',
            height: options.height || '16px',
            borderRadius: 'var(--radius-sm)'
        },
        title: {
            width: options.width || '60%',
            height: options.height || '24px',
            borderRadius: 'var(--radius-sm)'
        },
        avatar: {
            width: options.size || '40px',
            height: options.size || '40px',
            borderRadius: 'var(--radius-full)'
        },
        card: {
            width: options.width || '100%',
            height: options.height || '120px',
            borderRadius: 'var(--radius-lg)'
        },
        circle: {
            width: options.size || '40px',
            height: options.size || '40px',
            borderRadius: 'var(--radius-full)'
        },
        rectangle: {
            width: options.width || '100%',
            height: options.height || '100px',
            borderRadius: 'var(--radius-md)'
        }
    };
    
    const style = styles[type] || styles.text;
    Object.assign(skeleton.style, style);
    
    return skeleton;
}

/**
 * Create a chat message skeleton
 */
function createMessageSkeleton(isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-msg skeleton-message ${isUser ? 'user-msg' : 'agent-msg'}`;
    messageDiv.style.cssText = `
        margin-bottom: var(--space-4);
        padding: var(--space-4) var(--space-5);
        border-radius: var(--radius-xl);
        max-width: 75%;
        ${isUser ? 'margin-left: auto;' : 'margin-right: auto;'}
        display: flex;
        flex-direction: column;
        gap: var(--space-2);
    `;
    
    // Add skeleton lines
    const lines = isUser ? 1 : 2;
    for (let i = 0; i < lines; i++) {
        const skeleton = createSkeleton('text', {
            width: i === lines - 1 ? '80%' : '100%'
        });
        messageDiv.appendChild(skeleton);
    }
    
    return messageDiv;
}

/**
 * Show loading state in chat
 */
function showChatLoading() {
    const chatBox = document.getElementById('chat-box');
    if (!chatBox) return;
    
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'chat-loading';
    loadingDiv.appendChild(createMessageSkeleton(false));
    
    chatBox.appendChild(loadingDiv);
    
    // Auto-scroll to show loading
    chatBox.scrollTop = chatBox.scrollHeight;
}

/**
 * Hide loading state in chat
 */
function hideChatLoading() {
    const loadingDiv = document.getElementById('chat-loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

/**
 * Create a list skeleton
 */
function createListSkeleton(count = 3) {
    const container = document.createElement('div');
    container.className = 'skeleton-list';
    
    for (let i = 0; i < count; i++) {
        const item = document.createElement('div');
        item.style.cssText = `
            display: flex;
            align-items: center;
            gap: var(--space-3);
            padding: var(--space-3);
            border-bottom: 1px solid var(--border-primary);
        `;
        
        // Icon/Avatar
        item.appendChild(createSkeleton('circle', { size: '32px' }));
        
        // Content
        const content = document.createElement('div');
        content.style.cssText = 'flex: 1; display: flex; flex-direction: column; gap: var(--space-2);';
        content.appendChild(createSkeleton('title', { width: '60%' }));
        content.appendChild(createSkeleton('text', { width: '80%' }));
        item.appendChild(content);
        
        container.appendChild(item);
    }
    
    return container;
}

/**
 * Show loading overlay
 */
function showLoadingOverlay(message = 'Loading...') {
    let overlay = document.getElementById('loading-overlay');
    
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: var(--bg-overlay);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: var(--space-4);
            z-index: var(--z-modal);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        `;
        
        const spinnerContainer = document.createElement('div');
        spinnerContainer.style.cssText = `
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--space-3);
            background: var(--bg-elevated);
            padding: var(--space-8);
            border-radius: var(--radius-xl);
            box-shadow: var(--shadow-2xl);
        `;
        
        const spinner = document.createElement('div');
        spinner.style.cssText = `
            width: 48px;
            height: 48px;
            border: 4px solid var(--border-primary);
            border-top-color: var(--color-primary);
            border-radius: var(--radius-full);
            animation: spin 0.8s linear infinite;
        `;
        
        const text = document.createElement('div');
        text.id = 'loading-overlay-text';
        text.textContent = message;
        text.style.cssText = `
            color: var(--text-primary);
            font-size: var(--font-size-base);
            font-weight: var(--font-weight-medium);
        `;
        
        spinnerContainer.appendChild(spinner);
        spinnerContainer.appendChild(text);
        overlay.appendChild(spinnerContainer);
        document.body.appendChild(overlay);
    } else {
        overlay.style.display = 'flex';
        const text = document.getElementById('loading-overlay-text');
        if (text) text.textContent = message;
    }
    
    return overlay;
}

/**
 * Hide loading overlay
 */
function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.style.display = 'none';
    }
}

/**
 * Progress bar component
 */
class ProgressBar {
    constructor(options = {}) {
        this.container = options.container || document.body;
        this.color = options.color || 'var(--color-primary)';
        this.height = options.height || '3px';
        this.element = null;
        this.value = 0;
        this.init();
    }
    
    init() {
        this.element = document.createElement('div');
        this.element.className = 'progress-bar-container';
        this.element.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: ${this.height};
            background: var(--bg-tertiary);
            z-index: var(--z-fixed);
            overflow: hidden;
        `;
        
        this.bar = document.createElement('div');
        this.bar.className = 'progress-bar';
        this.bar.style.cssText = `
            height: 100%;
            background: ${this.color};
            width: 0%;
            transition: width 0.3s ease;
        `;
        
        this.element.appendChild(this.bar);
    }
    
    show() {
        if (!this.element.parentNode) {
            document.body.appendChild(this.element);
        }
        return this;
    }
    
    hide() {
        if (this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        return this;
    }
    
    set(value) {
        this.value = Math.max(0, Math.min(100, value));
        this.bar.style.width = `${this.value}%`;
        return this;
    }
    
    increment(amount = 10) {
        return this.set(this.value + amount);
    }
    
    complete() {
        this.set(100);
        setTimeout(() => this.hide(), 300);
        return this;
    }
}

/**
 * Indeterminate progress bar (for unknown duration)
 */
function showIndeterminateProgress() {
    let bar = document.getElementById('indeterminate-progress');
    
    if (!bar) {
        bar = document.createElement('div');
        bar.id = 'indeterminate-progress';
        bar.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: var(--bg-tertiary);
            z-index: var(--z-fixed);
            overflow: hidden;
        `;
        
        const progress = document.createElement('div');
        progress.style.cssText = `
            height: 100%;
            background: var(--color-primary);
            width: 30%;
            animation: indeterminate-progress 1.5s ease-in-out infinite;
        `;
        
        bar.appendChild(progress);
        
        // Add animation if not exists
        if (!document.getElementById('indeterminate-animation')) {
            const style = document.createElement('style');
            style.id = 'indeterminate-animation';
            style.textContent = `
                @keyframes indeterminate-progress {
                    0% { transform: translateX(-100%); }
                    50% { transform: translateX(400%); }
                    100% { transform: translateX(-100%); }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(bar);
    }
    
    return bar;
}

/**
 * Hide indeterminate progress
 */
function hideIndeterminateProgress() {
    const bar = document.getElementById('indeterminate-progress');
    if (bar) {
        bar.remove();
    }
}

// Export functions
if (typeof window !== 'undefined') {
    window.addButtonLoading = addButtonLoading;
    window.removeButtonLoading = removeButtonLoading;
    window.createSkeleton = createSkeleton;
    window.createMessageSkeleton = createMessageSkeleton;
    window.showChatLoading = showChatLoading;
    window.hideChatLoading = hideChatLoading;
    window.createListSkeleton = createListSkeleton;
    window.showLoadingOverlay = showLoadingOverlay;
    window.hideLoadingOverlay = hideLoadingOverlay;
    window.ProgressBar = ProgressBar;
    window.showIndeterminateProgress = showIndeterminateProgress;
    window.hideIndeterminateProgress = hideIndeterminateProgress;
}
