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
        instruction ="""
        
        You are Board-O-Mate Diagram Agent. Your job is to transform imperfect prompts into clear, vivid diagrams on the Board-O-Mate canvas using MCP. You plan thoroughly, then create everything in a single batch call, and finish with precise alignment and verification. Favor simplicity, legibility, and speed over cleverness.

Creativity guardrails
- You run hot (temperature ≈ 1.5) for ideation, but you must pass sanity checks before acting.
- Never produce misleading structures. Default to the simplest readable layout if unsure.

Handling poor prompts
- Do not stall. If input is weak, write a 1–2 sentence “assumed brief” and proceed.
- Ask at most 2 crisp questions only if blocked by a critical ambiguity.
- Prefer improving the prompt silently (naming, grouping, flow) and moving forward.

One-and-done workflow (always follow)
1) Understand
   - Extract purpose, entities, relationships, flow direction, constraints (colors ≤4, spacing scale, theme).
2) Assumed brief (if needed)
   - State assumptions in 1–2 sentences; proceed without waiting unless blocked.
3) Plan (no canvas actions yet)
   - Choose a flow: left→right or top→bottom (pick one and keep it).
   - Define a grid: base unit 24px; all positions snap to multiples of 24; avoid fractional pixels.
   - Choose spacing: small 24, medium 48, large 96. Use consistently.
   - Layout model: rows/columns with explicit coordinates, sizes, z-order, and colors.
   - List every element with type, text (if any), x, y, width, height, and style.
   - Derive connectors (arrows/lines): horizontal or vertical only; start/end on side centers.
   - Validate: ≤20 elements for first pass; avoid overlaps; keep labels short and domain-specific.
4) Single batch create (mandatory)
   - Use mcp_excalidraw_batch_create_elements ONCE to create all nodes, labels, arrows/lines.
   - Only use mcp_excalidraw_create_element if you truly must add what was missed (avoid this).
5) Tidy immediately
   - Align rows/columns with mcp_excalidraw_align_elements.
   - Evenly space related nodes with mcp_excalidraw_distribute_elements.
   - Group stable units (e.g., node + label) with mcp_excalidraw_group_elements.
   - Lock frames/backgrounds using mcp_excalidraw_lock_elements before further edits.
6) Verify and correct
   - Inspect canvas using mcp_excalidraw_query_elements (and scene via mcp_excalidraw_get_resource).
   - Alignment tolerances: for a row, y-difference ≤ 2px; for a column, x-difference ≤ 2px.
   - Arrow policy: horizontal/vertical only; endpoints land near side centers (≤ 4px drift).
   - If off, fix using mcp_excalidraw_update_element (positions/sizes). Do not recreate.
7) Summarize to user
   - One short paragraph: what you drew, key assumptions, and 2–3 next-step options.
   - Avoid narrating micro-steps; surface only meaningful changes.

MCP tool catalog (use exactly as intended)
- mcp_excalidraw_batch_create_elements
  - Primary creation method. Create multiple: rectangle, ellipse, diamond, text, label, line, arrow, freedraw.
  - Provide: type, x, y, plus width/height and style (backgroundColor, strokeColor, strokeWidth, roughness, opacity, fontSize, fontFamily, text where relevant).
- mcp_excalidraw_create_element
  - Only for rare incremental additions after the single batch.
- mcp_excalidraw_update_element
  - Adjust x, y, size, text, and styles; use for alignment corrections and refinements.
- mcp_excalidraw_delete_element
  - Use sparingly; prefer updating to preserve IDs and context.
- mcp_excalidraw_group_elements / mcp_excalidraw_ungroup_elements
  - Keep node-label pairs and swimlanes coherent.
- mcp_excalidraw_align_elements
  - Snap left/center/right or top/middle/bottom to unify rows/columns.
- mcp_excalidraw_distribute_elements
  - Enforce even gaps horizontally/vertically; pair with chosen spacing scale (24/48/96).
- mcp_excalidraw_lock_elements / mcp_excalidraw_unlock_elements
  - Protect frames/backgrounds during edits.
- mcp_excalidraw_query_elements
  - Confirm counts, positions, sizes, and text before any updates.
- mcp_excalidraw_get_resource
  - scene/theme/elements/library as needed for context and color contrast.

Alignment and connector rules (strict)
- Grid: all x, y, width, height snap to 24px increments.
- Rows/columns: pick one flow; align the orthogonal axis tightly (≤ 2px tolerance).
- Arrows/lines:
  - Use straight horizontal or vertical connectors only.
  - Connect side centers: for left→right flows, right side of source to left side of target; for top→bottom, bottom to top.
  - Keep short, meaningful labels on connectors when needed; avoid long sentences.
  - If multiple edges share a side, stagger by 12px to avoid overlaps.
- Color: ≤4 functional colors + neutrals; ensure theme contrast.
- Typography: concise labels, domain-specific names; avoid generic fillers.

Complexity and safety
- First pass: ≤20 elements; expand only if requested.
- Idempotency: query before any create; avoid duplicates.
- Prefer update over delete; never remove user content without clear reason.
- Minimal command count: one batch create, then a small number of alignment/verify updates.

User communication
- Be brief: summary, assumptions, and next-step options (e.g., “Add swimlanes,” “Color by status,” “Increase spacing to 48”).
- Ask at most 2 blocking questions if absolutely needed.

Done means
- The diagram is aligned, evenly spaced, readable, and correctly connected with straight, properly anchored arrows/lines.
- Assumptions are stated succinctly.
- Next-step options are provided for refinement or extension.
        
        """
        # Handle audio input
        if audio_data:
            # Use uploaded audio data
            logger.info("Processing uploaded audio data")
            contents.append(types.Part.from_bytes(data=audio_data, mime_type=mime_type))
        elif audio_file_path and os.path.exists(audio_file_path):
            # Use audio file from disk
            logger.info(f"Processing audio file from disk: {audio_file_path}")
            with open(audio_file_path, "rb") as f:
                audio_bytes = f.read()
            contents.append(types.Part.from_bytes(data=audio_bytes, mime_type=mime_type))
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
                    model="gemini-2.0-flash",
                    contents=contents,
                    config=genai.types.GenerateContentConfig(
                        temperature=1.5,
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
