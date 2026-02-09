// ============================================
// EMPTY STATE COMPONENTS
// ============================================

/**
 * Create an empty state component
 */
function createEmptyState(options = {}) {
    const {
        icon = '📭',
        title = 'No items yet',
        description = 'Get started by adding your first item.',
        actionText = null,
        actionCallback = null,
        className = ''
    } = options;
    
    const container = document.createElement('div');
    container.className = `empty-state ${className}`;
    container.style.cssText = `
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: var(--space-12) var(--space-6);
        text-align: center;
        color: var(--text-secondary);
        min-height: 200px;
    `;
    
    // Icon
    const iconElement = document.createElement('div');
    iconElement.className = 'empty-state-icon';
    iconElement.textContent = icon;
    iconElement.style.cssText = `
        font-size: 64px;
        margin-bottom: var(--space-4);
        opacity: 0.7;
    `;
    container.appendChild(iconElement);
    
    // Title
    const titleElement = document.createElement('h3');
    titleElement.className = 'empty-state-title';
    titleElement.textContent = title;
    titleElement.style.cssText = `
        font-size: var(--font-size-xl);
        font-weight: var(--font-weight-semibold);
        color: var(--text-primary);
        margin-bottom: var(--space-2);
    `;
    container.appendChild(titleElement);
    
    // Description
    const descElement = document.createElement('p');
    descElement.className = 'empty-state-description';
    descElement.textContent = description;
    descElement.style.cssText = `
        font-size: var(--font-size-base);
        color: var(--text-secondary);
        margin-bottom: var(--space-6);
        max-width: 400px;
        line-height: var(--line-height-relaxed);
    `;
    container.appendChild(descElement);
    
    // Action button (optional)
    if (actionText && actionCallback) {
        const actionBtn = document.createElement('button');
        actionBtn.className = 'btn btn-primary btn-modern';
        actionBtn.textContent = actionText;
        actionBtn.addEventListener('click', actionCallback);
        container.appendChild(actionBtn);
    }
    
    return container;
}

/**
 * Chat empty state
 */
function createChatEmptyState() {
    return createEmptyState({
        icon: '💬',
        title: 'Start a conversation',
        description: 'Type a message below to begin chatting with the AI assistant. You can ask questions, request help, or have a conversation.',
        actionText: null
    });
}

/**
 * MCP list empty state
 */
function createMCPEmptyState(onAddClick) {
    return createEmptyState({
        icon: '🔌',
        title: 'No MCP servers',
        description: 'Model Context Protocol servers allow the assistant to access external tools and data sources. Add your first MCP server to get started.',
        actionText: 'Add MCP Server',
        actionCallback: onAddClick
    });
}

/**
 * Tools list empty state
 */
function createToolsEmptyState() {
    return createEmptyState({
        icon: '🛠️',
        title: 'No tools available',
        description: 'Tools will appear here once you add MCP servers. Tools allow the assistant to perform actions and retrieve information.',
        actionText: null
    });
}

/**
 * Embeddings empty state
 */
function createEmbeddingsEmptyState() {
    return createEmptyState({
        icon: '📚',
        title: 'No embeddings yet',
        description: 'Create vector stores from your documents to enable semantic search and RAG capabilities. Upload PDFs, code, or scrape websites to get started.',
        actionText: null
    });
}

/**
 * Documents empty state
 */
function createDocumentsEmptyState() {
    return createEmptyState({
        icon: '📄',
        title: 'No documents loaded',
        description: 'Upload documents or scrape web pages to create a knowledge base for your AI assistant.',
        actionText: null
    });
}

/**
 * Search results empty state
 */
function createSearchEmptyState(query) {
    return createEmptyState({
        icon: '🔍',
        title: 'No results found',
        description: query 
            ? `No results found for "${query}". Try different keywords or check your spelling.`
            : 'Try searching for something.',
        actionText: null
    });
}

/**
 * Error state
 */
function createErrorState(options = {}) {
    const {
        icon = '⚠️',
        title = 'Something went wrong',
        description = 'An error occurred. Please try again.',
        actionText = 'Retry',
        actionCallback = null
    } = options;
    
    const container = createEmptyState({
        icon,
        title,
        description,
        actionText,
        actionCallback,
        className: 'error-state'
    });
    
    // Make title red
    const titleElement = container.querySelector('.empty-state-title');
    if (titleElement) {
        titleElement.style.color = 'var(--color-error)';
    }
    
    return container;
}

/**
 * Connection error state
 */
function createConnectionErrorState(onRetry) {
    return createErrorState({
        icon: '🔌',
        title: 'Connection error',
        description: 'Unable to connect to the server. Please check your internet connection and try again.',
        actionText: 'Retry Connection',
        actionCallback: onRetry
    });
}

/**
 * Insert empty state into container
 */
function showEmptyState(containerId, emptyStateElement) {
    const container = typeof containerId === 'string' 
        ? document.getElementById(containerId) 
        : containerId;
    
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Add empty state
    container.appendChild(emptyStateElement);
}

/**
 * Remove empty state
 */
function hideEmptyState(containerId) {
    const container = typeof containerId === 'string' 
        ? document.getElementById(containerId) 
        : containerId;
    
    if (!container) return;
    
    const emptyState = container.querySelector('.empty-state, .error-state');
    if (emptyState) {
        emptyState.remove();
    }
}

/**
 * Check if list is empty and show/hide empty state
 */
function updateEmptyState(containerId, items, emptyStateCreator) {
    const container = typeof containerId === 'string' 
        ? document.getElementById(containerId) 
        : containerId;
    
    if (!container) return;
    
    const existingEmptyState = container.querySelector('.empty-state, .error-state');
    
    if (items.length === 0 && !existingEmptyState) {
        const emptyState = emptyStateCreator();
        container.appendChild(emptyState);
    } else if (items.length > 0 && existingEmptyState) {
        existingEmptyState.remove();
    }
}

// Export functions
if (typeof window !== 'undefined') {
    window.createEmptyState = createEmptyState;
    window.createChatEmptyState = createChatEmptyState;
    window.createMCPEmptyState = createMCPEmptyState;
    window.createToolsEmptyState = createToolsEmptyState;
    window.createEmbeddingsEmptyState = createEmbeddingsEmptyState;
    window.createDocumentsEmptyState = createDocumentsEmptyState;
    window.createSearchEmptyState = createSearchEmptyState;
    window.createErrorState = createErrorState;
    window.createConnectionErrorState = createConnectionErrorState;
    window.showEmptyState = showEmptyState;
    window.hideEmptyState = hideEmptyState;
    window.updateEmptyState = updateEmptyState;
}
