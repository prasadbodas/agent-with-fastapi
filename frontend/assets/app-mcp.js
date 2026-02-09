const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/react';
let socket;

let messageHistory = [];
let sessionId = localStorage.getItem('chat_session_id') || generateSessionId();
let currentMode = localStorage.getItem('chat_mode') || 'agent';
let currentStreamingMessage = null; // Track current streaming message for Ask mode
let streamingTimeout = null; // Timeout to detect end of stream
localStorage.setItem('chat_session_id', sessionId);
localStorage.setItem('chat_mode', currentMode);

// ============================================
// THEME MANAGEMENT
// ============================================

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-toggle-icon');
    if (icon) {
        icon.textContent = theme === 'light' ? '🌙' : '☀️';
    }
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

function generateSessionId() {
    return 'sess-' + Math.random().toString(36).substr(2, 16);
}

function updateModeInfo() {
    const modeText = document.getElementById('current-mode-text');
    if (modeText) {
        if (currentMode === 'agent') {
            modeText.textContent = 'Agent Mode: Tool-enabled ReAct agent';
        } else {
            modeText.textContent = 'Ask Mode: RAG-enabled Q&A assistant';
        }
    }
}

function putInnerHTMLOfMessage(div, msg_content) {
    // Regular message with markdown support
    if (typeof marked !== 'undefined') {
        console.log('Rendering markdown with marked library');
        div.innerHTML = marked.parse(msg_content);
    } else {
        // Fallback: simple formatting without markdown library
        const formattedMsg = msg_content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        div.innerHTML = formattedMsg;
    }
}

function renderMessages() {
    const hr = document.createElement('hr');
    hr.className = 'my-1';
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        const wasAtBottom = chatBox.scrollHeight - chatBox.clientHeight <= chatBox.scrollTop + 1;

        chatBox.innerHTML = '';
        messageHistory.forEach(({msg, sender, type, streaming}) => {
            const div = document.createElement('div');
            var usageDiv = null;
            var toolDiv = null;
            var toolResultDiv = null;

            // Handle different message types
            if (sender == "agent"){
                // Try to parse as JSON first (for agent mode responses)
                try {
                    msg_json = JSON.parse(msg);

                    // Check if this is a RAG response
                    if (msg_json.rag && msg_json.rag.messages && msg_json.rag.messages.content) {
                        msg_content = msg_json.rag.messages ? msg_json.rag.messages.content : msg_json;

                        putInnerHTMLOfMessage(div, msg_content);
                        // Add streaming indicator if still streaming
                        if (streaming) {
                            const streamingIndicator = document.createElement('span');
                            streamingIndicator.className = 'streaming-indicator';
                            streamingIndicator.innerHTML = ' <span class="typing-dots">...</span>';
                            div.appendChild(streamingIndicator);
                        }
                        // Skip the rest of agent processing for RAG responses
                    } else if (msg_json.agent && msg_json.agent.messages && msg_json.agent.messages.length > 0) {
                        // Handle regular agent responses (existing logic)
                        // If agent messages are present, use the first message content
                        console.log('Agent messages found:', msg_json.agent.messages[0].additional_kwargs.tool_calls);
                        if (msg_json.agent.messages[0].additional_kwargs &&
                            msg_json.agent.messages[0].additional_kwargs.tool_calls &&
                            msg_json.agent.messages[0].additional_kwargs.tool_calls.length > 0
                        ) {
                            // If tool calls are present, render them
                            // {"agent": {"messages": [{"content": "", "additional_kwargs": {"tool_calls": [{"id": "call_e9v23FP4z6bvuvF4lux6Y86Y", "function": {"arguments": "{"action":"schema","model":"dashboard.item","domain":null,"fields":null,"values":null,"ids":null}", "name": "odoo_tool"}, "type": "function"}], "refusal": null}, "response_metadata": {"token_usage": {"completion_tokens": 301, "prompt_tokens": 395, "total_tokens": 696, "completion_tokens_details": {"accepted_prediction_tokens": 0, "audio_tokens": 0, "reasoning_tokens": 256, "rejected_prediction_tokens": 0}, "prompt_tokens_details": {"audio_tokens": 0, "cached_tokens": 0}}, "model_name": "gpt-5-nano-2025-08-07", "system_fingerprint": null, "id": "chatcmpl-C6EnEEGq1SCaZ6skM2cLdjkwDRjdL", "service_tier": "default", "finish_reason": "tool_calls", "logprobs": null}, "id": "run--2243a84d-3b68-4181-85cd-2f5be8376b90-0", "usage_metadata": {"input_tokens": 395, "output_tokens": 301, "total_tokens": 696, "input_token_details": {"audio": 0, "cache_read": 0}, "output_token_details": {"audio": 0, "reasoning": 256}}}]}}
                            msg_json.agent.messages[0].additional_kwargs.tool_calls.forEach(toolCall => {
                                console.log('Rendering tool call:', toolCall);
                                if (toolCall.type === 'function') {
                                    toolDiv = document.createElement('div');
                                    toolDiv.id = toolCall.id;
                                    renderToolCall(toolDiv, toolCall.function);
                                    console.log('Tool call rendered:', toolDiv);
                                }
                            });
                        } else if (msg_json.agent.messages[0].content.length > 0) {
                            // If the first message has content, use it
                            // console.log(msg_json.agent.messages[0].content, typeof msg_json);
                            msg_content = msg_json.agent.messages ? msg_json.agent.messages[0].content : msg_json;
                            putInnerHTMLOfMessage(div, msg_content);
                        } else {
                            console.log('No agent/tool calls messages found, using original message');
                            putInnerHTMLOfMessage(div, msg);
                        }

                        usage_metrics = msg_json.agent.messages[0].usage_metadata;
                        if (usage_metrics) {
                            usageDiv = document.createElement('div');
                            usageDiv.className = 'usage-metrics fs-6 text-secondary';
                            usageDiv.innerHTML = `
                                <span>Token Metrics- <b>I/P</b>: ${usage_metrics.input_tokens || 0} <b>O/P</b>: ${usage_metrics.output_tokens || 0} <b>Total</b>: ${usage_metrics.total_tokens || 0}</span>
                            `;
                        }
                    } else if (msg_json.tools && msg_json.tools.messages && msg_json.tools.messages.length > 0) {
                        msg_json.tools.messages.forEach(toolMsg => {
                            console.log('Rendering tool message:', toolMsg);
                            toolResultDiv = document.createElement('div');
                            parentToolDiv = document.getElementById(toolMsg.tool_call_id);
                            renderToolResponse(toolResultDiv, toolMsg);
                            if (parentToolDiv) {
                                parentToolDiv.appendChild(toolResultDiv);
                                // discard further execution of the loop
                                return;
                            } else {
                                console.warn('Parent tool div not found for tool call ID: ', toolMsg.tool_call_id);
                            }
                        });
                    } else {
                        // Fallback to the original message if no agent messages are found
                        console.log('No agent messages found, using original message');
                        putInnerHTMLOfMessage(div, msg);
                    }
                } catch (e) {
                    // If JSON parsing fails, treat as plain text (for simple responses or streaming)
                    console.log('Failed to parse as JSON, treating as plain text:', e);
                    putInnerHTMLOfMessage(div, msg);
                    // Add streaming indicator if still streaming
                    if (streaming) {
                        const streamingIndicator = document.createElement('span');
                        streamingIndicator.className = 'streaming-indicator';
                        streamingIndicator.innerHTML = ' <span class="typing-dots">...</span>';
                        div.appendChild(streamingIndicator);
                    }
                }
            } else {
                // For user messages, just use the original message content
                putInnerHTMLOfMessage(div, msg);
            }

            div.className = sender === "user" ? "user-msg" : "agent-msg";
            div.classList.add('chat-msg');
            if (sender === "agent") {
                // div.appendChild(hr);
                console.log(usageDiv);

                // Render tool calls if available
                if (toolDiv) {
                    console.log('Appending tool calls:', toolDiv);
                    div.appendChild(toolDiv);
                }
                // Append usage metrics if available
                if (usageDiv) {
                    div.appendChild(usageDiv);
                }
            }

            if (toolResultDiv == null) {
                // Append the message div to the chat box
                chatBox.appendChild(div);
            }
        });

        // Auto-scroll to bottom if user was already at the bottom
        if (wasAtBottom || messageHistory.length === 1) {
            chatBox.scrollTop = chatBox.scrollHeight;
        }
    }
}

function renderToolCall(div, toolData) {
    div.className = 'tool-call';
    const toolName = toolData.name || 'Unknown Tool';
    const toolArgs = JSON.parse(toolData.arguments || '{}');
    const formattedArgs = Object.entries(toolArgs)
        .map(([key, value]) => `<strong>${key}:</strong> ${typeof value === 'object' ? JSON.stringify(value, null, 2) : value}`)
        .join('<br>');

    div.innerHTML = `
        <div class="tool-name">🔧 Tool Call: ${toolName}</div>
        <div class="tool-args">${formattedArgs}</div>
    `;
}

function renderToolResponse(div, toolData) {
    console.log('Rendering tool response:', toolData);
    div.id = toolData.id;
    if (toolData.status === 'error') {
        div.className = 'tool-error error';
        div.innerHTML = `
            <div class="error-label">❌ Tool Error:</div>
            <div class="tool-result">${toolData.content}</div>
        `;
    } else {
        div.className = 'tool-response success';
        div.innerHTML = `
            <div class="tool-result-label">✅ Tool Result:</div>
            <div class="tool-result">${toolData.content}</div>
        `;
    }
}

function renderToolExecuting(div, toolData) {
    div.className = 'tool-executing';
    const toolName = toolData.name || 'tool';
    div.innerHTML = `⏳ Executing ${toolName}...`;
}

function displayMessage(msg, sender = "agent", type = null) {
    messageHistory.push({msg, sender, type});
    renderMessages();
}

function fetchHistory() {
    fetch(`/history/${sessionId}`)
        .then(res => res.json())
        .then(data => {
            if (data.history) {
                messageHistory = data.history.map(({msg, sender}) => ({msg, sender}));
                renderMessages();
            }
        });
}

function connectWebSocket() {
    // Close existing socket if any
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
    }
    
    // Choose WebSocket endpoint based on mode
    const endpoint = currentMode === 'agent' ? '/ws/react' : '/ws/ask';
    const wsEndpointUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + endpoint;
    
    socket = new WebSocket(wsEndpointUrl);

    socket.onopen = function() {
        console.log('WebSocket connected to', endpoint);
    };

    socket.onmessage = function(event) {
        // Remove loading state from send button
        const sendBtn = document.getElementById('send-btn');
        if (sendBtn && typeof window.removeButtonLoading === 'function') {
            window.removeButtonLoading(sendBtn);
        }
        
        try {
            if (currentMode === 'ask') {
                // Handle streaming for Ask mode
                const chunk = event.data;
                
                if (currentStreamingMessage === null) {
                    // Start new streaming message
                    currentStreamingMessage = {
                        msg: chunk,
                        sender: "agent",
                        streaming: true
                    };
                    messageHistory.push(currentStreamingMessage);
                } else {
                    // Append to existing streaming message
                    currentStreamingMessage.msg += chunk;
                }
                
                renderMessages();
                
                // Clear existing timeout and set new one
                if (streamingTimeout) {
                    clearTimeout(streamingTimeout);
                }
                
                // Set timeout to detect end of stream (no new chunks for 1 second)
                streamingTimeout = setTimeout(() => {
                    if (currentStreamingMessage) {
                        currentStreamingMessage.streaming = false;
                        currentStreamingMessage = null;
                        renderMessages(); // Final render to clean up any streaming indicators
                    }
                }, 1000);
                
            } else {
                // Handle regular messages for Agent mode
                messageHistory.push({msg: event.data, sender: "agent"});
                renderMessages();
            }
        } catch (e) {
            // Fallback for plain text messages
            if (currentMode === 'ask' && currentStreamingMessage !== null) {
                currentStreamingMessage.msg += event.data;
            } else {
                messageHistory.push({msg: event.data, sender: "agent"});
            }
            renderMessages();
        }
    };

    socket.onclose = function() {
        console.log('WebSocket disconnected');
    };

    socket.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function sendMessage(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        // Reset streaming state for new message
        if (currentMode === 'ask') {
            currentStreamingMessage = null;
            if (streamingTimeout) {
                clearTimeout(streamingTimeout);
                streamingTimeout = null;
            }
        }
        
        let payload = {
            message,
            session_id: sessionId,
            mode: currentMode
        };
        
        const modelSelect = document.getElementById('model-select');
        if (modelSelect && modelSelect.value) {
            payload.model_provider = modelSelect.value;
        }
        socket.send(JSON.stringify(payload));
    } else {
        console.error('WebSocket is not open');
        showNotification('Connection error. Please refresh the page.', 'error');
    }
}

// ============================================
// NOTIFICATION SYSTEM (Using Toast)
// ============================================

function showNotification(message, type = 'info') {
    if (window.toast) {
        window.toast.show(message, type);
    } else {
        // Fallback
        const statusDiv = document.getElementById('status-message');
        if (statusDiv) {
            statusDiv.textContent = message;
            statusDiv.className = `status-message ${type}`;
            statusDiv.style.display = 'block';
            
            setTimeout(() => {
                statusDiv.style.display = 'none';
            }, 3000);
        }
    }
}

// ============================================
// INITIALIZATION
// ============================================

window.addEventListener('DOMContentLoaded', () => {
    // Initialize theme
    initTheme();
    
    // Theme toggle event listener
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    // Initialize mode from localStorage
    const savedMode = localStorage.getItem('chat_mode') || 'agent';
    currentMode = savedMode;

    // Set the radio button to match saved mode
    const modeRadio = document.querySelector(`input[name="mode"][value="${currentMode}"]`);
    if (modeRadio) {
        modeRadio.checked = true;
    }

    // Update mode info text
    updateModeInfo();

    // Initialize keyboard shortcuts
    if (typeof window.initKeyboardShortcuts === 'function') {
        window.initKeyboardShortcuts();
    }
    
    // Create scroll to bottom button
    if (typeof window.createScrollToBottomButton === 'function') {
        window.createScrollToBottomButton();
    }

    // Add event listeners for mode change
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                currentMode = this.value;
                localStorage.setItem('chat_mode', currentMode);
                // Reset streaming state when changing modes
                currentStreamingMessage = null;
                updateModeInfo();
                // Reconnect WebSocket with new endpoint
                connectWebSocket();
                console.log('Mode changed to:', currentMode);
            }
        });
    });

    fetchHistory();
    connectWebSocket();
    const sendBtn = document.getElementById('send-btn');
    const input = document.getElementById('user-input');
    if (sendBtn && input) {
        sendBtn.addEventListener('click', () => {
            const msg = input.value;
            if (msg) {
                displayMessage(msg, "user");
                sendMessage(msg);
                input.value = '';                // Add loading state
                if (typeof window.addButtonLoading === 'function') {
                    window.addButtonLoading(sendBtn, 'Sending...');
                }            }
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                const msg = input.value;
                if (msg) {
                    displayMessage(msg, "user");
                    sendMessage(msg);
                    input.value = '';
                }
            }
        });
    }
    // Show session id in UI
    const sessionInfo = document.getElementById('session-info');
    if (sessionInfo) {
        sessionInfo.textContent = `Session: ${sessionId}`;
    }

    document.getElementById('new-chat-btn').addEventListener('click', function() {
        sessionId = generateSessionId();
        localStorage.setItem('chat_session_id', sessionId);
        messageHistory = [];
        renderMessages();
        fetchHistory();
        // Optionally, update session info display
        const sessionInfo = document.getElementById('session-info');
        if (sessionInfo) {
            sessionInfo.textContent = `Session: ${sessionId}`;
        }
    });

    // MCP transport selection handler
    transportFieldsVisibility();
    // MCP UI handlers: submit add MCP, refresh list, and fetch tools
    const addForm = document.getElementById('add-mcp-form');
    if (addForm) {
        addForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const name = document.getElementById('mcp-name').value;
            const transport = document.getElementById('mcp-transport').value;
            const url = document.getElementById('mcp-url') ? document.getElementById('mcp-url').value : null;
            const command = document.getElementById('mcp-command') ? document.getElementById('mcp-command').value : null;
            const argsStr = document.getElementById('mcp-args') ? document.getElementById('mcp-args').value : null;
            let args = [];
            try { if (argsStr) args = JSON.parse(argsStr); } catch (err) { args = []; }
            const payload = { name, transport };
            // Basic client-side validation
            const statusDiv = document.getElementById('add-mcp-status');
            if (!name || !transport) {
                statusDiv.innerHTML = `<div class='text-danger'>Name and transport are required.</div>`;
                return;
            }
            if (transport === 'streamable_http' && (!url || url.trim().length === 0)) {
                statusDiv.innerHTML = `<div class='text-danger'>Endpoint URL is required for HTTP transport.</div>`;
                return;
            }
            if (transport === 'stdio' && (!command || command.trim().length === 0)) {
                statusDiv.innerHTML = `<div class='text-danger'>Command is required for STDIO transport.</div>`;
                return;
            }
            if (transport === 'streamable_http') payload.url = url;
            if (transport === 'stdio') {
                payload.command = command;
                payload.args = args;
            }
            try {
                const res = await fetch('/mcp', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
                const data = await res.json();
                const statusDiv = document.getElementById('add-mcp-status');
                if (data && data.success) {
                    statusDiv.innerHTML = `<div class='text-success'>Added MCP: ${name}</div>`;
                    await reloadAgent();
                    await fetchMcpList();
                } else {
                    statusDiv.innerHTML = `<div class='text-danger'>Failed to add MCP</div>`;
                }
            } catch (err) {
                const statusDiv = document.getElementById('add-mcp-status');
                statusDiv.innerHTML = `<div class='text-danger'>Error: ${err.message}</div>`;
            }
        });
    }

    const refreshMcpBtn = document.getElementById('refresh-mcps');
    if (refreshMcpBtn) {
        refreshMcpBtn.addEventListener('click', function() { fetchMcpList(); });
    }

    const refreshToolsBtn = document.getElementById('refresh-tools');
    if (refreshToolsBtn) {
        refreshToolsBtn.addEventListener('click', async () => { await fetchTools(); });
    }
    // Initial load
    fetchMcpList();
    fetchTools();

    // use selected model in model-select
    const modelSelect = document.getElementById('model-select');
    // send selected model on change to re create agent
    if (modelSelect) {
        modelSelect.addEventListener('change', async () => {
            await reloadAgent();
        });
    }
});

function transportFieldsVisibility() {
    var transportSelect = document.getElementById('mcp-transport');
    
    transportSelect.addEventListener('change', function() {
        var transport = this.value;
        var httpFields = document.querySelectorAll('[data-transport="http"]');
        var stdioFields = document.querySelectorAll('[data-transport="stdio"]');

        if (transport === 'streamable_http') {
            httpFields.forEach(field => field.style.display = 'block');
            stdioFields.forEach(field => field.style.display = 'none');
            // Set field validation/disabled attributes
            const url = document.getElementById('mcp-url');
            const cmd = document.getElementById('mcp-command');
            const args = document.getElementById('mcp-args');
            if (url) { url.required = true; url.disabled = false; }
            if (cmd) { cmd.required = false; cmd.disabled = true; }
            if (args) { args.required = false; args.disabled = true; }
        }else if (transport === 'stdio') {
            httpFields.forEach(field => field.style.display = 'none');
            stdioFields.forEach(field => field.style.display = 'block');
            // Set field validation/disabled attributes
            const url = document.getElementById('mcp-url');
            const cmd = document.getElementById('mcp-command');
            const args = document.getElementById('mcp-args');
            if (url) { url.required = false; url.disabled = true; }
            if (cmd) { cmd.required = true; cmd.disabled = false; }
            if (args) { args.required = false; args.disabled = false; }
        }else{
            httpFields.forEach(field => field.style.display = 'none');
            stdioFields.forEach(field => field.style.display = 'none');
            // Clear required/disabled
            const url = document.getElementById('mcp-url');
            const cmd = document.getElementById('mcp-command');
            const args = document.getElementById('mcp-args');
            if (url) { url.required = false; url.disabled = true; }
            if (cmd) { cmd.required = false; cmd.disabled = true; }
            if (args) { args.required = false; args.disabled = true; }
        }
    });

    // Trigger change event on page load to set initial visibility
    var event = new Event('change');
    transportSelect.dispatchEvent(event);
}

async function fetchMcpList() {
    try {
        const res = await fetch('/mcp/list');
        const data = await res.json();
        const list = document.getElementById('mcp-list');
        if (!list) return;
        list.innerHTML = '';
        (data.mcps || []).forEach(mcp => {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.innerHTML = `
                <div>
                    <div><strong>${mcp.name}</strong> <small class='text-muted'>(${mcp.transport})</small></div>
                    <div class='small text-muted'>${mcp.url || mcp.command || ''}</div>
                </div>
                <div class='btn-group'>
                    <button class='btn btn-sm btn-outline-secondary btn-test' data-id='${mcp.id}'>Test</button>
                    <button class='btn btn-sm btn-outline-danger btn-delete' data-id='${mcp.id}'>Delete</button>
                </div>
            `;
            list.appendChild(li);
        });
        // Attach handlers
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                if (!confirm('Delete MCP?')) return;
                await deleteMcp(id);
            });
        });
        document.querySelectorAll('.btn-test').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                testMcpById(id);
            });
        });
    } catch (err) {
        console.error('Failed to fetch MCP list', err);
    }
}

async function deleteMcp(id) {
    try {
        const res = await fetch('/mcp/' + id, { method: 'DELETE' });
        const data = await res.json();
        if (data && data.success) {
            await reloadAgent();
            fetchMcpList();
        } else {
            alert('Failed to delete MCP');
        }
    } catch (err) { alert('Error deleting MCP: ' + err.message); }
}

async function testMcpById(id) {
    // No direct test-by-id; fetch the MCP record and call /mcp/test
    try {
        const res = await fetch('/mcp/list');
        const data = await res.json();
        const mcp = (data.mcps || []).find(m => m.id == id);
        if (!mcp) return alert('MCP not found');
        const body = { name: mcp.name, transport: mcp.transport, url: mcp.url, command: mcp.command, args: mcp.args };
        const r = await fetch('/mcp/test', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        const d = await r.json();
        if (d.success) {
            alert('MCP test success. Tools: ' + JSON.stringify(d.tools));
        } else {
            alert('MCP test failed');
        }
    } catch (err) { alert('Error testing MCP: ' + err.message); }
}

async function reloadAgent() {
    try {
        // Call backend endpoint to reload MCP and recreate agent
        // send selected model as well
        let model_provider = null;
        const modelSelect = document.getElementById('model-select');
        if (modelSelect && modelSelect.value) {
            model_provider = modelSelect.value;
        }

        const res = await fetch('/mcp/reload-agent', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ model_provider }) });
        const data = await res.json();
        if (data && data.success) {
            console.log('Agent reloaded');
            const status = document.getElementById('add-mcp-status');
            if (status) status.innerHTML = '<div class="text-success">MCP reloaded and agent recreated</div>';
        } else {
            alert('Failed to reload agent: ' + (data.error || 'unknown'));
        }
    } catch (err) { alert('Error reloading agent: ' + err.message); }
}

async function fetchTools() {
    try {
        const res = await fetch('/mcp/tools');
        const data = await res.json();
        const list = document.getElementById('tools-list');
        if (!list) return;
        list.innerHTML = '';
        (data.tools || []).forEach(tool => {
            const li = document.createElement('li');
            li.className = 'list-group-item';
            li.textContent = `${tool.name} (${tool.id})`;
            list.appendChild(li);
        });
    } catch (err) { console.error('Failed to fetch tools', err); }
}