import asyncio
# from fastapi import FastAPI
from langchain_ollama import ChatOllama
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# app = FastAPI()

client = MultiServerMCPClient(
    {
        # "weather": {
        #     "url": "http://localhost:8001/mcp",
        #     "transport": "streamable_http",
        # },
        # "odoo": {
        #     "url": "http://localhost:8002/mcp",
        #     "transport": "streamable_http",
        # }
        "filesystem": {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "C:\\Users\\PrasadBodas\\Desktop\\temp\\dir-for-mcp-1"
            ]
        }
    }
)

async def main():
    
    tools = await client.get_tools()
    model = ChatOllama(model="qwen3:4b")
    agent = create_react_agent(model, tools)
    response = await agent.ainvoke({"messages": "create a text file named hello.txt with content 'Hello from MCP!'"})
    
    print(response)
    for message in response['messages']:
        print(message.content)

if __name__ == "__main__":
    asyncio.run(main())