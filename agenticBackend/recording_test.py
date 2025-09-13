import pyaudio
import wave
import requests
import io
import time
import os
from datetime import datetime

class AudioRecorder:
    def __init__(self):
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1  # Mono
        self.fs = 44100  # Record at 44100 samples per second
        self.seconds = 5  # Recording duration
        self.filename = "temp_recording.wav"
        
    def record_audio(self):
        """Record audio for specified duration"""
        print("🎤 Starting audio recording...")
        print("Speak now! Recording for 5 seconds...")
        
        # Initialize PyAudio
        p = pyaudio.PyAudio()
        
        # Open stream
        stream = p.open(format=self.sample_format,
                       channels=self.channels,
                       rate=self.fs,
                       frames_per_buffer=self.chunk,
                       input=True)
        
        frames = []
        
        # Record for specified duration
        for i in range(0, int(self.fs / self.chunk * self.seconds)):
            data = stream.read(self.chunk)
            frames.append(data)
            
            # Show progress
            progress = (i + 1) / int(self.fs / self.chunk * self.seconds) * 100
            print(f"\rRecording... {progress:.1f}%", end="", flush=True)
        
        print("\n✅ Recording completed!")
        
        # Stop and close the stream
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save the recorded data as a WAV file
        wf = wave.open(self.filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        print(f"💾 Audio saved as: {self.filename}")
        return self.filename
    
    def send_to_api(self, audio_file_path=None):
        """Send recorded audio to Flask API"""
        if audio_file_path is None:
            audio_file_path = self.filename
            
        if not os.path.exists(audio_file_path):
            print(f"❌ Audio file not found: {audio_file_path}")
            return False
            
        print("📤 Sending audio to Flask API...")
        
        try:
            # Read the audio file
            with open(audio_file_path, 'rb') as audio_file:
                files = {'audio': (audio_file_path, audio_file, 'audio/wav')}
                
                # Send to Flask API
                response = requests.post(
                    'http://localhost:5000/process-audio-upload',
                    files=files,
                    timeout=60
                )
            
            print(f"📡 API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print("✅ Audio processed successfully!")
                    print(f"🤖 Response: {result.get('response', 'No response')}")
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
            print(f"❌ Error sending audio to API: {e}")
            return False
    
    def cleanup(self):
        """Remove temporary audio file"""
        if os.path.exists(self.filename):
            os.remove(self.filename)
            print(f"🗑️ Cleaned up temporary file: {self.filename}")

def main():
    print("🎙️ Audio Recorder for Flask API")
    print("=" * 40)
    
    # Check if Flask server is running
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            print("✅ Flask server is running")
        else:
            print("⚠️ Flask server responded but may have issues")
    except requests.exceptions.ConnectionError:
        print("❌ Flask server is not running!")
        print("Please start the Flask server first:")
        print("python flask_app.py")
        return
    
    print()
    
    # Create recorder instance
    recorder = AudioRecorder()
    
    try:
        # Record audio
        audio_file = recorder.record_audio()
        
        print()
        
        # Send to API
        success = recorder.send_to_api(audio_file)
        
        if success:
            print("\n🎉 Audio recording and processing completed successfully!")
        else:
            print("\n💥 Something went wrong during processing")
            
    except KeyboardInterrupt:
        print("\n⏹️ Recording interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Clean up
        recorder.cleanup()

if __name__ == "__main__":
    main()
