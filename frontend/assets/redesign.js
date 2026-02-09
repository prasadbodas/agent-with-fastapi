// Alpine.js State Management for Redesigned UI

function appState() {
    return {
        // UI State
        theme: localStorage.getItem('theme') || 'light',
        showSidebar: window.innerWidth > 768,
        showSettings: false,
        showToolsPanel: false,
        showKnowledgePanel: false,
        showAddMCPModal: false,
        newMCP: {
            name: '',
            transport: 'stdio',
            command: '',
            url: '',
            args: '',
            env: ''
        },
        
        // Chat State
        conversations: [],
        conversationsLoaded: false,
        currentConversation: null,
        messages: [],
        currentMessage: '',
        isLoading: false,
        searchQuery: '',
        attachedFiles: [],
        isDragging: false,
        uploadProgress: {},
        showScrollToBottom: false,
        
        // WebSocket
        ws: null,
        
        // Tools & Knowledge
        mcpTools: [],
        mcpServers: [],
        toolsByServer: {},
        expandedServers: {},
        enabledTools: [],
        vectorStores: [],
        activeVectorStore: null,
        
        // Settings
        settings: {
            provider: 'openai',
            temperature: 0.7,
        },
        
        // Canvas/Artifacts Panel
        showCanvas: false,
        canvasTab: 'preview',
        canvasType: null,
        canvasContent: '',
        canvasRawContent: '',
        canvasLanguage: '',
        canvasData: null,
        codeOutput: '',
        
        // Initialize
        init() {
            this.loadConversations();
            this.loadVectorStores();
            this.loadMCPTools();
            this.applyTheme();
            this.setupWebSocket();
            this.setupKeyboardShortcuts();
            
            // Handle window resize
            window.addEventListener('resize', () => {
                if (window.innerWidth <= 768) {
                    this.showSidebar = false;
                }
            });
            
            // Setup scroll listener for scroll-to-bottom button
            this.$nextTick(() => {
                const chatContainer = this.$refs.chatContainer;
                if (chatContainer) {
                    chatContainer.addEventListener('scroll', () => {
                        this.checkScrollPosition();
                    });
                }
            });
        },
        
        setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Ctrl/Cmd + K: Focus search
                if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                    e.preventDefault();
                    const searchInput = document.querySelector('.search-input');
                    if (searchInput) searchInput.focus();
                }
                
                // Ctrl/Cmd + N: New chat
                if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                    e.preventDefault();
                    this.createNewConversation();
                }
                
                // Ctrl/Cmd + B: Toggle sidebar
                if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                    e.preventDefault();
                    this.showSidebar = !this.showSidebar;
                }
                
                // Escape: Close modals/panels
                if (e.key === 'Escape') {
                    if (this.showAddMCPModal) {
                        this.showAddMCPModal = false;
                    } else if (this.showCanvas) {
                        this.showCanvas = false;
                    } else if (this.showSettings) {
                        this.showSettings = false;
                    } else if (this.showToolsPanel || this.showKnowledgePanel) {
                        this.showToolsPanel = false;
                        this.showKnowledgePanel = false;
                    }
                }
            });
        },
        
        // Theme Management
        toggleTheme() {
            this.theme = this.theme === 'light' ? 'dark' : 'light';
            this.saveTheme();
        },
        
        saveTheme() {
            localStorage.setItem('theme', this.theme);
            this.applyTheme();
        },
        
        applyTheme() {
            document.documentElement.setAttribute('data-theme', this.theme);
        },
        
        // Conversation Management
        async loadConversations() {
            try {
                const response = await fetch('/api/conversations');
                if (response.ok) {
                    this.conversations = await response.json();
                    this.conversationsLoaded = true;
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (error) {
                console.error('Failed to load conversations:', error);
                this.showToast('Failed to load conversation history', 'error');
                this.conversations = [];
                this.conversationsLoaded = true;
            }
        },
        
        createNewConversation() {
            const newConv = {
                id: Date.now().toString(),
                title: 'New Chat',
                timestamp: new Date().toISOString(),
                messageCount: 0
            };
            this.conversations.unshift(newConv);
            this.currentConversation = newConv;
            this.messages = [];
            this.showToast('New conversation created', 'success');
        },
        
        switchConversation(conversation) {
            this.currentConversation = conversation;
            this.loadMessages(conversation.id);
            
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                this.showSidebar = false;
            }
        },
        
        async loadMessages(conversationId) {
            try {
                const response = await fetch(`/api/conversations/${conversationId}/messages`);
                if (response.ok) {
                    const rawMessages = await response.json();
                    this.messages = this.parseRawMessages(rawMessages);
                } else if (response.status === 404) {
                    this.messages = [];
                    this.showToast('Conversation not found', 'warning');
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }
            } catch (error) {
                console.error('Failed to load messages:', error);
                this.showToast('Failed to load messages', 'error');
                this.messages = [];
            }
        },
        
        parseRawMessages(rawMessages) {
            const parsed = [];
            
            for (const raw of rawMessages) {
                const role = raw.sender;
                const content = raw.msg;
                
                // User messages are plain text
                if (role === 'user') {
                    parsed.push({
                        role: 'user',
                        content: content,
                        timestamp: raw.timestamp
                    });
                    continue;
                }
                
                // Agent messages are JSON strings
                if (role === 'agent') {
                    try {
                        const data = JSON.parse(content);
                        
                        // Check if this is a standalone tool response message
                        if (data.tools && data.tools.messages && !data.agent && !data.rag) {
                            // This is a standalone tool response - add as separate tool messages
                            for (const toolMsg of data.tools.messages) {
                                parsed.push({
                                    role: 'tool',
                                    content: toolMsg.content,
                                    tool_name: toolMsg.name,
                                    tool_call_id: toolMsg.tool_call_id,
                                    status: toolMsg.status || 'success',
                                    timestamp: raw.timestamp
                                });
                            }
                            continue;
                        }
                        
                        // Handle agent messages with tool calls
                        if (data.agent && data.agent.messages && data.agent.messages.length > 0) {
                            const agentMsg = data.agent.messages[0];
                            const message = {
                                role: 'agent',
                                content: agentMsg.content || '',
                                timestamp: raw.timestamp
                            };
                            
                            // Add tool calls if present
                            if (agentMsg.additional_kwargs && 
                                agentMsg.additional_kwargs.tool_calls && 
                                agentMsg.additional_kwargs.tool_calls.length > 0) {
                                message.tool_calls = agentMsg.additional_kwargs.tool_calls;
                            }
                            
                            // Add usage metadata
                            if (agentMsg.usage_metadata) {
                                message.usage_metadata = agentMsg.usage_metadata;
                            }
                            
                            parsed.push(message);
                        }
                        // Handle RAG messages
                        else if (data.rag && data.rag.messages) {
                            parsed.push({
                                role: 'agent',
                                content: data.rag.messages.content || '',
                                usage_metadata: data.rag.messages.usage_metadata,
                                timestamp: raw.timestamp
                            });
                        }
                    } catch (e) {
                        console.error('Failed to parse agent message:', e);
                        // Add as plain text if parsing fails
                        parsed.push({
                            role: 'agent',
                            content: content,
                            timestamp: raw.timestamp
                        });
                    }
                }
            }
            
            return parsed;
        },
        
        async renameConversation(conversation) {
            const newTitle = prompt('Enter new title:', conversation.title);
            if (newTitle && newTitle.trim()) {
                conversation.title = newTitle.trim();
                // TODO: Save to backend
                this.showToast('Conversation renamed', 'success');
            }
        },
        
        async deleteConversation(conversation) {
            if (confirm(`Delete "${conversation.title}"?`)) {
                const index = this.conversations.indexOf(conversation);
                if (index > -1) {
                    this.conversations.splice(index, 1);
                }
                
                if (this.currentConversation?.id === conversation.id) {
                    this.currentConversation = null;
                    this.messages = [];
                }
                
                // TODO: Delete from backend
                this.showToast('Conversation deleted', 'success');
            }
        },
        
        filterConversations() {
            // Filtering logic handled by computed properties
        },
        
        // Computed properties for conversation grouping
        get todayConversations() {
            return this.filterByDate(0);
        },
        
        get yesterdayConversations() {
            return this.filterByDate(1);
        },
        
        get last7DaysConversations() {
            return this.filterByDateRange(2, 7);
        },
        
        get olderConversations() {
            return this.filterByDateRange(8, 365);
        },
        
        filterByDate(daysAgo) {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const targetDate = new Date(today);
            targetDate.setDate(targetDate.getDate() - daysAgo);
            const nextDate = new Date(targetDate);
            nextDate.setDate(nextDate.getDate() + 1);
            
            return this.conversations.filter(conv => {
                if (this.searchQuery && !conv.title.toLowerCase().includes(this.searchQuery.toLowerCase())) {
                    return false;
                }
                const convDate = new Date(conv.timestamp);
                return convDate >= targetDate && convDate < nextDate;
            });
        },
        
        filterByDateRange(startDaysAgo, endDaysAgo) {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const startDate = new Date(today);
            startDate.setDate(startDate.getDate() - endDaysAgo);
            const endDate = new Date(today);
            endDate.setDate(endDate.getDate() - startDaysAgo);
            
            return this.conversations.filter(conv => {
                if (this.searchQuery && !conv.title.toLowerCase().includes(this.searchQuery.toLowerCase())) {
                    return false;
                }
                const convDate = new Date(conv.timestamp);
                return convDate >= startDate && convDate < endDate;
            });
        },
        
        // Message Management
        async sendCurrentMessage() {
            if (!this.currentMessage.trim() && this.attachedFiles.length === 0) return;
            
            // Create conversation if needed
            if (!this.currentConversation) {
                this.createNewConversation();
            }
            
            const messageContent = this.currentMessage.trim();
            const userMessage = {
                role: 'user',
                content: messageContent,
                timestamp: new Date().toISOString(),
                id: Date.now() // Temporary ID for optimistic update
            };
            
            // Optimistic UI update
            this.messages.push(userMessage);
            const messageIndex = this.messages.length - 1;
            this.currentMessage = '';
            this.isLoading = true;
            
            // Auto-scroll to bottom
            this.$nextTick(() => {
                this.scrollToBottom();
            });
            
            // Send via WebSocket with error handling
            try {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        type: 'chat',
                        message: messageContent,
                        conversationId: this.currentConversation.id,
                        vectorStore: this.activeVectorStore,
                        tools: this.enabledTools
                    }));
                } else {
                    throw new Error('WebSocket not connected');
                }
            } catch (error) {
                // Rollback optimistic update on error
                this.messages.splice(messageIndex, 1);
                this.currentMessage = messageContent;
                this.isLoading = false;
                this.showToast('Failed to send message. Please try again.', 'error');
                
                // Attempt to reconnect
                this.setupWebSocket();
            }
        },
        
        sendMessage(text) {
            this.currentMessage = text;
            this.sendCurrentMessage();
        },
        
        async regenerateMessage(index) {
            // Remove assistant message and regenerate
            if (index > 0) {
                this.messages.splice(index);
                const lastUserMessage = this.messages[this.messages.length - 1];
                if (lastUserMessage && lastUserMessage.role === 'user') {
                    this.currentMessage = lastUserMessage.content;
                    this.messages.pop();
                    await this.sendCurrentMessage();
                }
            }
        },
        
        async editMessage(message, index) {
            const newContent = prompt('Edit message:', message.content);
            if (newContent && newContent.trim()) {
                message.content = newContent.trim();
                // TODO: Save to backend and regenerate response if needed
                this.showToast('Message edited', 'success');
            }
        },
        
        async deleteMessage(index) {
            if (confirm('Delete this message?')) {
                this.messages.splice(index, 1);
                // TODO: Delete from backend
                this.showToast('Message deleted', 'success');
            }
        },
        
        copyMessage(message) {
            navigator.clipboard.writeText(message.content).then(() => {
                this.showToast('Message copied to clipboard', 'success');
            }).catch(() => {
                this.showToast('Failed to copy message', 'error');
            });
        },
        
        stopGeneration() {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'stop' }));
            }
            this.isLoading = false;
            this.showToast('Generation stopped', 'info');
        },
        
        // File Management
        handleFileSelect(event) {
            const files = Array.from(event.target.files);
            this.attachedFiles.push(...files);
            event.target.value = '';
        },
        
        handleDrop(event) {
            this.isDragging = false;
            const files = Array.from(event.dataTransfer.files);
            if (files.length > 0) {
                this.attachedFiles.push(...files);
                this.showToast(`${files.length} file(s) added`, 'success');
            }
        },
        
        removeFile(index) {
            this.attachedFiles.splice(index, 1);
        },
        
        async uploadFilesToVectorStore(files, vectorStoreName) {
            const formData = new FormData();
            files.forEach(file => {
                formData.append('files', file);
            });
            formData.append('vectorstore_name', vectorStoreName);
            
            try {
                const response = await fetch('/api/upload-to-vectorstore', {
                    method: 'POST',
                    body: formData
                });
                
                if (response.ok) {
                    const result = await response.json();
                    this.showToast(`${files.length} file(s) uploaded successfully`, 'success');
                    await this.loadVectorStores();
                    return result;
                } else {
                    throw new Error('Upload failed');
                }
            } catch (error) {
                this.showToast('Failed to upload files', 'error');
                console.error('Upload error:', error);
                return null;
            }
        },
        
        async createVectorStore() {
            const name = prompt('Enter vector store name:');
            if (!name || !name.trim()) return;
            
            const storeName = name.trim().replace(/\s+/g, '_').toLowerCase();
            
            if (this.attachedFiles.length === 0) {
                this.showToast('Please attach files first', 'warning');
                return;
            }
            
            this.showToast('Creating vector store...', 'info');
            
            const result = await this.uploadFilesToVectorStore(this.attachedFiles, storeName);
            if (result) {
                this.attachedFiles = [];
                this.activeVectorStore = storeName;
                this.showToast(`Vector store "${storeName}" created`, 'success');
            }
        },
        
        async addFilesToExistingStore(storeName) {
            if (this.attachedFiles.length === 0) {
                this.showToast('Please attach files first', 'warning');
                return;
            }
            
            const result = await this.uploadFilesToVectorStore(this.attachedFiles, storeName);
            if (result) {
                this.attachedFiles = [];
                this.showToast(`Files added to "${storeName}"`, 'success');
            }
        },
        
        async deleteVectorStore(store) {
            if (!confirm(`Delete vector store "${store.name}"? This cannot be undone.`)) return;
            
            try {
                const response = await fetch(`/api/vectorstore/${encodeURIComponent(store.name)}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    await this.loadVectorStores();
                    if (this.activeVectorStore === store.name) {
                        this.activeVectorStore = null;
                    }
                    this.showToast(`Deleted "${store.name}"`, 'success');
                } else {
                    throw new Error('Delete failed');
                }
            } catch (error) {
                this.showToast('Failed to delete vector store', 'error');
                console.error('Delete error:', error);
            }

        },
        
        // Vector Store Management
        async loadVectorStores() {
            try {
                const response = await fetch('/vectorstores');
                if (response.ok) {
                    const data = await response.json();
                    
                    // Fetch detailed info for each vectorstore
                    const storesWithInfo = await Promise.all(
                        data.vectorstores.map(async (name) => {
                            try {
                                const infoResponse = await fetch(`/api/vectorstore/${encodeURIComponent(name)}/info`);
                                if (infoResponse.ok) {
                                    const info = await infoResponse.json();
                                    return {
                                        name: info.name,
                                        count: info.document_count || 0
                                    };
                                }
                            } catch (error) {
                                console.error(`Failed to get info for ${name}:`, error);
                            }
                            return { name, count: 0 };
                        })
                    );
                    
                    this.vectorStores = storesWithInfo;
                }
            } catch (error) {
                console.error('Failed to load vector stores:', error);
            }
        },
        
        selectVectorStore(store) {
            this.activeVectorStore = this.activeVectorStore === store.name ? null : store.name;
            this.showToast(
                this.activeVectorStore ? `Using ${store.name}` : 'Vector store deselected',
                'success'
            );
        },
        
        createVectorStore() {
            // TODO: Implement vector store creation
            this.showToast('Vector store creation coming soon', 'info');
        },
        
        // MCP Tools Management
        async loadMCPTools() {
            try {
                // First get MCP servers list
                const mcpResponse = await fetch('/mcp/list');
                if (mcpResponse.ok) {
                    const mcpData = await mcpResponse.json();
                    this.mcpServers = mcpData.mcps || [];
                    
                    // Initialize expanded state for each server
                    this.mcpServers.forEach(server => {
                        if (this.expandedServers[server.id] === undefined) {
                            this.expandedServers[server.id] = false;
                        }
                    });
                }
                
                // Then get available tools with server mapping
                const toolsResponse = await fetch('/mcp/tools');
                if (toolsResponse.ok) {
                    const data = await toolsResponse.json();
                    const savedTools = JSON.parse(localStorage.getItem('enabledTools') || '[]');
                    
                    // Store tools by server mapping
                    this.toolsByServer = data.tools_by_server || {};
                    
                    // Check if tools array exists in response
                    if (data.tools && Array.isArray(data.tools)) {
                        this.mcpTools = data.tools.map(tool => ({
                            ...tool,
                            enabled: savedTools.includes(tool.name),
                            executing: false
                        }));
                    } else {
                        this.mcpTools = [];
                    }
                }
            } catch (error) {
                console.error('Failed to load MCP tools:', error);
                this.showToast('Failed to load MCP tools: ' + error.message, 'error');
            }
        },
        
        toggleServerExpansion(serverId) {
            this.expandedServers[serverId] = !this.expandedServers[serverId];
        },
        
        getServerTools(serverName) {
            // Get tools for specific server from mapping
            const serverTools = this.toolsByServer[serverName] || [];
            
            // Map to full tool objects with enabled state
            return serverTools.map(tool => {
                const fullTool = this.mcpTools.find(t => t.name === tool.name);
                return fullTool || tool;
            });
        },
        
        async toggleServerActive(server) {
            try {
                const response = await fetch(`/mcp/${server.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ active: server.active ? 0 : 1 })
                });
                
                if (response.ok) {
                    server.active = server.active ? 0 : 1;
                    await fetch('/mcp/reload', { method: 'POST' });
                    await this.loadMCPTools();
                    this.showToast(
                        server.active ? `Activated ${server.name}` : `Deactivated ${server.name}`,
                        'success'
                    );
                }
            } catch (error) {
                console.error('Error toggling server:', error);
                this.showToast('Error updating server: ' + error.message, 'error');
            }
        },
        
        async deleteMCPServer(server) {
            if (!confirm(`Delete MCP server "${server.name}"? This cannot be undone.`)) return;
            
            try {
                const response = await fetch(`/mcp/${server.id}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    await fetch('/mcp/reload', { method: 'POST' });
                    await this.loadMCPTools();
                    this.showToast(`Deleted ${server.name}`, 'success');
                }
            } catch (error) {
                console.error('Error deleting server:', error);
                this.showToast('Error deleting server: ' + error.message, 'error');
            }
        },
        
        async refreshMCPTools() {
            this.showToast('Refreshing tools...', 'info');
            await this.loadMCPTools();
            this.showToast('Tools refreshed', 'success');
        },
        
        openAddMCPModal() {
            this.newMCP = {
                name: '',
                transport: 'stdio',
                command: '',
                url: '',
                args: '',
                env: ''
            };
            this.showAddMCPModal = true;
        },
        
        async addNewMCP() {
            // Validation based on transport type
            if (!this.newMCP.name) {
                this.showToast('Please provide a server name', 'error');
                return;
            }
            
            if (this.newMCP.transport === 'stdio' && !this.newMCP.command) {
                this.showToast('Please provide a command for stdio transport', 'error');
                return;
            }
            
            if (this.newMCP.transport === 'http' && !this.newMCP.url) {
                this.showToast('Please provide a URL for http transport', 'error');
                return;
            }
            
            try {
                let mcpConfig = {
                    name: this.newMCP.name,
                    transport: this.newMCP.transport,
                    active: true
                };
                
                // Add fields based on transport type
                if (this.newMCP.transport === 'stdio') {
                    mcpConfig.command = this.newMCP.command;
                    mcpConfig.args = this.newMCP.args ? this.newMCP.args.split(',').map(a => a.trim()) : [];
                } else if (this.newMCP.transport === 'http') {
                    mcpConfig.url = this.newMCP.url;
                }
                
                // Add environment variables/metadata if provided
                if (this.newMCP.env && this.newMCP.env.trim()) {
                    try {
                        mcpConfig.metadata = JSON.parse(this.newMCP.env);
                    } catch (e) {
                        this.showToast('Invalid JSON in environment variables', 'error');
                        return;
                    }
                }
                
                const response = await fetch('/mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(mcpConfig)
                });
                
                if (response.ok) {
                    // Reload MCP client after adding
                    await fetch('/mcp/reload', { method: 'POST' });
                    this.showToast('MCP server added successfully', 'success');
                    this.showAddMCPModal = false;
                    await this.loadMCPTools();
                } else {
                    const error = await response.json();
                    this.showToast(error.detail || 'Failed to add MCP server', 'error');
                }
            } catch (error) {
                console.error('Error adding MCP:', error);
                this.showToast('Error adding MCP server: ' + error.message, 'error');
            }
        },
        
        toggleTool(tool) {
            // Save enabled tools to localStorage
            const enabledToolNames = this.mcpTools
                .filter(t => t.enabled)
                .map(t => t.name);
            localStorage.setItem('enabledTools', JSON.stringify(enabledToolNames));
            
            this.showToast(
                tool.enabled ? `Enabled ${tool.name}` : `Disabled ${tool.name}`,
                'success'
            );
        },
        
        get enabledTools() {
            return this.mcpTools.filter(tool => tool.enabled).map(t => t.name);
        },
        
        setToolExecuting(toolName, executing) {
            const tool = this.mcpTools.find(t => t.name === toolName);
            if (tool) {
                tool.executing = executing;
            }
        },
        
        // WebSocket Management
        setupWebSocket() {
            // Close existing connection if any
            if (this.ws) {
                this.ws.close();
            }
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            // Use /ws/react for agent mode or /ws/ask for RAG mode
            const endpoint = this.selectedVectorStore ? '/ws/ask' : '/ws/react';
            const wsUrl = `${protocol}//${window.location.host}${endpoint}`;
            
            try {
                this.ws = new WebSocket(wsUrl);
                
                this.ws.onopen = () => {
                    console.log('WebSocket connected');
                    this.showToast('Connected', 'success');
                };
                
                this.ws.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        
                        // Handle agent/tool responses (JSON structured messages)
                        if (typeof data === 'object') {
                            // Check for RAG response
                            if (data.rag && data.rag.messages && data.rag.messages.content) {
                                const content = data.rag.messages.content;
                                if (this.messages.length === 0 || this.messages[this.messages.length - 1].role !== 'agent') {
                                    this.messages.push({
                                        role: 'agent',
                                        content: '',
                                        usage_metadata: data.rag.messages.usage_metadata,
                                        timestamp: new Date().toISOString()
                                    });
                                }
                                const lastMessage = this.messages[this.messages.length - 1];
                                lastMessage.content += content;
                                this.$nextTick(() => this.scrollToBottom());
                                return;
                            }
                            
                            // Handle agent messages with tool calls
                            if (data.agent && data.agent.messages && data.agent.messages.length > 0) {
                                const agentMsg = data.agent.messages[0];
                                
                                // Check for tool calls
                                if (agentMsg.additional_kwargs && 
                                    agentMsg.additional_kwargs.tool_calls && 
                                    agentMsg.additional_kwargs.tool_calls.length > 0) {
                                    
                                    // Add agent message with tool calls embedded
                                    this.messages.push({
                                        role: 'agent',
                                        content: agentMsg.content || '',
                                        tool_calls: agentMsg.additional_kwargs.tool_calls,
                                        usage_metadata: agentMsg.usage_metadata,
                                        timestamp: new Date().toISOString()
                                    });
                                    
                                    this.$nextTick(() => this.scrollToBottom());
                                    return;
                                }
                                
                                // Handle regular agent content
                                if (agentMsg.content && agentMsg.content.length > 0) {
                                    if (this.messages.length === 0 || this.messages[this.messages.length - 1].role !== 'agent') {
                                        this.messages.push({
                                            role: 'agent',
                                            content: agentMsg.content,
                                            usage_metadata: agentMsg.usage_metadata,
                                            timestamp: new Date().toISOString()
                                        });
                                    } else {
                                        const lastMessage = this.messages[this.messages.length - 1];
                                        lastMessage.content += agentMsg.content;
                                        if (agentMsg.usage_metadata) {
                                            lastMessage.usage_metadata = agentMsg.usage_metadata;
                                        }
                                    }
                                    this.$nextTick(() => this.scrollToBottom());
                                    return;
                                }
                            }
                            
                            // Handle tool responses
                            if (data.tools && data.tools.messages && data.tools.messages.length > 0) {
                                data.tools.messages.forEach(toolMsg => {
                                    // Find the DOM element with matching tool_call_id
                                    const toolDiv = document.getElementById(toolMsg.tool_call_id);
                                    
                                    if (toolDiv) {
                                        // Append the result to the existing tool call div
                                        const statusIcon = toolMsg.status === 'error' ? '❌' : '✅';
                                        const statusText = toolMsg.status === 'error' ? 'Error' : 'Success';
                                        const resultHtml = `
                                            <div class="tool-result ${toolMsg.status === 'error' ? 'error' : 'success'}">
                                                <div class="tool-result-label">${statusIcon} Tool Result (${statusText}):</div>
                                                <div class="tool-result-content">${toolMsg.content}</div>
                                            </div>
                                        `;
                                        toolDiv.insertAdjacentHTML('beforeend', resultHtml);
                                    } else {
                                        // If no matching tool call found, add as separate message
                                        this.messages.push({
                                            role: 'tool',
                                            content: toolMsg.content,
                                            tool_name: toolMsg.name,
                                            status: toolMsg.status,
                                            timestamp: new Date().toISOString()
                                        });
                                    }
                                });
                                this.$nextTick(() => this.scrollToBottom());
                                return;
                            }
                        }
                        
                        // Fallback: Plain text streaming (backward compatibility)
                        const content = typeof data === 'string' ? data : JSON.stringify(data);
                        if (this.messages.length === 0 || this.messages[this.messages.length - 1].role !== 'agent') {
                            this.messages.push({
                                role: 'agent',
                                content: content,
                                timestamp: new Date().toISOString()
                            });
                        } else {
                            const lastMessage = this.messages[this.messages.length - 1];
                            lastMessage.content += content;
                        }
                        
                        this.$nextTick(() => this.scrollToBottom());
                        
                    } catch (error) {
                        console.error('WebSocket message parsing error:', error);
                        // Treat as plain text on parse error
                        const content = event.data;
                        if (this.messages.length === 0 || this.messages[this.messages.length - 1].role !== 'agent') {
                            this.messages.push({
                                role: 'agent',
                                content: content,
                                timestamp: new Date().toISOString()
                            });
                        } else {
                            const lastMessage = this.messages[this.messages.length - 1];
                            lastMessage.content += content;
                        }
                        this.$nextTick(() => this.scrollToBottom());
                    }
                };
                
                this.ws.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.showToast('Connection error', 'error');
                };
                
                this.ws.onclose = () => {
                    console.log('WebSocket closed');
                    // Attempt to reconnect after 3 seconds
                    setTimeout(() => {
                        if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
                            this.showToast('Reconnecting...', 'info');
                            this.setupWebSocket();
                        }
                    }, 3000);
                };
            } catch (error) {
                console.error('Failed to create WebSocket:', error);
                this.showToast('Failed to connect. Please refresh the page.', 'error');
            }
        },
        
        async generateConversationTitle() {
            // Generate a title based on the first user message
            if (this.messages.length > 0 && this.currentConversation) {
                const firstMessage = this.messages[0].content;
                const title = firstMessage.slice(0, 50) + (firstMessage.length > 50 ? '...' : '');
                this.currentConversation.title = title;
                // TODO: Save to backend
            }
        },
        
        // Utility Functions
        renderMarkdown(text) {
            if (typeof marked !== 'undefined') {
                return marked.parse(text || '');
            }
            return text || '';
        },
        
        scrollToBottom() {
            const container = this.$refs.chatContainer;
            if (container) {
                container.scrollTop = container.scrollHeight;
                this.showScrollToBottom = false;
            }
        },
        
        checkScrollPosition() {
            const container = this.$refs.chatContainer;
            if (container) {
                const threshold = 100; // Show button if more than 100px from bottom
                const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight;
                this.showScrollToBottom = distanceFromBottom > threshold;
            }
        },
        
        autoResize(event) {
            const textarea = event.target;
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
        },
        
        handleEnter(event) {
            if (!event.shiftKey) {
                this.sendCurrentMessage();
            }
        },
        
        showToast(message, type = 'info') {
            if (typeof window.toastManager !== 'undefined') {
                window.toastManager[type](message);
            } else {
                console.log(`[${type}] ${message}`);
            }
        },
        
        // Canvas/Artifacts Methods
        openCanvas(content, type = 'html', language = '', rawContent = '') {
            this.canvasContent = content;
            this.canvasRawContent = rawContent || content;
            this.canvasType = type;
            this.canvasLanguage = language;
            this.canvasTab = 'preview';
            this.codeOutput = '';
            this.showCanvas = true;
            
            // Parse data if it's a table/CSV
            if (type === 'data' || language === 'csv') {
                this.parseDataForCanvas(content);
            }
            
            this.showToast('Opened in canvas', 'success');
        },
        
        parseDataForCanvas(content) {
            try {
                // Try to parse as CSV or JSON
                if (content.includes(',') || content.includes('\t')) {
                    const lines = content.trim().split('\n');
                    const headers = lines[0].split(/,|\t/);
                    const data = lines.slice(1).map(line => line.split(/,|\t/));
                    
                    this.canvasData = {
                        headers: headers,
                        data: data,
                        rows: data.length,
                        columns: headers.length
                    };
                } else if (content.trim().startsWith('[') || content.trim().startsWith('{')) {
                    const json = JSON.parse(content);
                    if (Array.isArray(json)) {
                        const headers = Object.keys(json[0] || {});
                        const data = json.map(row => headers.map(h => row[h]));
                        
                        this.canvasData = {
                            headers: headers,
                            data: data,
                            rows: data.length,
                            columns: headers.length
                        };
                    }
                }
            } catch (error) {
                console.error('Failed to parse data:', error);
                this.canvasData = null;
            }
        },
        
        detectCodeInMessage(message) {
            // Detect code blocks in markdown and offer to open in canvas
            const codeBlockRegex = /```(\w+)?\n([\s\S]+?)```/g;
            const matches = [...message.matchAll(codeBlockRegex)];
            
            if (matches.length > 0) {
                const match = matches[matches.length - 1]; // Use last code block
                const language = match[1] || 'plaintext';
                const code = match[2].trim();
                
                // Check if it's executable or visual content
                if (['html', 'svg'].includes(language)) {
                    return { type: 'html', language, content: code };
                } else if (['python', 'javascript', 'js'].includes(language)) {
                    return { type: 'code', language, content: code };
                } else if (['csv', 'json'].includes(language)) {
                    return { type: 'data', language, content: code };
                }
            }
            return null;
        },
        
        copyCanvasContent() {
            const content = this.canvasRawContent || this.canvasContent;
            navigator.clipboard.writeText(content).then(() => {
                this.showToast('Copied to clipboard', 'success');
            }).catch(() => {
                this.showToast('Failed to copy', 'error');
            });
        },
        
        downloadCanvas() {
            const content = this.canvasRawContent || this.canvasContent;
            const ext = this.canvasLanguage || 'txt';
            const filename = `artifact.${ext}`;
            
            const blob = new Blob([content], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            
            this.showToast('Downloaded', 'success');
        },
        
        async executeCode() {
            this.codeOutput = 'Executing...';
            
            try {
                if (this.canvasLanguage === 'javascript' || this.canvasLanguage === 'js') {
                    // Execute JavaScript in sandbox
                    const logs = [];
                    const console = {
                        log: (...args) => logs.push(args.join(' '))
                    };
                    
                    try {
                        const result = eval(this.canvasRawContent);
                        if (result !== undefined) logs.push(String(result));
                        this.codeOutput = logs.join('\n') || 'No output';
                    } catch (error) {
                        this.codeOutput = `Error: ${error.message}`;
                    }
                } else if (this.canvasLanguage === 'python') {
                    // Send to backend for Python execution
                    const response = await fetch('/api/execute-python', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ code: this.canvasRawContent })
                    });
                    
                    if (response.ok) {
                        const result = await response.json();
                        this.codeOutput = result.output || result.error || 'No output';
                    } else {
                        this.codeOutput = 'Error: Failed to execute code';
                    }
                }
            } catch (error) {
                this.codeOutput = `Error: ${error.message}`;
            }
        }
    };
}

// Message rendering helper functions
function renderToolCall(toolData, toolCallId) {
    const toolName = toolData.name || 'Unknown Tool';
    const toolArgs = typeof toolData.arguments === 'string' 
        ? JSON.parse(toolData.arguments || '{}') 
        : (toolData.arguments || {});
    
    const formattedArgs = Object.entries(toolArgs)
        .map(([key, value]) => `<strong>${key}:</strong> ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}`)
        .join('<br>');

    return `
        <div class="tool-call" id="${toolCallId}">
            <div class="tool-call-header">
                <i class="bi bi-gear-fill"></i>
                <span>🔧 Tool Call: ${toolName}</span>
            </div>
            <div class="tool-call-content">
                <pre>${formattedArgs}</pre>
            </div>
        </div>
    `;
}

function renderToolResponse(toolData) {
    const statusIcon = toolData.status === 'error' ? '❌' : '✅';
    const statusClass = toolData.status === 'error' ? 'tool-status-error' : 'tool-status-success';
    const toolName = toolData.name || toolData.tool_name || 'Tool';
    
    return `
        <div class="tool-call-header">
            <i class="bi bi-gear-fill"></i>
            <span>Tool: ${toolName}</span>
            <span class="${statusClass}" title="${toolData.status || 'success'}">${statusIcon}</span>
        </div>
        <div class="tool-call-content">
            <pre>${toolData.content}</pre>
        </div>
    `;
}

function renderTokenUsage(usageMetadata) {
    if (!usageMetadata) return '';
    
    return `
        <div class="token-usage">
            <i class="bi bi-lightning-charge"></i>
            <span>${usageMetadata.input_tokens || 0} in</span>
            <span class="token-separator">•</span>
            <span>${usageMetadata.output_tokens || 0} out</span>
            ${usageMetadata.total_tokens ? `
                <span class="token-separator">•</span>
                <span>${usageMetadata.total_tokens} total</span>
            ` : ''}
        </div>
    `;
}

function renderAgentMessage(message) {
    let html = '';
    
    // Handle tool calls if present
    if (message.tool_calls && message.tool_calls.length > 0) {
        message.tool_calls.forEach(toolCall => {
            if (toolCall.type === 'function') {
                html += renderToolCall(toolCall.function, toolCall.id);
            }
        });
    }
    
    // Add content if it exists
    if (message.content && message.content.trim()) {
        html += `<div class="message-text">${marked.parse(message.content)}</div>`;
    }
    
    // Add token usage if available
    if (message.usage_metadata) {
        html += renderTokenUsage(message.usage_metadata);
    }
    
    return html;
}

// Initialize toast manager
document.addEventListener('DOMContentLoaded', () => {
    if (typeof ToastManager !== 'undefined') {
        window.toastManager = new ToastManager();
    }
});
