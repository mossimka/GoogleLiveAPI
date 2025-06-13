import io
import os
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

origins = [
    "http://localhost:5173",
    "http://207.154.221.138:3010"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import wave

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    buffer = io.BytesIO()  # <-- инициализация переменной buffer

    try:
        while True:
            data = await websocket.receive_bytes()
            buffer.write(data)

            # Если собралось хотя бы 100KB, можно распознавать
            if buffer.tell() > 100_000:
                buffer.seek(0)

                # Читаем и сохраняем в temp файл
                current_buffer = buffer.read()
                buffer.seek(0)
                buffer.truncate(0)  # очищаем буфер

                with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
                    f.write(current_buffer)
                    temp_path = f.name

                # 1. Распознаём речь через Whisper (speech-to-text)
                with open(temp_path, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="json"
                    )
                    user_input = transcription.text

                print(f"[whisper] -> {user_input}")

                # 2. Отправляем текст в GPT
                chat_response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You're a friendly person. Answer in less than 60 words. Answer shortly and clearly"
                            ),
                        },
                        {"role": "user", "content": user_input},
                    ]
                )
                answer = chat_response.choices[0].message.content
                print(f"[gpt] -> {answer}")

                # 3. Преобразуем ответ в голос через TTS
                tts_response = client.audio.speech.create(
                    model="tts-1-hd",
                    voice="shimmer",
                    input=answer
                )

                # 4. Отправляем голос обратно клиенту
                await websocket.send_bytes(tts_response.content)

    except WebSocketDisconnect:
        print("Клиент отключился")
