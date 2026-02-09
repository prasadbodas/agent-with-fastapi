# Quick Start Guide - Redesigned UI

## 🚀 Getting Started

### 1. Start the Server
```bash
cd c:\python\langgraph\ollama-chat
python mainchat.py
```

### 2. Access the Redesigned Interface
Open your browser and navigate to:
```
http://localhost:8000/redesign
```

## ✨ Key Features to Try

### 💬 Conversations
- **Create New Chat:** Click the "New Chat" button in the sidebar
- **Switch Conversations:** Click any conversation in the sidebar
- **Search:** Type in the search box to filter conversations by title
- **Rename:** Hover over a conversation and click the pencil icon
- **Delete:** Hover over a conversation and click the trash icon

### 📝 Messaging
- **Send Message:** Type your message and press Enter
- **New Line:** Press Shift+Enter to add a line break
- **Stop Generation:** Click the stop button (appears during generation)
- **Copy Message:** Hover over any message and click the clipboard icon
- **Regenerate:** Click the refresh icon on assistant messages
- **Edit Message:** Click the pencil icon to edit any message
- **Delete Message:** Click the trash icon to remove a message

### 📎 File Attachments
- **Attach Files:** Click the paperclip icon in the input area
- **Remove Files:** Click the X on any attached file chip
- **Note:** Backend processing integration in progress

### 🗄️ Knowledge Bases (Vector Stores)
- **View Available Stores:** Click the database badge in the header
- **Select Store:** Click on a store in the right panel to activate it
- **Active Indicator:** Selected store shows in header badge

### 🛠️ MCP Tools
- **View Available Tools:** Click the tools badge in the header
- **Enable/Disable:** Toggle the switch next to any tool
- **Active Count:** Number of enabled tools shows in header badge

### 🎨 Theme
- **Switch Theme:** Click the sun/moon icon in the sidebar footer
- **Automatic Save:** Your theme preference is saved automatically

### 📱 Mobile Experience
- **Hamburger Menu:** On mobile, tap the menu icon to open the sidebar
- **Swipe Gestures:** Swipe from left to open sidebar (planned)
- **Responsive Layout:** All features work on mobile devices

## 🎯 What's New vs Old Interface

| Feature | Old UI | New UI |
|---------|--------|--------|
| **Pages** | 3 separate pages | 1 unified page |
| **Navigation** | Page reloads | Instant switching |
| **Conversations** | No history | Full history with search |
| **Message Actions** | Limited | Copy, regenerate, edit, delete |
| **Stop Generation** | Not available | ✅ Implemented |
| **File Upload** | Separate page | Inline attachment |
| **Tools/Knowledge** | Separate pages | Side panel |
| **Mobile** | Limited | Fully responsive |
| **Theme** | Light only (old) | Light + Dark |
| **State Management** | Vanilla JS | Alpine.js (reactive) |

## 🔧 Troubleshooting

### WebSocket Connection Issues
If you see "Connection lost. Reconnecting..." toast:
1. Check if the server is running
2. Verify no firewall is blocking WebSocket connections
3. Refresh the page to force reconnection

### Conversations Not Loading
If the sidebar shows "No conversations yet":
1. This is normal for first-time use
2. Click "New Chat" to create your first conversation
3. Existing chats from the old UI will be imported automatically

### Messages Not Sending
1. Ensure you have text in the input field
2. Check WebSocket connection status in browser console (F12)
3. Verify server is running and accessible

### Theme Not Persisting
1. Check browser's localStorage is enabled
2. Try clearing cache and reloading

## 📊 What's Implemented (6/10 Tasks Complete)

### ✅ Completed
1. **Unified SPA Architecture** - All features in one page
2. **Conversation Sidebar** - History, search, organization
3. **Backend APIs** - Full conversation management
4. **Message Interactions** - Copy, regenerate, edit, delete, stop
5. **Alpine.js State** - Reactive UI with centralized state
6. **Mobile Responsive** - Works on all screen sizes

### ⏳ In Progress
7. **Inline Context Management** - File upload UI ready, backend integration needed
8. **Tools Panel** - Basic UI complete, execution indicators planned
9. **Canvas/Artifacts** - Planned for code execution results
10. **Performance & Polish** - Virtual scrolling, accessibility audit, testing

## 🎓 Tips & Tricks

### Keyboard Shortcuts
- `Enter` - Send message
- `Shift+Enter` - New line in message
- `Esc` - Close modals/panels (planned)
- `Ctrl+K` - Search conversations (planned)

### Suggested Prompts
When starting a new chat, click any suggested prompt to quickly test the system:
- "Explain quantum computing"
- "Write Python code"
- "Plan a trip"
- "AI news summary"

### Context Indicators
The header shows what context is active:
- **Database badge** - Vector store for RAG
- **Tools badge** - Number of enabled MCP tools

### Conversation Organization
Conversations are automatically grouped:
- **Today** - Conversations from today
- **Yesterday** - Conversations from yesterday
- **Last 7 Days** - Recent conversations
- **Older** - Everything else

## 📚 Documentation

For complete technical details, see:
- **UI_REDESIGN.md** - Full implementation documentation
- **UI_MODERNIZATION.md** - Previous modernization work
- **METADATA_ENHANCEMENTS.md** - RAG metadata improvements

## 🐛 Known Issues

1. **Conversation Title Editing** - Currently saves to localStorage only, not backend
2. **File Upload Backend** - UI ready but processing not fully integrated
3. **Tool Toggle Persistence** - Resets on page reload
4. **Message Edit Regeneration** - Doesn't regenerate response from edited point

These will be addressed in upcoming tasks (5, 6, 10).

## 🎉 Next Features Coming

1. **Drag-Drop File Upload** - Drop files directly into chat
2. **Tool Execution Indicators** - See which tools are running
3. **Artifacts Panel** - View code execution results side-by-side
4. **Virtual Scrolling** - Smooth performance with 1000+ messages
5. **Voice Input** - Speak your messages
6. **Conversation Branching** - Create alternative conversation paths

## 💡 Feedback

Found a bug or have a suggestion? The redesign is actively being developed!
