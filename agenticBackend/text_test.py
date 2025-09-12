import requests
import json
import time

class TextProcessor:
    def __init__(self, api_url="http://localhost:5000"):
        self.api_url = api_url
        
    def check_server_health(self):
        """Check if Flask server is running"""
        try:
            response = requests.get(f'{self.api_url}/health', timeout=5)
            if response.status_code == 200:
                print("✅ Flask server is running")
                return True
            else:
                print("⚠️ Flask server responded but may have issues")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Flask server is not running!")
            print("Please start the Flask server first:")
            print("python flaskApp.py")
            return False
    
    def process_text(self, text_prompt):
        """Send text prompt to Flask API for processing"""
        if not text_prompt.strip():
            print("❌ Please provide a non-empty text prompt")
            return False
            
        print(f"📝 Processing text: '{text_prompt}'")
        print("📤 Sending to Flask API...")
        
        try:
            # Prepare the request data
            data = {
                "text_prompt": text_prompt
            }
            
            # Send to Flask API
            response = requests.post(
                f'{self.api_url}/process-text',
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=60
            )
            
            print(f"📡 API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Text processed successfully!")
                    print(f"🤖 Response: {result.get('response', 'No response')}")
                    print(f"⏰ Timestamp: {result.get('timestamp', 'Unknown')}")
                    return True
                else:
                    print(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ API request failed with status: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print("❌ Could not connect to Flask API. Make sure the server is running on http://localhost:5000")
            return False
        except Exception as e:
            print(f"❌ Error sending text to API: {e}")
            return False

def main():
    print("📝 Text Processor for Flask API")
    print("=" * 40)
    
    # Create processor instance
    processor = TextProcessor()
    
    # Check server health
    if not processor.check_server_health():
        return
    
    print()
    
    # Interactive text input loop
    while True:
        try:
            print("\n" + "="*50)
            print("Enter your text prompt (or 'quit' to exit):")
            text_input = input("> ").strip()
            
            if text_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if not text_input:
                print("⚠️ Please enter some text")
                continue
            
            print()
            success = processor.process_text(text_input)
            
            if success:
                print("\n🎉 Text processing completed successfully!")
            else:
                print("\n💥 Something went wrong during processing")
                
        except KeyboardInterrupt:
            print("\n⏹️ Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
