import os
import asyncio
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Create server parameters for stdio connection
server_params = StdioServerParameters(
    command="node",  # Executable
    args=["C:\\Users\\sanji\\OneDrive\\Documents\\GitHub\\mcp_excalidraw-main\\dist\\index.js"],  # MCP Server
    env=None,  # Optional environment variables
)   

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Prompt to get the weather for the current day in London.
            prompt = f"Using MCP Board-O-Mate, represent this simple physics problem. A ball is rolling on the ground at 20 m/s. Add as much detail into the diagram which you will be drawing and also display the problem itself as text. Visualize this problem in a vivid manner and bring it to life using the Board-O-Mate canvas. DO NOT USE CREATE_ELEMENT TOOL WITH THE TYPE AS 'freedraw'. DO NOT ASK FOLLOW UP QUESTIONS JUST DO WHAT I SAY."

            # Initialize the connection between client and server
            await session.initialize()

            # Send request to the model with MCP function declarations
            response = await client.aio.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=2,
                    tools=[session],  # uses the session, will automatically call the tool
                    # Uncomment if you **don't** want the SDK to automatically call the tool
                    # automatic_function_calling=genai.types.AutomaticFunctionCallingConfig(
                    #     disable=True
                    # ),
                ),
            )
            print(response.text)

# Start the asyncio event loop and run the main function
asyncio.run(run())