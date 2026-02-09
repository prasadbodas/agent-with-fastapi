// ============================================
// MESSAGE ENHANCEMENTS - Copy, Actions, etc.
// ============================================

/**
 * Add action buttons to a message element
 */
function addMessageActions(messageDiv, messageText, sender) {
    // Only add actions to agent messages for now
    if (sender !== 'agent') return;
    
    const actionsContainer = document.createElement('div');
    actionsContainer.className = 'message-actions';
    actionsContainer.style.cssText = `
        display: flex;
        gap: var(--space-2);
        margin-top: var(--space-2);
        padding-top: var(--space-2);
        border-top: 1px solid var(--border-primary);
        opacity: 0.7;
    `;
    
    // Copy button
    const copyBtn = createActionButton('📋', 'Copy', () => {
        copyToClipboard(messageText);
    });
    
    actionsContainer.appendChild(copyBtn);
    messageDiv.appendChild(actionsContainer);
}

/**
 * Create an action button
 */
function createActionButton(icon, title, onClick) {
    const button = document.createElement('button');
    button.className = 'btn-action';
    button.title = title;
    button.setAttribute('aria-label', title);
    button.innerHTML = `<span style="font-size: 14px;">${icon}</span>`;
    button.style.cssText = `
        background: transparent;
        border: 1px solid var(--border-primary);
        border-radius: var(--radius-sm);
        padding: var(--space-1) var(--space-2);
        cursor: pointer;
        transition: all var(--transition-fast);
        color: var(--text-secondary);
        font-size: var(--font-size-sm);
    `;
    
    button.addEventListener('mouseenter', () => {
        button.style.background = 'var(--bg-tertiary)';
        button.style.borderColor = 'var(--border-secondary)';
        button.style.transform = 'translateY(-1px)';
    });
    
    button.addEventListener('mouseleave', () => {
        button.style.background = 'transparent';
        button.style.borderColor = 'var(--border-primary)';
        button.style.transform = 'translateY(0)';
    });
    
    button.addEventListener('click', (e) => {
        e.stopPropagation();
        onClick();
    });
    
    return button;
}

/**
 * Copy text to clipboard with feedback
 */
function copyToClipboard(text) {
    // Remove markdown formatting for cleaner copy
    const cleanText = text.replace(/[*_`]/g, '');
    
    navigator.clipboard.writeText(cleanText).then(() => {
        showNotification('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showNotification('Failed to copy', 'error');
    });
}

/**
 * Add copy button to code blocks
 */
function addCodeCopyButtons() {
    const codeBlocks = document.querySelectorAll('.chat-msg pre');
    
    codeBlocks.forEach(block => {
        // Skip if copy button already exists
        if (block.querySelector('.code-copy-btn')) return;
        
        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'code-copy-btn';
        copyBtn.innerHTML = '📋 Copy';
        copyBtn.title = 'Copy code';
        copyBtn.setAttribute('aria-label', 'Copy code to clipboard');
        copyBtn.style.cssText = `
            position: absolute;
            top: var(--space-2);
            right: var(--space-2);
            background: var(--bg-elevated);
            border: 1px solid var(--border-primary);
            border-radius: var(--radius-sm);
            padding: var(--space-1) var(--space-2);
            cursor: pointer;
            font-size: var(--font-size-xs);
            color: var(--text-secondary);
            transition: all var(--transition-fast);
            opacity: 0;
        `;
        
        // Show button on hover
        wrapper.addEventListener('mouseenter', () => {
            copyBtn.style.opacity = '1';
        });
        
        wrapper.addEventListener('mouseleave', () => {
            copyBtn.style.opacity = '0';
        });
        
        copyBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const code = block.textContent;
            navigator.clipboard.writeText(code).then(() => {
                copyBtn.innerHTML = '✓ Copied!';
                copyBtn.style.background = 'var(--color-success-light)';
                copyBtn.style.color = 'var(--color-success)';
                
                setTimeout(() => {
                    copyBtn.innerHTML = '📋 Copy';
                    copyBtn.style.background = 'var(--bg-elevated)';
                    copyBtn.style.color = 'var(--text-secondary)';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy code:', err);
                showNotification('Failed to copy code', 'error');
            });
        });
        
        // Wrap the code block
        block.parentNode.insertBefore(wrapper, block);
        wrapper.appendChild(block);
        wrapper.appendChild(copyBtn);
    });
}

/**
 * Scroll to bottom button
 */
function createScrollToBottomButton() {
    const chatLog = document.getElementById('chat-box');
    if (!chatLog) return;
    
    const scrollBtn = document.createElement('button');
    scrollBtn.id = 'scroll-to-bottom';
    scrollBtn.className = 'scroll-to-bottom-btn';
    scrollBtn.innerHTML = '↓';
    scrollBtn.title = 'Scroll to bottom';
    scrollBtn.setAttribute('aria-label', 'Scroll to bottom of chat');
    scrollBtn.style.cssText = `
        position: absolute;
        bottom: calc(100% + var(--space-2));
        right: var(--space-4);
        width: 40px;
        height: 40px;
        background: var(--color-primary);
        color: var(--text-inverse);
        border: none;
        border-radius: var(--radius-full);
        box-shadow: var(--shadow-lg);
        cursor: pointer;
        font-size: 20px;
        display: none;
        align-items: center;
        justify-content: center;
        transition: all var(--transition-fast);
        z-index: var(--z-sticky);
    `;
    
    scrollBtn.addEventListener('click', () => {
        chatLog.scrollTo({
            top: chatLog.scrollHeight,
            behavior: 'smooth'
        });
    });
    
    scrollBtn.addEventListener('mouseenter', () => {
        scrollBtn.style.transform = 'scale(1.1)';
    });
    
    scrollBtn.addEventListener('mouseleave', () => {
        scrollBtn.style.transform = 'scale(1)';
    });
    
    // Show/hide button based on scroll position
    chatLog.addEventListener('scroll', () => {
        const isNearBottom = chatLog.scrollHeight - chatLog.clientHeight - chatLog.scrollTop < 100;
        scrollBtn.style.display = isNearBottom ? 'none' : 'flex';
    });
    
    // Insert button before chat input
    const chatInput = document.getElementById('chat-input');
    if (chatInput && chatInput.parentNode) {
        chatInput.parentNode.insertBefore(scrollBtn, chatInput);
    }
}

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

/**
 * Initialize keyboard shortcuts
 */
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + K: Focus search (if available) or input
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const input = document.getElementById('user-input');
            if (input) input.focus();
        }
        
        // Escape: Clear input
        if (e.key === 'Escape') {
            const input = document.getElementById('user-input');
            if (input && document.activeElement === input) {
                input.value = '';
            }
        }
    });
}

// Export functions to be called from main app.js
if (typeof window !== 'undefined') {
    window.addMessageActions = addMessageActions;
    window.addCodeCopyButtons = addCodeCopyButtons;
    window.createScrollToBottomButton = createScrollToBottomButton;
    window.initKeyboardShortcuts = initKeyboardShortcuts;
}
