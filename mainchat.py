import os
import getpass
from dotenv import load_dotenv
import sqlite3
import json

from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from odoo_tool import OdooTool
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# app = FastAPI()
sqlite3_checkpointer = None
agent = None
cursor = None
conn = None

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "odoo_agent.db")

def _set_env(key: str):
    if key not in os.environ:
        os.environ[key] = getpass.getpass(f"{key}:")

_set_env("OPENAI_API_KEY")

model_name = os.getenv("model", "gpt-5-nano")

model = ChatOpenAI(model=model_name)
tools = [OdooTool()]
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

app.mount("/static", StaticFiles(directory="frontend"), name="static")

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


@app.get("/")
async def get_ui():
    return FileResponse("frontend/index.html")


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
