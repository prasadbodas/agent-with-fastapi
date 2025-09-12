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

# app = FastAPI()
sqlite3_checkpointer = None
agent = None
cursor = None
conn = None
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    global cursor, conn, sqlite3_checkpointer, agent, prompt, model

    # Use AsyncSqliteSaver for SQLite checkpointer
    # sqlite3_checkpointer = await AsyncSqliteSaver.from_conn_string(DB_PATH)
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as saver:
        sqlite3_checkpointer = saver
        agent = create_react_agent(
            model,
            tools=tools,
            prompt=prompt,
            checkpointer=sqlite3_checkpointer
        )

        # Database setup
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

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory="frontend/assets"), name="static")

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

    config = {"configurable": {"thread_id": session_id}}
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

    return state_history
