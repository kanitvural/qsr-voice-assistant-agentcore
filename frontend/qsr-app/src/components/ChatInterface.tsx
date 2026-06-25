"use client";
/**
 * Chat Interface Component
 * 
 * Main ordering interface with voice and text modes.
 * Handles audio capture, playback, and message history.
 */

import { useState, useEffect, useRef } from 'react';
import { WebSocketClient } from '../services/WebSocketClient';
import type { AWSCredentials, AppSettings } from '../services/SettingsManager';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isAudio?: boolean;
  isComplete?: boolean; // Flag to indicate if message is finished streaming
}

interface ChatInterfaceProps {
  settings: AppSettings;
  credentials: AWSCredentials;
  accessToken: string;
  onSignOut: () => void;
}

export function ChatInterface({ 
  settings, 
  credentials, 
  accessToken,
  onSignOut
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [userLocation, setUserLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [currentTool, setCurrentTool] = useState<string | null>(null);
  const [showTextInput, setShowTextInput] = useState(false);

  const wsClientRef = useRef<WebSocketClient | null>(null);
  const recordingContextRef = useRef<AudioContext | null>(null);
  const playbackContextRef = useRef<AudioContext | null>(null);
  const nextPlayTimeRef = useRef<number>(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);

  // Get user's location on mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
          console.log('📍 User location obtained:', position.coords.latitude, position.coords.longitude);
        },
        (error) => {
          console.warn('⚠️ Geolocation permission denied or unavailable:', error.message);
          // Use default location if permission denied
          setUserLocation({ latitude: 32.7767, longitude: -96.7970 });
        },
        {
          enableHighAccuracy: true,
          timeout: 5000,
          maximumAge: 0
        }
      );
    } else {
      // Geolocation not supported
      setUserLocation({ latitude: 32.7767, longitude: -96.7970 });
    }
  }, []);

  // Initialize WebSocket connection
  const initWebSocket = async () => {
    if (wsClientRef.current?.isConnected()) {
      console.log('Already connected');
      return;
    }

    try {
      const client = new WebSocketClient({
        websocketUrl: settings.agentCore.websocketUrl,
        runtimeArn: settings.agentCore.runtimeArn,
        credentials,
        region: settings.cognito.region,
        accessToken,
        userLocation: userLocation || undefined
      });

      // Set up event handlers
      client.onConnected(() => {
        setIsConnected(true);
        setError(null);
        console.log('✅ Connected to AgentCore Runtime');
      });

      client.onDisconnected(() => {
        setIsConnected(false);
        console.log('❌ Disconnected from AgentCore Runtime');
      });

      client.onTranscription((text, role) => {
        addMessage(role, text, false, true); // User transcriptions are always complete
      });

      client.onResponse((text) => {
        addMessage('assistant', text, false, false); // Assistant responses stream, not complete yet
      });

      client.onAudio((audioData) => {
        playAudio(audioData);
      });

      client.onError((err) => {
        setError(err.message);
        console.error('WebSocket error:', err);
      });

      client.onInterruption(() => {
        // Stop all queued audio playback when interrupted
        if (playbackContextRef.current) {
          playbackContextRef.current.close();
          playbackContextRef.current = null;
          nextPlayTimeRef.current = 0;
        }
        // Mark current assistant message as complete when interrupted
        markLastAssistantMessageComplete();
        addMessage('assistant', '[Interrupted]', false, true);
      });

      client.onTurnComplete(() => {
        // Mark current assistant message as complete when turn ends
        markLastAssistantMessageComplete();
      });

      client.onToolStart((toolName) => {
        // Show tool execution banner
        setCurrentTool(toolName);
      });

      client.onToolEnd(() => {
        // Hide tool execution banner
        setCurrentTool(null);
      });

      wsClientRef.current = client;

      // Connect
      await client.connect();

    } catch (err) {
      setError('Failed to connect to AgentCore Runtime');
      console.error('Connection error:', err);
    }
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (role: 'user' | 'assistant', content: string, isAudio: boolean, isComplete: boolean = true) => {
    setMessages(prev => {
      // If this is an assistant message and the last message is also an incomplete assistant message,
      // append to it instead of creating a new one
      if (role === 'assistant' && prev.length > 0) {
        const lastMessage = prev[prev.length - 1];
        if (lastMessage.role === 'assistant' && !lastMessage.isComplete) {
          // Append to existing message with a space separator
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...lastMessage,
            content: lastMessage.content + ' ' + content,
            isComplete
          };
          return updated;
        }
      }
      
      // Otherwise, create a new message
      return [...prev, {
        role,
        content,
        timestamp: new Date(),
        isAudio,
        isComplete
      }];
    });
  };

  const markLastAssistantMessageComplete = () => {
    setMessages(prev => {
      if (prev.length === 0) return prev;
      const lastMessage = prev[prev.length - 1];
      if (lastMessage.role === 'assistant' && !lastMessage.isComplete) {
        const updated = [...prev];
        updated[updated.length - 1] = {
          ...lastMessage,
          isComplete: true
        };
        return updated;
      }
      return prev;
    });
  };

  const getToolDisplayName = (toolName: string): string => {
    // Convert tool names to user-friendly display names
    const toolMap: Record<string, string> = {
      'get_customer_location': '📍 Getting your location...',
      'qsr-backend-api___GetPreviousOrders': '📋 Loading previous orders...',
      'qsr-backend-api___GetNearestLocations': '🗺️ Finding nearby restaurants...',
      'qsr-backend-api___GetMenu': '📖 Loading menu...',
      'qsr-backend-api___AddToCart': '🛒 Adding to cart...',
      'qsr-backend-api___PlaceOrder': '✅ Placing your order...',
      'qsr-backend-api___GetCustomerProfile': '👤 Loading your profile...',
      'qsr-backend-api___GeocodeAddress': '📍 Looking up address...',
      'qsr-backend-api___FindLocationAlongRoute': '🛣️ Finding locations along route...'
    };
    
    return toolMap[toolName] || `🔧 ${toolName}...`;
  };

  const handleSendText = () => {
    if (!inputText.trim() || !wsClientRef.current?.isConnected()) return;

    addMessage('user', inputText, false);
    wsClientRef.current.sendText(inputText);
    setInputText('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendText();
    }
  };

  const startRecording = async () => {
    try {
      // Request wake lock to keep screen on during voice interaction
      if ('wakeLock' in navigator) {
        try {
          wakeLockRef.current = await navigator.wakeLock.request('screen');
          console.log('🔒 Screen wake lock acquired');
          
          // Listen for wake lock release
          wakeLockRef.current.addEventListener('release', () => {
            console.log('🔓 Screen wake lock released');
          });
        } catch (err) {
          console.warn('⚠️ Wake lock request failed:', err);
          // Continue anyway - wake lock is a nice-to-have, not critical
        }
      }

      // Connect WebSocket if not connected
      if (!wsClientRef.current?.isConnected()) {
        await initWebSocket();
      }

      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });

      // Create AudioContext for raw PCM processing
      const audioContext = new AudioContext();
      recordingContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (e) => {
        if (wsClientRef.current?.isConnected()) {
          const inputData = e.inputBuffer.getChannelData(0);
          
          // Downsample to 16kHz
          const downsampleRatio = audioContext.sampleRate / 16000;
          const outputLength = Math.floor(inputData.length / downsampleRatio);
          const int16Data = new Int16Array(outputLength);
          
          for (let i = 0; i < outputLength; i++) {
            const sourceIndex = Math.floor(i * downsampleRatio);
            int16Data[i] = Math.max(-32768, Math.min(32767, inputData[sourceIndex] * 32768));
          }
          
          // Send as ArrayBuffer
          wsClientRef.current.sendAudio(int16Data.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);

    } catch (err) {
      setError('Failed to access microphone');
      console.error('Microphone error:', err);
    }
  };

  const stopRecording = () => {
    // Release wake lock
    if (wakeLockRef.current) {
      wakeLockRef.current.release()
        .then(() => {
          console.log('🔓 Screen wake lock released manually');
          wakeLockRef.current = null;
        })
        .catch((err) => {
          console.warn('⚠️ Failed to release wake lock:', err);
        });
    }

    // Stop audio recording
    if (recordingContextRef.current && isRecording) {
      recordingContextRef.current.close();
      recordingContextRef.current = null;
      setIsRecording(false);
    }

    // Stop audio playback
    if (playbackContextRef.current) {
      playbackContextRef.current.close();
      playbackContextRef.current = null;
    }

    // Disconnect WebSocket gracefully
    if (wsClientRef.current) {
      wsClientRef.current.disconnect();
      wsClientRef.current = null;
      setIsConnected(false);
    }

    // Reset audio playback state
    nextPlayTimeRef.current = 0;

    console.log('🛑 Stopped recording, playback, and disconnected');
  };

  const playAudio = async (audioData: ArrayBuffer) => {
    try {
      // Create or recreate audio context if needed
      if (!playbackContextRef.current || playbackContextRef.current.state === 'closed') {
        playbackContextRef.current = new AudioContext({ sampleRate: 16000 });
        nextPlayTimeRef.current = playbackContextRef.current.currentTime;
      }

      // Resume if suspended
      if (playbackContextRef.current.state === 'suspended') {
        await playbackContextRef.current.resume();
      }

      // The audio is raw PCM Int16 data at 16kHz mono
      // Convert Int16 to Float32 for Web Audio API
      const int16Array = new Int16Array(audioData);
      const float32Array = new Float32Array(int16Array.length);
      
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0; // Convert to -1.0 to 1.0 range
      }

      // Create AudioBuffer manually for PCM data
      const audioBuffer = playbackContextRef.current.createBuffer(
        1, // mono
        float32Array.length,
        16000 // sample rate
      );
      
      audioBuffer.getChannelData(0).set(float32Array);

      // Queue audio for sequential playback without gaps
      const currentTime = playbackContextRef.current.currentTime;
      if (nextPlayTimeRef.current < currentTime) {
        nextPlayTimeRef.current = currentTime;
      }

      // Play the audio
      const source = playbackContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(playbackContextRef.current.destination);
      source.start(nextPlayTimeRef.current);
      
      // Update next play time
      nextPlayTimeRef.current += audioBuffer.duration;

    } catch (err) {
      console.error('Audio playback error:', err);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh', 
      minHeight: '-webkit-fill-available',
      position: 'relative',
      overflow: 'hidden' 
    }}>
      {/* Header - Fixed */}
      <div className="glass-panel" style={{ 
        padding: '20px',
        margin: '20px 20px 0 20px',
        flexShrink: 0,
        position: 'sticky',
        top: 20,
        zIndex: 100,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, var(--primary), var(--secondary))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            boxShadow: '0 0 15px var(--primary-glow)'
          }}>
            🎙️
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', background: 'none', WebkitTextFillColor: 'var(--text-main)' }}>AI QSR Voice</h2>
            <p style={{ margin: 0, fontSize: '12px', color: isConnected ? '#2ecc71' : 'var(--text-muted)' }}>
              {isConnected ? '● Connected' : '● Disconnected'}
            </p>
          </div>
        </div>
        <button className="btn-secondary" onClick={onSignOut} style={{ padding: '8px 16px', fontSize: '14px' }}>
          Sign Out
        </button>
      </div>

      {/* Tool Execution Banner */}
      {currentTool && (
        <div style={{
          background: 'linear-gradient(135deg, rgba(253, 185, 19, 0.2), rgba(253, 185, 19, 0.05))',
          border: '1px solid rgba(253, 185, 19, 0.3)',
          color: '#f1c40f',
          padding: '12px 20px',
          margin: '16px 20px 0 20px',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontWeight: '500',
          fontSize: '14px',
          backdropFilter: 'blur(8px)'
        }}>
          <span style={{ animation: 'pulse 1.5s ease-in-out infinite' }}>🔧</span>
          <span>{getToolDisplayName(currentTool)}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div style={{
          background: 'rgba(255, 71, 87, 0.2)',
          border: '1px solid var(--primary)',
          color: '#ff4757',
          padding: '12px 20px',
          margin: '16px 20px 0 20px',
          borderRadius: '12px',
          fontSize: '14px',
          backdropFilter: 'blur(8px)'
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Messages Area */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto',
        overflowX: 'hidden',
        padding: '20px',
        paddingBottom: '120px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        WebkitOverflowScrolling: 'touch'
      }}>
        {messages.length === 0 && (
          <div className="glass-panel" style={{ 
            textAlign: 'center', 
            marginTop: 'auto',
            marginBottom: 'auto',
            maxWidth: '400px',
            alignSelf: 'center'
          }}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎙️</div>
            <p style={{ fontSize: '20px', marginBottom: '8px', color: 'var(--text-main)', fontWeight: '600' }}>
              Welcome to AI Voice Ordering
            </p>
            <p style={{ fontSize: '15px', color: 'var(--text-muted)' }}>
              Tap the microphone to start your order or type a message below.
            </p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-bubble ${msg.role === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'}`}
          >
            <div style={{ fontSize: '16px', whiteSpace: 'pre-wrap', color: 'var(--text-main)' }}>
              {msg.content}
            </div>
            <div style={{ 
              fontSize: '12px', 
              marginTop: '8px',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <span>{msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
              {msg.isAudio && <span>🎤 Voice</span>}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Floating Action Area */}
      <div style={{
        position: 'fixed',
        bottom: '24px',
        right: '20px',
        left: showTextInput ? '20px' : 'auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        gap: '12px',
        zIndex: 1000
      }}>
        {/* Recording Indicator */}
        {isRecording && !showTextInput && (
          <div className="glass-panel" style={{
            position: 'absolute',
            bottom: '80px',
            right: 0,
            padding: '8px 16px',
            borderRadius: '20px',
            fontSize: '13px',
            fontWeight: '500',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--primary)'
          }}>
            <span style={{ 
              width: '8px', height: '8px', borderRadius: '50%', 
              backgroundColor: 'var(--primary)',
              boxShadow: '0 0 8px var(--primary)',
              animation: 'pulse-ring 1.5s infinite'
            }} />
            Listening...
          </div>
        )}

        {/* Text Input */}
        {showTextInput && (
          <div className="glass-panel" style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px',
            borderRadius: '24px',
            marginRight: '8px',
            minWidth: 0
          }}>
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type message..."
              disabled={!isConnected}
              autoFocus
              className="input-glass"
              style={{ padding: '12px 16px', border: 'none', background: 'transparent' }}
            />
            {inputText.trim() && (
              <button
                onClick={handleSendText}
                disabled={!isConnected}
                className="btn-primary"
                style={{ padding: '12px 20px', flexShrink: 0 }}
              >
                Send
              </button>
            )}
          </div>
        )}

        {/* Keyboard Toggle Button */}
        {isRecording && (
          <button
            onClick={() => setShowTextInput(!showTextInput)}
            className="btn-secondary"
            style={{
              width: '56px', height: '56px', borderRadius: '50%', padding: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '24px', flexShrink: 0
            }}
          >
            {showTextInput ? '✕' : '⌨️'}
          </button>
        )}

        {/* Voice Button */}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          className={isRecording ? 'btn-secondary' : 'btn-primary'}
          style={{
            width: '64px', height: '64px', borderRadius: '50%', padding: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '28px', flexShrink: 0,
            boxShadow: isRecording ? 'none' : '0 8px 24px var(--primary-glow)',
            animation: isRecording ? 'none' : 'pulse-ring 2s infinite'
          }}
        >
          {isRecording ? '⏹️' : '🎤'}
        </button>
      </div>
    </div>
  );
}