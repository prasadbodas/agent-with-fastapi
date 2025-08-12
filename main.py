import os
import getpass
from dotenv import load_dotenv

from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from odoo_tool import OdooTool

load_dotenv()

def _set_env(key: str):
    if key not in os.environ:
        os.environ[key] = getpass.getpass(f"{key}:")

_set_env("OPENAI_API_KEY")

model_name = os.getenv("model", "gpt-5-nano")
model = ChatOpenAI(model=model_name)

tools = [
    OdooTool()
]

prompt = (
    "You are expert Odoo 17 agent and web search assistant.\n"
    "You are a helpful ReAct agent that can answer questions and perform tasks using the tools provided.\n"
    "You can use the DuckDuckGo search tool to find information on the web, and the Odoo tool to interact with an Odoo instance.\n"
    "Always collect necessary information(like fields,data type & relations) before using a tool.\n"
    "When you need to use a tool, call it in your response.\n"
    "If you don't need to use a tool, just answer the question directly.\n"
    "If you are unsure about something, ask for clarification.\n"
    "You can also ask the user for more information if needed.\n"
    "Always use less input/output tokens and avoid unnecessary verbosity.\n"
    "Think step by step and reason about your actions.\n"
    
    "Here are the tools available to you:\n"
    "{tools}"
)

agent = create_react_agent(model, tools=tools, prompt=prompt)

def main():
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit", "q"}:
            break
        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            stream_mode="updates",
            recursion_limit=10
        ):
            print(chunk)
            print("////////////////////////////\n")
            if chunk and "agent" in chunk and "messages" in chunk["agent"]:
                for message in chunk["agent"]["messages"]:
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for tool_call in message.tool_calls:
                            print(f"Tool call: {tool_call['name']} with args {tool_call['args']}")
                    elif hasattr(message, "content") and message.content.strip():
                        print("Assistant:", message.content.strip())
                    elif hasattr(message, "tool_results"):
                        for tool_result in message.tool_results:
                            print(f"Tool result: {tool_result}")
                    elif hasattr(message, "error"):
                        print(f"Error: {message.error}")

if __name__ == "__main__":
    main()