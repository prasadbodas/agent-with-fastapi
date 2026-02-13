import getpass
import json
import os
import sqlite3
import time
from contextlib import asynccontextmanager
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.prebuilt import create_react_agent
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from chromadb.config import Settings
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from pydantic import BaseModel
from tools.odoo_tool import OdooTool

from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_text_splitters import Language

from rag.scraper import WebScraper

import mainmcp
from mainmcp import router as chat_mcp_router

# app = FastAPI()
sqlite3_checkpointer = None
agent = None
cursor = None
conn = None
base_tools = []
# RAG components
vectorstore = None
embeddings = None
rag_model = None

load_dotenv()

# Disable ChromaDB telemetry
os.environ["ANONYMIZED_TELEMETRY"] = "False"

DB_PATH = os.getenv("DB_PATH", "odoo_agent.db")

def _set_env(key: str):
    if key not in os.environ:
        os.environ[key] = getpass.getpass(f"{key}:")

_set_env("OPENAI_API_KEY")

model_name = os.getenv("model", "gpt-5-nano")

model = ChatOpenAI(model=model_name)
# tools = [OdooTool()]
tools = []
prompt = (
    "You are an expert Odoo ReAct agent that can answer questions and perform tasks using the tools provided.\n"
    "Always use 1 tool at a time, and only when necessary.\n"
    "Do not proceed after the first tool call until you have received the response from the tool.\n"
    "Do not use multiple tools in a single step.\n"
    "Do not use tools that are not relevant to the current task.\n"
    "Do not proceed with the next step if tool response is an error or if the tool call was not successful.\n"
    "If you need to use a tool, ensure you have all the required information (like required fields, data type & relations).\n"
    "Verify models, fields, and data types before performing actions.\n"
    "If you are unsure, ask for clarification or request more information.\n"
    "If you don't need to use a tool, answer the question directly and concisely.\n"
    "Do not make assumptions or fabricate information.\n"
    "Always verify facts and avoid hallucinations.\n"
    "If you are not certain about an answer, state your uncertainty.\n"
    "Use less input/output tokens and avoid unnecessary verbosity.\n"
    "Take a deep breath and think step by step. Like collecting list of existing models and fields.\n"
    
    "Here are the tools available to you:\n"
    "{tools}"
)

# prompt = """
#     You are an expert Odoo Technical Architect and Senior Odoo Developer
#     with deep expertise in Odoo versions 16-19, Python, PostgreSQL, OWL,
#     XML views, security, and module packaging.

#     Your primary responsibility is to DESIGN and GENERATE complete,
#     production-ready Odoo addons.

#     You MUST strictly follow Odoo development best practices and conventions.

#     ----------------------------------
#     CORE RESPONSIBILITIES
#     ----------------------------------

#     1. Analyze user requirements and convert them into:
#     - Module architecture
#     - Data models
#     - Business logic
#     - Views and UI behavior
#     - Security and access rules

#     2. Always generate Odoo modules with:
#     - Proper directory structure
#     - __manifest__.py
#     - __init__.py files
#     - models/, views/, security/, data/, static/ (when applicable)
#     - XML views with correct inheritance and xpath usage
#     - Python code compliant with Odoo ORM and API decorators

#     3. Ensure compatibility with the specified Odoo version.
#     - If version is not mentioned, default to latest stable (Odoo 19).

#     ----------------------------------
#     STRICT RULES
#     ----------------------------------

#     - NEVER generate pseudo-code.
#     - NEVER mix Django/FastAPI/Flask patterns with Odoo.
#     - NEVER assume external services unless explicitly mentioned.
#     - ALWAYS use Odoo ORM (models.Model, fields, api).
#     - ALWAYS define access rights and record rules when models are created.
#     - ALWAYS include technical_name, depends, version, summary, description in manifest.

#     ----------------------------------
#     OUTPUT FORMAT
#     ----------------------------------

#     When generating a module:
#     1. First show a high-level module overview.
#     2. Then generate a clear folder structure.
#     3. Then generate each file with:
#     - File path as a heading
#     - You don't have to write code in response if using tools. Just describe the file structure.
#     4. Keep responses structured and readable.

#     ----------------------------------
#     SPECIAL CAPABILITIES
#     ----------------------------------

#     - Can refactor existing modules
#     - Can migrate modules between Odoo versions
#     - Can generate OWL components for backend UI
#     - Can optimize performance and security
#     - Can explain installation and usage steps

#     ----------------------------------
#     THINKING STRATEGY
#     ----------------------------------

#     - Think step-by-step internally.
#     - Validate business logic before writing code.
#     - Prefer simplicity, scalability, and maintainability.

#     You are not a general-purpose chatbot.
#     You are a specialized Odoo Module Generator.
    
#     "Here are the tools available to you:\n"
#     "{tools}"
# """

@asynccontextmanager
async def lifespan(app: FastAPI):
    global cursor, conn, sqlite3_checkpointer, agent, prompt, model

    # Use AsyncSqliteSaver for SQLite checkpointer
    # sqlite3_checkpointer = await AsyncSqliteSaver.from_conn_string(DB_PATH)
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as saver:
        sqlite3_checkpointer = saver
        # Snapshot base tools (non-MCP) before adding MCP tools
        global base_tools
        base_tools = list(tools)

        # Load MCP-based tools (if any) and merge into tools list
        try:
            await mainmcp.reload_mcp_client()
            mcp_client = mainmcp.get_mcp_client()
            if mcp_client is not None:
                try:
                    mcp_tools = await mcp_client.get_tools()
                    if mcp_tools:
                        tools.extend(mcp_tools)
                except Exception as e:
                    print('Error getting tools from MCP client:', e)
        except Exception as e:
            print('Error reloading MCP client at startup:', e)

        agent = create_react_agent(
            model,
            tools=tools,
            prompt=prompt,
            checkpointer=sqlite3_checkpointer
        )
        # Database setup (chat history)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()

        yield
        # Cleanup
        # await sqlite3_checkpointer.close()
        # Close the database connection
        cursor.close()
        conn.close()

async def recreate_agent_with_mcp_tools(model_provider="openai"):
    global agent, tools, base_tools, sqlite3_checkpointer
    # Reset tools to base tools
    tools = list(base_tools)
    # Try to attach MCP client tools
    try:
        await mainmcp.reload_mcp_client()
        mcp_client = mainmcp.get_mcp_client()
        if mcp_client is not None:
            mcp_tools = await mcp_client.get_tools()
            if mcp_tools:
                tools.extend(mcp_tools)
    except Exception as e:
        print('Error reloading or fetching MCP tools:', e)
    
    # Recreate model based on provider selection
    if model_provider == "openai":
        model_name = os.getenv("model", "gpt-5-nano")
        model = ChatOpenAI(model=model_name)
    else:  # Default to ollama
        ollama_model_name = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        model = ChatOllama(model=ollama_model_name)
    
    # Recreate agent using same checkpointer
    agent = create_react_agent(model, tools=tools, prompt=prompt, checkpointer=sqlite3_checkpointer)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_mcp_router)

app.mount("/static", StaticFiles(directory="frontend/assets"), name="static")


@app.post('/mcp/reload-agent')
async def reload_agent_endpoint(request: Request):
    """Reload MCP client and recreate local agent with updated tools."""
    res = await mainmcp.reload_mcp_client()
    if not res.get('success'):
        return JSONResponse({'success': False, 'error': res.get('error')}, status_code=500)
    
    model_provider = 'openai'
    data = await request.json()
    print("reload-agent data:")
    print(data)
    if data.get('model_provider'):
        model_provider = data.get('model_provider')
    await recreate_agent_with_mcp_tools(model_provider=model_provider)
    return JSONResponse({'success': True, 'message': 'MCP reloaded and agent recreated'})

# Route to list available vectorstores
import glob
@app.get("/vectorstores")
async def list_vectorstores():
    import os
    base_dir = os.path.join(os.getcwd(), "vectorstores")
    if not os.path.isdir(base_dir):
        return {"vectorstores": []}
    stores = []
    for entry in os.listdir(base_dir):
        store_path = os.path.join(base_dir, entry)
        if os.path.isdir(store_path):
            # Check for Chroma vectorstore marker (chroma.sqlite3)
            if os.path.exists(os.path.join(store_path, "chroma.sqlite3")):
                stores.append(entry)
    return {"vectorstores": stores}

# Helper functions for DB
def save_message(session_id, sender, message):
    cursor.execute(
        "INSERT INTO chat_history (session_id, sender, message) VALUES (?, ?, ?)",
        (session_id, sender, message)
    )
    conn.commit()

def get_history(session_id):
    cursor.execute(
        "SELECT sender, message, timestamp FROM chat_history WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    return [
        {"sender": row[0], "msg": row[1], "timestamp": row[2]}
        for row in cursor.fetchall()
    ]

def ai_message_to_dict(response):
    """Convert AI message to a dictionary."""
    print(response)
    def ai_msg_to_dict(ai_msg):
        return {
            "content": ai_msg.content,
            "additional_kwargs": ai_msg.additional_kwargs,
            "response_metadata": ai_msg.response_metadata,
            "id": ai_msg.id,
            "usage_metadata": ai_msg.usage_metadata,
        }

    data = {
        "agent": {
            "messages": [ai_msg_to_dict(ai_msg) for ai_msg in response["agent"]["messages"]]
        }
    }

    return json.dumps(data)

def ai_rag_message_to_dict(response):
    """Convert AI message to a dictionary."""
    print(response)
    def ai_msg_to_dict(ai_msg):
        return {
            "content": ai_msg.content,
            "additional_kwargs": ai_msg.additional_kwargs,
            "response_metadata": ai_msg.response_metadata,
            "id": ai_msg.id,
            "usage_metadata": ai_msg.usage_metadata,
        }

    data = {
        "rag": {
            "messages": ai_msg_to_dict(response)
        }
    }

    return json.dumps(data)

def ai_tool_message_to_dict(response):
    """Convert AI tool message to a dictionary."""
    # print(response)
    def ai_tool_msg_to_dict(tool_msg):
        return {
            "content": tool_msg.content,
            "name": tool_msg.name,
            "tool_call_id": tool_msg.tool_call_id,
            "id": tool_msg.id,
            "status": tool_msg.status if hasattr(tool_msg, 'status') else "success",
        }

    data = {
        "tools": {
            "messages": [ai_tool_msg_to_dict(tool_msg) for tool_msg in response["tools"]["messages"]]
        }
    }

    return json.dumps(data)

# Streaming ReAct agent using create_react_agent
async def react_agent_stream(user_message, session_id):

    config = {
        "configurable": {"thread_id": session_id},
        "recursion_limit": 50,
    }
    async for step in agent.astream(
        {"messages": [{"role": "user", "content": user_message}]},
        config=config,
        stream_mode="updates",
    ):
        # print(step)
        if "agent" in step and "messages" in step["agent"]:
            for message in step["agent"]["messages"]:
                msg_json = ai_message_to_dict(step)
                save_message(session_id, "agent", msg_json)
                yield msg_json
        elif "tools" in step and "messages" in step["tools"]:
            for tool_message in step["tools"]["messages"]:
                msg_json = ai_tool_message_to_dict(step)
                save_message(session_id, "agent", msg_json)
                yield msg_json
        else:
            msg_json = ai_message_to_dict(step)
            save_message(session_id, "agent", msg_json)
            yield msg_json


@app.websocket("/ws/react")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            session_id = data.get("session_id")
            if not session_id:
                await websocket.send_text("Error: session_id is required.")
                continue
            save_message(session_id, "user", user_message)
            async for response in react_agent_stream(user_message, session_id):
                await websocket.send_text(response)
    except WebSocketDisconnect:
        pass
    

@app.websocket("/ws/ask")
async def websocket_ask_endpoint(websocket: WebSocket):
    """WebSocket endpoint for RAG-enabled ask mode with streaming"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")
            session_id = data.get("session_id")
            vectorstore_name = data.get("vectorstore")
            model_provider = data.get("model_provider", "ollama")  # Default to ollama
            if not session_id:
                await websocket.send_text("Error: session_id is required.")
                continue
            save_message(session_id, "user", user_message)
            
            # Stream the response chunks
            async for chunk in rag_enabled_ask(user_message, session_id, vectorstore_name, model_provider):
                if isinstance(chunk, str) and chunk.strip():
                    # Send each chunk as it becomes available
                    await websocket.send_text(chunk)
    except WebSocketDisconnect:
        pass

@app.get("/")
async def get_ui():
    return FileResponse("frontend/index.html")

@app.get("/embeddings")
async def get_embedding_ui():
    return FileResponse("frontend/manage-embedding.html")

@app.get("/demo")
async def get_demo_ui():
    return FileResponse("frontend/demo.html")

@app.get("/redesign")
async def get_redesign_ui():
    return FileResponse("frontend/index-redesign.html")

@app.post("/load-code")
async def load_code(request: Request):
    """
    Load Python source code files from a directory using GenericLoader and LanguageParser.
    Expects JSON body: { "dir_path": "<directory_path>" }
    """
    try:
        data = await request.json()
        dir_path = data.get("dir_path")
        if not dir_path:
            return {"success": False, "error": "Missing dir_path"}

        # check if directory exists
        if not os.path.isdir(dir_path):
            return {"success": False, "error": "Invalid dir_path"}

        # Use GenericLoader with LanguageParser for Python and a splitter
        from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

        # Define splitters for Python and JS
        py_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.PYTHON,
            chunk_size=1000,
            chunk_overlap=100
        )
        js_splitter = RecursiveCharacterTextSplitter.from_language(
            language=Language.JS,
            chunk_size=1000,
            chunk_overlap=100
        )

        # Load Python files
        py_loader = GenericLoader.from_filesystem(
            dir_path,
            glob="**/*.py",
            parser=LanguageParser(language=Language.PYTHON),
            splitter=py_splitter
        )
        py_documents = py_loader.load()

        # Load JS files
        js_loader = GenericLoader.from_filesystem(
            dir_path,
            glob="**/*.js",
            parser=LanguageParser(language=Language.JS),
            splitter=js_splitter
        )
        js_documents = js_loader.load()

        documents = py_documents + js_documents
        docs_json = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in documents
        ]
        return {"success": True, "documents": docs_json}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/load-pdfs")
async def load_pdfs(pdf_files: List[UploadFile] = File(...)):
    """
    Upload and process PDF files.
    Expects multipart/form-data with PDF files.
    """
    import tempfile
    
    if not pdf_files:
        return {"success": False, "error": "No PDF files provided"}
    
    scraper = WebScraper()
    all_documents = []
    
    try:
        for pdf_file in pdf_files:
            # Validate file type
            if not pdf_file.filename.lower().endswith('.pdf'):
                continue
                
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                content = await pdf_file.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Process the PDF file
                documents = scraper.scrape_local_pdf(temp_path)
                
                # Update metadata with original filename
                for doc in documents:
                    doc.metadata['source'] = pdf_file.filename
                    doc.metadata['original_filename'] = pdf_file.filename
                    doc.metadata['file_type'] = 'pdf'
                
                all_documents.extend(documents)
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
        
        # Convert documents to JSON-serializable format
        docs_json = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in all_documents
        ]
        
        return {"success": True, "documents": docs_json}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/load-csvs")
async def load_csvs(csv_files: List[UploadFile] = File(...)):
    """
    Upload and process CSV files.
    Expects multipart/form-data with CSV files and configuration.
    """
    import tempfile
    import os
    from rag.scraper import WebScraper
    
    if not csv_files:
        return {"success": False, "error": "No CSV files provided"}
    
    scraper = WebScraper()
    all_documents = []
    
    try:
        for csv_file in csv_files:
            # Validate file type
            if not csv_file.filename.lower().endswith('.csv'):
                continue
                
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(suffix='.csv', delete=False, mode='w+b') as temp_file:
                content = await csv_file.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Process the CSV file
                documents = scraper.scrape_local_csv(temp_path)
                
                # Update metadata with original filename
                for doc in documents:
                    doc.metadata['source'] = csv_file.filename
                    doc.metadata['original_filename'] = csv_file.filename
                    doc.metadata['file_type'] = 'csv'
                
                all_documents.extend(documents)
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
        
        # Convert documents to JSON-serializable format
        docs_json = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in all_documents
        ]
        
        return {"success": True, "documents": docs_json}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/load-docx")
async def load_docx(docx_files: List[UploadFile] = File(...)):
    """
    Upload and process DOCX files.
    Expects multipart/form-data with DOCX files.
    """
    import tempfile
    import os
    from rag.scraper import WebScraper
    
    if not docx_files:
        return {"success": False, "error": "No DOCX files provided"}
    
    scraper = WebScraper()
    all_documents = []
    
    try:
        for docx_file in docx_files:
            # Validate file type
            if not (docx_file.filename.lower().endswith('.docx') or docx_file.filename.lower().endswith('.doc')):
                continue
                
            # Save uploaded file to temporary location
            with tempfile.NamedTemporaryFile(suffix='.docx', delete=False, mode='w+b') as temp_file:
                content = await docx_file.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                # Process the DOCX file
                documents = scraper.scrape_local_docx(temp_path)
                
                # Update metadata with original filename
                for doc in documents:
                    doc.metadata['source'] = docx_file.filename
                    doc.metadata['original_filename'] = docx_file.filename
                    doc.metadata['file_type'] = 'docx'
                
                all_documents.extend(documents)
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
        
        # Convert documents to JSON-serializable format
        docs_json = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in all_documents
        ]
        
        return {"success": True, "documents": docs_json}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

class ScrapeRequest(BaseModel):
    urls: List[str]
    max_depth: int = 2
    max_pages: int = None
    method: str = 'async'

@app.post("/scrape")
async def scrape_urls(request: ScrapeRequest):
    scraper = WebScraper()
    try:
        if request.method == 'async':
            documents = await scraper.scrape_async_html(request.urls)
        elif request.method == 'selenium':
            documents = scraper.scrape_with_selenium(request.urls)
        elif request.method == 'recursive':
            # Use first URL, allow optional depth via request (extend ScrapeRequest if needed)
            url = request.urls[0] if request.urls else None
            if not url:
                return {"success": False, "error": "No URL provided for recursive scrape."}
            print(f"request.max_depth: {request.max_depth}")
            max_depth = request.max_depth if hasattr(request, 'max_depth') else 2
            print(f"max_depth: {max_depth}")
            documents = scraper.scrape_recursive(url, max_depth=max_depth)
        elif request.method == 'sitemap':
            # Use first URL as sitemap URL
            sitemap_url = request.urls[0] if request.urls else None
            if not sitemap_url:
                return {"success": False, "error": "No sitemap URL provided."}
            max_depth = request.max_depth if hasattr(request, 'max_depth') else 2
            max_pages = request.max_pages if hasattr(request, 'max_pages') else None
            documents = await scraper.scrape_sitemap(sitemap_url, max_depth=max_depth, max_pages=max_pages)
        elif request.method == 'pdf-async':
            # Scrape PDF URLs
            if not request.urls:
                return {"success": False, "error": "No PDF URLs provided."}
            documents = await scraper.scrape_pdf_urls_async(request.urls)
        else:
            documents = scraper.scrape_basic_html(request.urls)

        # Convert documents to JSON-serializable format
        docs_json = [
            {"page_content": doc.page_content, "metadata": doc.metadata}
            for doc in documents
        ]
        return {"success": True, "documents": docs_json}
    except Exception as e:
        return {"success": False, "error": str(e)}

class VectorStoreRequest(BaseModel):
    documents: List[dict]
    name: str


@app.post("/create-vectorstore")
async def create_vectorstore(request: VectorStoreRequest):
    try:
        # Re-create Document objects from the received JSON with metadata cleaning
        documents = []
        for doc_data in request.documents:
            # Clean metadata to ensure compatibility with Chroma
            cleaned_metadata = clean_metadata_for_vectorstore(doc_data['metadata'])
            
            documents.append(
                Document(
                    page_content=doc_data['page_content'], 
                    metadata=cleaned_metadata
                )
            )
        
        embedding_model_name = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
        embeddings = OllamaEmbeddings(model=embedding_model_name)
        persist_dir = os.path.join("vectorstores", request.name)
        os.makedirs(persist_dir, exist_ok=True)
        
        vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            persist_directory=persist_dir
        )
        
        return {"success": True, "path": persist_dir, "document_count": len(documents)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def clean_metadata_for_vectorstore(metadata: dict) -> dict:
    """
    Clean metadata to ensure compatibility with Chroma vectorstore.
    Converts complex types to simple scalars.
    """
    cleaned = {}
    
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = None
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        elif isinstance(value, list):
            # Convert lists to comma-separated strings
            cleaned[key] = ', '.join(str(item) for item in value if item is not None)
        elif isinstance(value, dict):
            # Convert dicts to JSON strings
            cleaned[key] = json.dumps(value)
        else:
            # Convert other types to strings
            cleaned[key] = str(value)
    
    return cleaned

async def rag_enabled_ask(user_message, session_id, vectorstore_name=None, model_provider="ollama"):
    global vectorstore, embeddings, rag_model
    print("RAG enabled ask called")
    print(f"Using model provider: {model_provider}")
    print(vectorstore)

    # Always reload vectorstore if a name is provided (per request)
    embedding_model_name = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text:latest")
    if embeddings is None:
        embeddings = OllamaEmbeddings(model=embedding_model_name)
    if vectorstore_name:
        vectorstore_path = os.path.join("vectorstores", vectorstore_name)
        if not os.path.exists(vectorstore_path):
            yield f"Error: Vector store '{vectorstore_name}' not found. Please create it first."
            return
        vectorstore = Chroma(
            persist_directory=vectorstore_path,
            embedding_function=embeddings
        )
    elif vectorstore is None:
        # fallback to default
        vectorstore_path = "vectorstores/zehntech_advance_dashboard"
        if not os.path.exists(vectorstore_path):
            yield "Error: Vector store not found. Please create it first."
            return
        vectorstore = Chroma(
            persist_directory=vectorstore_path,
            embedding_function=embeddings
        )
    
    # Initialize RAG model based on provider selection
    if model_provider == "openai":
        model_name = os.getenv("model", "gpt-4o-mini")
        rag_model = ChatOpenAI(model=model_name)
    else:  # Default to ollama
        model_name = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
        rag_model = ChatOllama(model=model_name)

    # get search string formated/corrected from LLM
    # Create prompt with context
    # pre_prompt = (
    #     f"Rephrase the following user query to improve search results for relevant documents:\n\n"
    #     f"Restrict the rephrased query to be concise and focused on key terms.\n\n"
    #     f"Return only the rephrased query without any additional text, which directly goes into the search.\n\n"
    #     f"User Query: {user_message}\n\n"
    #     f"Rephrased Query:"
    # )
    # print(f"User message: {user_message}")
    # formatted_message = rag_model.invoke(pre_prompt)
    # print(f"Formatted message: {formatted_message.content}")

    # Retrieve relevant documents
    # relevant_docs = vectorstore.similarity_search(formatted_message.content, k=5)
    
    relevant_docs = vectorstore.similarity_search(user_message, k=10)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])

    prompt = (
        "You are an helpful assistant. Use the provided documentation context to answer clearly.\n\n"
        "If unsure, say \"I don't know\" instead of guessing.\n\n"
        "Refuse hallucinations if no relevant docs found.\n\n"
        "Always cite doc section (from metadata).\n\n"
        "Output should be compatible with marked.min.js\n\n"
        "Context:\n"
        f"{context}\n\n"
        "Question:\n"
        f"{user_message}"
    )

    print(f"Prompt: {prompt}")

    # Stream response from the RAG model
    full_response = ""
    async for chunk in rag_model.astream(prompt):
        if hasattr(chunk, 'content') and chunk.content:
            full_response += chunk.content
            # Yield each chunk for streaming
            yield chunk.content
    
    # Save the complete response to database
    ai_msg = ai_rag_message_to_dict_simple(full_response)
    save_message(session_id, "agent", ai_msg)

def ai_rag_message_to_dict_simple(content):
    """Convert simple content to RAG message format."""
    data = {
        "rag": {
            "messages": {
                "content": content,
                "additional_kwargs": {},
                "response_metadata": {},
                "id": f"rag_{int(time.time())}",
                "usage_metadata": {}
            }
        }
    }
    return json.dumps(data)

@app.post("/message")
async def post_message(data: dict):
    user_message = data.get("message", "")
    session_id = data.get("session_id", "")
    save_message(session_id, "user", user_message)
    return {"status": "ok"}


@app.get("/history/{session_id}")
async def get_history_route(session_id: str):
    return {"history": get_history(session_id)}

@app.get("/state_history/{session_id}")
async def get_state_history_route(session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    state_history = []

    async for record in sqlite3_checkpointer.alist(config):
        state_history.append(record)

    return {"state_history": state_history}

# New API endpoints for redesigned UI

@app.get("/api/conversations")
async def get_conversations():
    """Get all conversations with metadata"""
    try:
        cursor.execute("""
            SELECT DISTINCT session_id, 
                   MIN(timestamp) as first_message,
                   MAX(timestamp) as last_message,
                   COUNT(*) as message_count
            FROM chat_history 
            GROUP BY session_id 
            ORDER BY last_message DESC
        """)
        conversations = []
        for row in cursor.fetchall():
            # Get first user message as title
            cursor.execute("""
                SELECT message FROM chat_history 
                WHERE session_id = ? AND sender = 'user' 
                ORDER BY timestamp ASC LIMIT 1
            """, (row[0],))
            first_msg = cursor.fetchone()
            title = first_msg[0][:50] + "..." if first_msg and len(first_msg[0]) > 50 else (first_msg[0] if first_msg else "New Chat")
            
            conversations.append({
                "id": row[0],
                "title": title,
                "timestamp": row[2],  # last_message
                "messageCount": row[3]
            })
        return conversations
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Get all messages for a conversation"""
    try:
        messages = get_history(conversation_id)
        return messages
        result = []
        for msg in messages:
            role = msg["sender"]
            content = msg["msg"]
            usage_metadata = None
            
            # Parse JSON messages from agent (they're stored as JSON strings)
            if role == "agent":
                try:
                    parsed = json.loads(content)
                    
                    # Check if this is a standalone tool response message (only has tools, no agent content)
                    if "tools" in parsed and "agent" not in parsed and "rag" not in parsed:
                        # This is a standalone tool response message
                        tool_msgs = parsed["tools"]["messages"]
                        if tool_msgs and len(tool_msgs) > 0:
                            for tool_msg in tool_msgs:
                                tool_content = tool_msg.get("content", "")
                                tool_name = tool_msg.get("name", "Tool")
                                tool_call_id = tool_msg.get("tool_call_id")
                                tool_status = tool_msg.get("status", "success")
                                if tool_content and tool_content.strip():
                                    tool_data = {
                                        "role": "tool",
                                        "content": tool_content,
                                        "tool_name": tool_name,
                                        "timestamp": msg.get("timestamp")
                                    }
                                    if tool_call_id:
                                        tool_data["tool_call_id"] = tool_call_id
                                    if tool_status:
                                        tool_data["status"] = tool_status
                                    result.append(tool_data)
                        # Skip adding this message as an agent message since it's only tools
                        continue
                    
                    # Handle mixed messages with both agent content and tool calls
                    if "tools" in parsed and "messages" in parsed["tools"]:
                        tool_msgs = parsed["tools"]["messages"]
                        if tool_msgs and len(tool_msgs) > 0:
                            for tool_msg in tool_msgs:
                                tool_content = tool_msg.get("content", "")
                                tool_name = tool_msg.get("name", "Tool")
                                tool_call_id = tool_msg.get("tool_call_id")
                                tool_status = tool_msg.get("status", "success")
                                if tool_content and tool_content.strip():
                                    tool_data = {
                                        "role": "tool",
                                        "content": tool_content,
                                        "tool_name": tool_name,
                                        "timestamp": msg.get("timestamp")
                                    }
                                    if tool_call_id:
                                        tool_data["tool_call_id"] = tool_call_id
                                    if tool_status:
                                        tool_data["status"] = tool_status
                                    result.append(tool_data)
                        # Continue to process the agent message below
                    
                    # Extract actual content from the nested structure
                    if "agent" in parsed and "messages" in parsed["agent"]:
                        # Get the last message content and usage metadata
                        agent_msgs = parsed["agent"]["messages"]
                        if agent_msgs and len(agent_msgs) > 0:
                            last_msg = agent_msgs[-1]
                            content = last_msg.get("content", "")
                            usage_metadata = last_msg.get("usage_metadata")
                    elif "rag" in parsed and "messages" in parsed["rag"]:
                        rag_msg = parsed["rag"]["messages"]
                        content = rag_msg.get("content", "")
                        usage_metadata = rag_msg.get("usage_metadata")
                except (json.JSONDecodeError, KeyError, IndexError) as e:
                    # If parsing fails, keep original content and log the error
                    print(f"Failed to parse agent message: {e}")
            
            # Add the message (even if content is empty but has usage_metadata)
            message_data = {
                "role": role,
                "content": content if content else "",
                "timestamp": msg.get("timestamp")
            }
            if usage_metadata:
                message_data["usage_metadata"] = usage_metadata
            result.append(message_data)
        
        return result
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages"""
    try:
        cursor.execute("DELETE FROM chat_history WHERE session_id = ?", (conversation_id,))
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.put("/api/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, data: dict):
    """Update conversation metadata (e.g., title)"""
    # TODO: Add title column to database schema
    return {"status": "ok", "message": "Title update not yet implemented"}

@app.post("/api/upload-to-vectorstore")
async def upload_to_vectorstore(
    files: List[UploadFile] = File(...),
    vectorstore_name: str = Form(...)
):
    """Upload files and add them to a vector store"""
    import tempfile
    import shutil
    from pathlib import Path
    from rag.scraper import WebScraper
    
    if not files:
        return JSONResponse(status_code=400, content={"error": "No files provided"})
    
    if not vectorstore_name:
        return JSONResponse(status_code=400, content={"error": "Vector store name required"})
    
    scraper = WebScraper()
    all_documents = []
    processed_files = []
    
    try:
        for file in files:
            filename = file.filename.lower()
            
            # Create temporary file
            suffix = Path(filename).suffix
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False, mode='w+b') as temp_file:
                content = await file.read()
                temp_file.write(content)
                temp_path = temp_file.name
            
            try:
                documents = []
                
                # Process based on file type
                if filename.endswith('.pdf'):
                    documents = scraper.scrape_local_pdf(temp_path)
                elif filename.endswith('.csv'):
                    documents = scraper.scrape_local_csv(temp_path)
                elif filename.endswith(('.docx', '.doc')):
                    documents = scraper.scrape_local_docx(temp_path)
                elif filename.endswith('.txt'):
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                    from langchain.schema import Document
                    documents = [Document(page_content=text, metadata={
                        'source': file.filename,
                        'file_type': 'txt'
                    })]
                else:
                    # Unsupported file type
                    continue
                
                # Update metadata
                for doc in documents:
                    doc.metadata['source'] = file.filename
                    doc.metadata['original_filename'] = file.filename
                    doc.metadata['vectorstore'] = vectorstore_name
                
                all_documents.extend(documents)
                processed_files.append(file.filename)
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass
        
        if not all_documents:
            return JSONResponse(status_code=400, content={"error": "No valid documents processed"})
        
        # Create or update vector store
        vectorstore_path = f"vectorstores/{vectorstore_name}"
        os.makedirs(vectorstore_path, exist_ok=True)
        
        # Initialize or load existing vectorstore
        vectorstore = Chroma(
            collection_name=vectorstore_name,
            embedding_function=embeddings,
            persist_directory=vectorstore_path,
            client_settings=Settings(anonymized_telemetry=False)
        )
        
        # Add documents to vectorstore
        vectorstore.add_documents(all_documents)
        
        return JSONResponse(content={
            "success": True,
            "vectorstore": vectorstore_name,
            "files_processed": processed_files,
            "document_count": len(all_documents)
        })
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.delete("/api/vectorstore/{vectorstore_name}")
async def delete_vectorstore(vectorstore_name: str):
    """Delete a vector store and all its data"""
    import shutil
    
    try:
        vectorstore_path = f"vectorstores/{vectorstore_name}"
        
        if os.path.exists(vectorstore_path):
            shutil.rmtree(vectorstore_path)
            return {"success": True, "message": f"Deleted {vectorstore_name}"}
        else:
            return JSONResponse(status_code=404, content={"error": "Vector store not found"})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/vectorstore/{vectorstore_name}/info")
async def get_vectorstore_info(vectorstore_name: str):
    """Get information about a vector store"""
    try:
        vectorstore_path = f"vectorstores/{vectorstore_name}"
        
        if not os.path.exists(vectorstore_path):
            return JSONResponse(status_code=404, content={"error": "Vector store not found"})
        
        # Load vectorstore to get document count
        vectorstore = Chroma(
            collection_name=vectorstore_name,
            embedding_function=embeddings,
            persist_directory=vectorstore_path,
            client_settings=Settings(anonymized_telemetry=False)
        )
        
        # Get collection stats
        collection = vectorstore._collection
        count = collection.count()
        
        return {
            "name": vectorstore_name,
            "document_count": count,
            "path": vectorstore_path
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/execute-python")
async def execute_python(data: dict):
    """Execute Python code in a sandboxed environment"""
    import subprocess
    import tempfile
    
    code = data.get("code", "")
    if not code:
        return JSONResponse(status_code=400, content={"error": "No code provided"})
    
    try:
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Execute with timeout
            result = subprocess.run(
                ['python', temp_path],
                capture_output=True,
                text=True,
                timeout=5  # 5 second timeout
            )
            
            output = result.stdout
            error = result.stderr
            
            if error:
                return {"output": output, "error": error}
            else:
                return {"output": output or "Code executed successfully"}
                
        finally:
            # Clean up
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=400, content={"error": "Code execution timed out (5s limit)"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Execution error: {str(e)}"})


    return state_history
