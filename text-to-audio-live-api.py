"""
Command Line Chat with Gemini 2.0 Flash exp Audio Response (Gemini Developer API only)

Requirements:
- google-genai
- pyaudio

Setup:
1. Install dependencies: `pip install google-genai pyaudio`
2. Set the GOOGLE_API_KEY environment variable with your API key from Google AI Studio.

Usage:
1. Run the script
2. Type your message at the "You: " prompt and press Enter
3. Listen to Gemini's response
4. Type "quit" to exit
"""

import asyncio
import os
import pyaudio
from google import genai
from google.genai.types import Modality
from dotenv import load_dotenv

# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 24000  # Gemini uses 24kHz for audio output
CHUNK_SIZE = 1024

load_dotenv() 

# Get API key from environment
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise EnvironmentError("GOOGLE_API_KEY is not set in environment variables.")

# Initialize Gemini client using API Key
client = genai.Client(
    api_key=api_key,
    http_options={"api_version": "v1alpha"}
)

MODEL = "models/gemini-2.0-flash-exp"
CONFIG = {"generation_config": {"response_modalities": ["AUDIO"]}}

# Initialize PyAudio
pya = pyaudio.PyAudio()

async def play_audio(audio_queue):
    """Plays audio chunks from the queue until receiving None signal."""
    stream = await asyncio.to_thread(
        pya.open,
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        output=True,
    )

    try:
        while True:
            audio_bytes = await audio_queue.get()
            if audio_bytes is None:
                break
            await asyncio.to_thread(stream.write, audio_bytes)
    finally:
        stream.stop_stream()
        stream.close()

async def chat_session():
    """Manages the chat session with Gemini, handling text input and audio output."""
    audio_queue = asyncio.Queue()

    try:
        async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
            audio_task = asyncio.create_task(play_audio(audio_queue))
            print("Start chatting! Type 'quit' to exit.")

            while True:
                user_message = await asyncio.to_thread(input, "You: ")
                if user_message.lower() == "quit":
                    break

                await session.send(input=user_message or "Hello", end_of_turn=True)

                async for response in session.receive():
                    if audio_data := response.data:
                        audio_queue.put_nowait(audio_data)
                    elif text := response.text:
                        print("Gemini:", text, end="")

                print()

            await session.close()
            await audio_queue.put(None)
            await audio_task

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Chat session ended.")

if __name__ == "__main__":
    try:
        asyncio.run(chat_session())
    except KeyboardInterrupt:
        print("\nChat terminated by user.")
    finally:
        pya.terminate()
        print("Resources cleaned up.")
