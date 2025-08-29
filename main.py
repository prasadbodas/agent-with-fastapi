import os
import getpass
from dotenv import load_dotenv

from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from tools.odoo_tool import OdooTool
from langgraph.checkpoint.memory import InMemorySaver

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
    "You are an expert Odoo ReAct agent that can answer questions and perform tasks using the tools provided.\n"
    "Always collect and use necessary information (like required fields, data type & relations) before using a tool.\n"
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

agent = create_react_agent(
    model,
    tools=tools,
    prompt=prompt,
    checkpointer=InMemorySaver()
)

def main():
    while True:
        user_input = input("You: ")
        if user_input.lower() in {"exit", "quit", "q"}:
            break

        config = {"configurable": {"thread_id": "1"}}

        for chunk in agent.stream(
            {"messages": [{"role": "user", "content": user_input}]},
            config=config,
            stream_mode="updates",
            recursion_limit=10,
        ):
            print(chunk)
            print("////////////////////////////\n")
            if chunk and "agent" in chunk and "messages" in chunk["agent"]:
                for message in chunk["agent"]["messages"]:
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for tool_call in message.tool_calls:
                            print(f"Tool call: {tool_call['name']} with args {tool_call['args']}")
                    elif hasattr(message, "content") and message.content.strip():
                        print("Assistant: ", message.content.strip())
                    elif hasattr(message, "tool_results"):
                        for tool_result in message.tool_results:
                            print(f"Tool result: {tool_result}")
                    elif hasattr(message, "error"):
                        print(f"Error: {message.error}")

                    # Log token counts if available
                    usage = getattr(message, "usage_metadata", None)
                    if usage:
                        print(
                            f"Tokens - Input: {usage.get('input_tokens')}, "
                            f"Output: {usage.get('output_tokens')}, "
                            f"Total: {usage.get('total_tokens')}"
                        )

if __name__ == "__main__":
    main()