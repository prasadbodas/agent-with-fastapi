const wsUrl = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/react';
let socket;

let messageHistory = [];
let sessionId = localStorage.getItem('chat_session_id') || generateSessionId();
let currentMode = localStorage.getItem('chat_mode') || 'agent';
localStorage.setItem('chat_session_id', sessionId);
localStorage.setItem('chat_mode', currentMode);

function generateSessionId() {
    return 'sess-' + Math.random().toString(36).substr(2, 16);
    //sess-fxst5i1vm7b
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
        messageHistory.forEach(({msg, sender, type}) => {
            console.log('Rendering message:', msg, sender, type);
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
                    if (msg_json.type === "rag_response") {
                        if (msg_json.partial && msg_json.content) {
                            // For streaming RAG responses, append content
                            if (!div.ragContent) div.ragContent = "";
                            div.ragContent += msg_json.content;
                            putInnerHTMLOfMessage(div, div.ragContent);
                        } else if (msg_json.complete_response) {
                            // For complete RAG response, use the full response
                            putInnerHTMLOfMessage(div, msg_json.complete_response);
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
                    // If JSON parsing fails, treat as plain text (for simple responses)
                    console.log('Failed to parse as JSON, treating as plain text:', e);
                    putInnerHTMLOfMessage(div, msg);
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
        try {
            // const data = JSON.parse(event.data);

            messageHistory.push({msg: event.data, sender: "agent"});
            renderMessages();
        } catch (e) {
            // Fallback for plain text messages
            messageHistory.push({msg: event.data, sender: "agent"});
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
        let payload = {
            message,
            session_id: sessionId,
            mode: currentMode
        };
        // If in RAG mode, add selected vectorstore
        if (currentMode === 'ask') {
            const select = document.getElementById('vectorstore-select');
            if (select && select.value) {
                payload.vectorstore = select.value;
            }
        }
        socket.send(JSON.stringify(payload));
    } else {
        console.error('WebSocket is not open');
    }
}

window.addEventListener('DOMContentLoaded', () => {
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

    // Load vectorstores and update visibility
    loadVectorstores();
    updateVectorstoreVisibility();

    // Add event listeners for mode change
    const modeRadios = document.querySelectorAll('input[name="mode"]');
    modeRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                currentMode = this.value;
                localStorage.setItem('chat_mode', currentMode);
                updateModeInfo();
                updateVectorstoreVisibility();
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
                input.value = '';
            }
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
});

// Fetch and populate vectorstore options
function loadVectorstores() {
    fetch('/vectorstores')
        .then(res => res.json())
        .then(data => {
            const select = document.getElementById('vectorstore-select');
            if (select && data.vectorstores) {
                select.innerHTML = '';
                data.vectorstores.forEach(store => {
                    const opt = document.createElement('option');
                    opt.value = store;
                    opt.textContent = store;
                    select.appendChild(opt);
                });
            }
        });
}

// Show/hide vectorstore select based on mode
function updateVectorstoreVisibility() {
    const group = document.getElementById('vectorstore-select-group');
    if (group) {
        group.style.display = (currentMode === 'ask') ? '' : 'none';
    }
}