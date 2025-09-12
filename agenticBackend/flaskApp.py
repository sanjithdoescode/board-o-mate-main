import os
import asyncio
import json
import logging
from datetime import datetime
from io import BytesIO
from flask import Flask, request, jsonify
from flask_cors import CORS
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend integration

# Initialize Gemini client
client = genai.Client(api_key="AIzaSyBVQZ6bw5n7dACioMacuiURsZd1lefge_U")

# MCP server parameters
server_params = StdioServerParameters(
    command="node",
    args=["D:\\mcp_excalidraw-main\\dist\\index.js"],
    env=None,
)

# Global event loop for async operations
loop = None

def get_or_create_loop():
    """Get or create an event loop for async operations"""
    global loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

async def process_request(audio_data=None, audio_file_path=None, text_prompt=None, mime_type="audio/mp3"):
    """
    Process the request with dynamic input
    
    Args:
        audio_data: Raw audio bytes (if uploading file)
        audio_file_path: Path to audio file on disk
        text_prompt: Text prompt to use instead of audio
        mime_type: MIME type of the audio file
    """
    try:
        logger.info(f"Processing request - audio_data: {bool(audio_data)}, audio_file_path: {audio_file_path}, text_prompt: {bool(text_prompt)}")
        
        contents = []
        
        # Handle audio input
        if audio_data:
            # Use uploaded audio data
            logger.info("Processing uploaded audio data")
            contents.append(types.Part.from_bytes(data=audio_data, mime_type=mime_type))
            instruction = "Transcribe the audio above. Treat the transcription as the user's request and then answer it. Draw the diagram properly for the given request, by using the MCP tools available to you."
        elif audio_file_path and os.path.exists(audio_file_path):
            # Use audio file from disk
            logger.info(f"Processing audio file from disk: {audio_file_path}")
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type))
            instruction = "Transcribe the audio above. Treat the transcription as the user's request and then answer it. Draw the diagram properly for the given request, by using the MCP tools available to you."
        elif text_prompt:
            # Use text prompt directly
            logger.info(f"Processing text prompt: {text_prompt[:100]}...")
            # Add the text prompt as content
            contents.append(text_prompt)
            instruction = "Draw the diagram properly for the given request, by using the MCP tools available to you."
        else:
            raise ValueError("No valid input provided. Please provide audio_data, audio_file_path, or text_prompt.")
        
        # Add instruction to contents
        contents.append(instruction)
        
        logger.info(f"Starting MCP session with {len(contents)} content parts...")
        # Process with MCP and Gemini
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                logger.info("Initializing MCP session...")
                # Initialize MCP
                await session.initialize()
                
                logger.info("Sending request to Gemini...")
                # Send contents to Gemini with MCP tools
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=genai.types.GenerateContentConfig(
                        temperature=0,
                        tools=[session],
                    ),
                )
                
                logger.info("Request completed successfully")
                return {
                    "success": True,
                    "response": response.text,
                    "timestamp": datetime.now().isoformat()
                }
                
    except Exception as e:
        logger.error(f"Error in process_request: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/process-audio-file', methods=['POST'])
def process_audio_file():
    """Process audio file from disk"""
    try:
        data = request.get_json()
        audio_file_path = data.get('audio_file_path')
        mime_type = data.get('mime_type', 'audio/mp3')
        
        if not audio_file_path:
            return jsonify({"error": "audio_file_path is required"}), 400
        
        # Run the async function using the event loop
        loop = get_or_create_loop()
        result = loop.run_until_complete(process_request(
            audio_file_path=audio_file_path,
            mime_type=mime_type
        ))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_audio_file: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/process-audio-upload', methods=['POST'])
def process_audio_upload():
    """Process uploaded audio file"""
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Read audio data
        audio_data = audio_file.read()
        mime_type = audio_file.content_type or 'audio/mp3'
        
        # Run the async function using the event loop
        loop = get_or_create_loop()
        result = loop.run_until_complete(process_request(
            audio_data=audio_data,
            mime_type=mime_type
        ))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_audio_upload: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/process-text', methods=['POST'])
def process_text():
    """Process text prompt directly"""
    try:
        data = request.get_json()
        text_prompt = data.get('text_prompt')
        
        if not text_prompt:
            return jsonify({"error": "text_prompt is required"}), 400
        
        # Run the async function using the event loop
        loop = get_or_create_loop()
        result = loop.run_until_complete(process_request(
            text_prompt=text_prompt
        ))
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_text: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/process', methods=['POST'])
def process_generic():
    """Generic endpoint that accepts any type of input"""
    try:
        data = request.get_json()
        
        # Get the event loop
        loop = get_or_create_loop()
        
        # Check for different input types
        if 'audio_file_path' in data:
            # Process audio file from disk
            result = loop.run_until_complete(process_request(
                audio_file_path=data['audio_file_path'],
                mime_type=data.get('mime_type', 'audio/mp3')
            ))
        elif 'text_prompt' in data:
            # Process text prompt
            result = loop.run_until_complete(process_request(
                text_prompt=data['text_prompt']
            ))
        else:
            return jsonify({"error": "Please provide either 'audio_file_path' or 'text_prompt'"}), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in process_generic: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask API server...")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /process-audio-file - Process audio file from disk")
    print("  POST /process-audio-upload - Process uploaded audio file")
    print("  POST /process-text - Process text prompt")
    print("  POST /process - Generic endpoint for any input type")
    print("\nExample usage:")
    print("  curl -X POST http://localhost:5000/process-text -H 'Content-Type: application/json' -d '{\"text_prompt\": \"Draw a flowchart for user login process\"}'")
    print("  curl -X POST http://localhost:5000/process-audio-file -H 'Content-Type: application/json' -d '{\"audio_file_path\": \"ball_command.mp3\"}'")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
