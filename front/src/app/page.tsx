'use client'

import { useEffect, useRef, useState } from 'react'

export default function Home() {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const [recording, setRecording] = useState(false)

  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL
    if (!wsUrl) {
      console.error('NEXT_PUBLIC_WS_URL не задана в .env.local')
      return
    }

    const ws = new WebSocket(wsUrl)
    ws.binaryType = 'arraybuffer'


    ws.onopen = () => {
      console.log('[WS] Открыт 🎉')
      setSocket(ws)
    }

    ws.onmessage = (event) => {
      const audioBlob = new Blob([event.data], { type: 'audio/ogg; codecs=opus' })
      const audioUrl = URL.createObjectURL(audioBlob)
      const audio = new Audio(audioUrl)
      audio.play()
    }

    return () => {
      ws.close()
    }
  }, [])

  const chunks: Blob[] = []

  const startRecording = async () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket не готов 😢')
      return
    }

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const mediaRecorder = new MediaRecorder(stream, {
      mimeType: 'audio/webm;codecs=opus',
    })

    mediaRecorderRef.current = mediaRecorder

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        chunks.push(event.data)
      }
    }

    mediaRecorder.onstop = async () => {
      const fullBlob = new Blob(chunks, { type: 'audio/webm' })
      const buffer = await fullBlob.arrayBuffer()
      socket.send(buffer) // теперь отправляем один полноценный файл
      chunks.length = 0
    }

    mediaRecorder.start()
    setRecording(true)
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }


  return (
    <main className="w-full h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center text-center gap-4">
        <h1 className="text-xl font-bold mb-4">Voice Assistant with OpenAI</h1>
        <small>(Click start recording, say your question, click stop recording)</small>
        <button
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
          onClick={recording ? stopRecording : startRecording}
        >
          {recording ? 'Stop recording' : 'Start recording'}
        </button>
      </div>
    </main>
  )
}
