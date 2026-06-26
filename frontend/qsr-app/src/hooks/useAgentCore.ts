import { useRef, useCallback } from "react";
import { WebSocketClient } from "@/lib/websocket";
import { getStoredSession } from "@/lib/cognito";
import { useChatStore } from "@/store/useChatStore";
import { useConfigStore } from "@/store/useConfigStore";

export function useAgentCore() {
  const {
    addMessage,
    markLastAssistantMessageComplete,
    setConnected,
    setRecording,
    setError,
    setCurrentTool,
    isRecording,
  } = useChatStore();

  const wsClientRef = useRef<WebSocketClient | null>(null);
  const recordingContextRef = useRef<AudioContext | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef<number>(0);

  const initWebSocket = useCallback(async () => {
    if (wsClientRef.current?.isConnected()) return;

    try {
      const { credentials, session } = getStoredSession();
      if (!credentials || !session) throw new Error("Authentication missing");

      const configStore = useConfigStore.getState().config;
      if (!configStore) throw new Error("Configuration not loaded");

      const websocketUrl = configStore.websocketUrl;
      const runtimeArn = configStore.runtimeArn;
      const region = configStore.region;

      const client = new WebSocketClient({
        websocketUrl,
        runtimeArn,
        credentials,
        region,
        accessToken: session.accessToken,
      });

      client.onConnected(() => {
        setConnected(true);
        setError(null);
      });

      client.onDisconnected(() => setConnected(false));
      client.onError((err) => setError(err.message));
      
      client.onTranscription((text, role) => addMessage(role, text, false, true));
      client.onResponse((text) => addMessage("assistant", text, false, false));
      client.onAudio((data) => playAudio(data));
      
      client.onInterruption(() => {
        if (playbackContextRef.current) {
          playbackContextRef.current.close();
          playbackContextRef.current = null;
          nextPlayTimeRef.current = 0;
        }
        markLastAssistantMessageComplete();
        addMessage("assistant", "[Interrupted]", false, true);
      });

      client.onTurnComplete(() => markLastAssistantMessageComplete());
      client.onToolStart((toolName) => setCurrentTool(toolName));
      client.onToolEnd(() => setCurrentTool(null));

      wsClientRef.current = client;
      await client.connect();

    } catch (err: any) {
      setError(err.message || "Failed to connect to AgentCore");
    }
  }, [addMessage, markLastAssistantMessageComplete, setConnected, setError, setCurrentTool]);

  const playAudio = async (audioData: ArrayBuffer) => {
    try {
      if (!playbackContextRef.current || playbackContextRef.current.state === "closed") {
        playbackContextRef.current = new AudioContext({ sampleRate: 16000 });
        nextPlayTimeRef.current = playbackContextRef.current.currentTime;
      }
      if (playbackContextRef.current.state === "suspended") {
        await playbackContextRef.current.resume();
      }

      const int16Array = new Int16Array(audioData);
      const float32Array = new Float32Array(int16Array.length);
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      const audioBuffer = playbackContextRef.current.createBuffer(1, float32Array.length, 16000);
      audioBuffer.getChannelData(0).set(float32Array);

      const currentTime = playbackContextRef.current.currentTime;
      if (nextPlayTimeRef.current < currentTime) {
        nextPlayTimeRef.current = currentTime;
      }

      const source = playbackContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(playbackContextRef.current.destination);
      source.start(nextPlayTimeRef.current);

      nextPlayTimeRef.current += audioBuffer.duration;
    } catch (err) {
      console.error("Audio playback error:", err);
    }
  };

  const startRecording = useCallback(async () => {
    try {
      if (!wsClientRef.current?.isConnected()) await initWebSocket();

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });

      const audioContext = new AudioContext();
      recordingContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (e) => {
        if (wsClientRef.current?.isConnected()) {
          const inputData = e.inputBuffer.getChannelData(0);
          const downsampleRatio = audioContext.sampleRate / 16000;
          const outputLength = Math.floor(inputData.length / downsampleRatio);
          const int16Data = new Int16Array(outputLength);

          for (let i = 0; i < outputLength; i++) {
            const sourceIndex = Math.floor(i * downsampleRatio);
            int16Data[i] = Math.max(-32768, Math.min(32767, inputData[sourceIndex] * 32768));
          }
          wsClientRef.current.sendAudio(int16Data.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      setRecording(true);
    } catch (err) {
      setError("Failed to access microphone");
    }
  }, [initWebSocket, setError, setRecording]);

  const stopRecording = useCallback(() => {
    if (recordingContextRef.current && isRecording) {
      recordingContextRef.current.close();
      recordingContextRef.current = null;
      setRecording(false);
    }
  }, [isRecording, setRecording]);

  const sendTextMessage = useCallback((text: string) => {
    if (!text.trim()) return;
    
    const doSend = () => {
      addMessage("user", text, false);
      wsClientRef.current?.sendText(text);
    };

    if (!wsClientRef.current?.isConnected()) {
      initWebSocket().then(() => doSend());
    } else {
      doSend();
    }
  }, [addMessage, initWebSocket]);

  return {
    startRecording,
    stopRecording,
    sendTextMessage,
  };
}
