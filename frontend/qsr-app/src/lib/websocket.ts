import { SignatureV4 } from "@smithy/signature-v4";
import { Sha256 } from "@aws-crypto/sha256-js";
import { AWSCredentials } from "./cognito";
import { useConfigStore } from "@/store/useConfigStore";

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private runtimeArn: string;
  private credentials: AWSCredentials;
  private region: string;
  private accessToken: string;
  private userLocation?: { latitude: number; longitude: number };
  private isFullyConnected: boolean = false;
  
  // Callbacks
  private onConnectedCb?: () => void;
  private onDisconnectedCb?: () => void;
  private onTranscriptionCb?: (text: string, role: 'user' | 'assistant') => void;
  private onResponseCb?: (text: string) => void;
  private onAudioCb?: (data: ArrayBuffer) => void;
  private onErrorCb?: (error: Error) => void;
  private onInterruptionCb?: () => void;
  private onTurnCompleteCb?: () => void;
  private onToolStartCb?: (toolName: string) => void;
  private onToolEndCb?: () => void;

  constructor(config: {
    websocketUrl: string; // We keep it for interface compat, but we generate the real URL
    runtimeArn: string;
    credentials: AWSCredentials;
    region: string;
    accessToken: string;
    userLocation?: { latitude: number; longitude: number };
  }) {
    this.runtimeArn = config.runtimeArn;
    this.credentials = config.credentials;
    this.region = config.region;
    this.accessToken = config.accessToken;
    this.userLocation = config.userLocation;
  }

  // --- Callback Setters ---
  onConnected(cb: () => void) { this.onConnectedCb = cb; }
  onDisconnected(cb: () => void) { this.onDisconnectedCb = cb; }
  onTranscription(cb: (text: string, role: 'user' | 'assistant') => void) { this.onTranscriptionCb = cb; }
  onResponse(cb: (text: string) => void) { this.onResponseCb = cb; }
  onAudio(cb: (data: ArrayBuffer) => void) { this.onAudioCb = cb; }
  onError(cb: (error: Error) => void) { this.onErrorCb = cb; }
  onInterruption(cb: () => void) { this.onInterruptionCb = cb; }
  onTurnComplete(cb: () => void) { this.onTurnCompleteCb = cb; }
  onToolStart(cb: (toolName: string) => void) { this.onToolStartCb = cb; }
  onToolEnd(cb: () => void) { this.onToolEndCb = cb; }

  async connect() {
    try {
      const configStore = useConfigStore.getState().config;
      if (!configStore) throw new Error("Config not loaded");

      // If local testing, bypass AWS SigV4 signing
      let finalUrl = configStore.websocketUrl;
      if (finalUrl.includes('localhost') || finalUrl.includes('127.0.0.1')) {
        finalUrl = `${finalUrl}?qualifier=DEFAULT&voice_id=tiffany`;
      } else {
        // Construct the strict Bedrock AgentCore WebSocket URL
        // It completely ignores the runtime specific hostname and uses the bedrock-agentcore regional endpoint
        const baseUrl = `wss://bedrock-agentcore.${configStore.region}.amazonaws.com/runtimes/${this.runtimeArn}/ws?qualifier=DEFAULT&voice_id=tiffany`;
        const httpsUrl = baseUrl.replace('wss://', 'https://');
        const urlObject = new URL(httpsUrl);
        
        const sigV4 = new SignatureV4({
          credentials: {
            accessKeyId: this.credentials.accessKeyId,
            secretAccessKey: this.credentials.secretAccessKey,
            sessionToken: this.credentials.sessionToken,
          },
          region: configStore.region,
          service: "bedrock-agentcore", // It MUST be bedrock-agentcore, not bedrock
          sha256: Sha256,
        });

        const signedRequest = await sigV4.presign({
          method: "GET",
          protocol: "https:",
          hostname: urlObject.hostname,
          path: urlObject.pathname,
          headers: {
            host: urlObject.hostname,
          },
          query: Object.fromEntries(urlObject.searchParams.entries()),
        }, { expiresIn: 300 });

        finalUrl = `https://${signedRequest.hostname}${signedRequest.path}`;
        if (signedRequest.query) {
          const queryParams = new URLSearchParams(signedRequest.query as Record<string, string>);
          finalUrl += `?${queryParams.toString()}`;
        }
        finalUrl = finalUrl.replace('https://', 'wss://');
      }

      this.ws = new WebSocket(finalUrl);
      // NOTE: We don't use binaryType = "arraybuffer" anymore because AgentCore protocol sends everything as JSON strings with base64 audio

      this.ws.onopen = () => {
        this.sendIdentity();
        // Delay onConnectedCb to prevent audio from racing ahead of "Hi"
        // This is critical because Nova Sonic hangs if audio arrives before the initial text prompt!
        setTimeout(() => {
          this.isFullyConnected = true;
          this.onConnectedCb?.();
        }, 500);
      };

      this.ws.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);
        this.onDisconnectedCb?.();
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.onErrorCb?.(new Error("WebSocket encountered an error"));
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };

    } catch (error: any) {
      console.error("Connection setup failed:", error);
      this.onErrorCb?.(error);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN && this.isFullyConnected;
  }

  // --- Outgoing Messages ---

  private sendIdentity() {
    // Bedrock AgentCore requires "auth" type with snake_case "access_token"
    const authMessage = {
      type: "auth",
      access_token: this.accessToken,
    };
    this.ws?.send(JSON.stringify(authMessage));
    
    // Send "Hi" message to initiate conversation
    // This triggers the agent to start speaking
    setTimeout(() => {
      this.sendText("Hi");
    }, 100); // Small delay to ensure auth is processed first
  }

  /**
   * Send text message to AgentCore
   */
  sendText(text: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('Cannot send text: WebSocket not connected');
      return;
    }

    const message = {
      type: 'bidi_text_input',
      text
    };

    this.ws.send(JSON.stringify(message));
    console.log('📤 Sent text:', text);
  }

  sendAudio(audioBuffer: ArrayBuffer) {
    if (!this.isConnected()) return;
    const msg = {
      type: "bidi_audio_input",
      audio: this.arrayBufferToBase64(audioBuffer),
      format: "pcm",
      sample_rate: 16000,
      channels: 1
    };
    this.ws?.send(JSON.stringify(msg));
  }

  // --- Incoming Message Handlers ---

  private handleMessage(data: string) {
    try {
      const parsed = JSON.parse(data);
      
      switch (parsed.type) {
        case "bidi_transcript_stream":
          if (parsed.role === "user") {
            this.onTranscriptionCb?.(parsed.transcript || parsed.text, "user");
          } else if (parsed.role === "assistant" || !parsed.role) {
            // Avoid duplicate final transcripts
            if (parsed.is_final === true) break;
            this.onResponseCb?.(parsed.transcript || parsed.text);
          }
          break;
          
        case "bidi_audio_stream":
          if (parsed.audio) {
            this.onAudioCb?.(this.base64ToArrayBuffer(parsed.audio));
          }
          break;
          
        case "bidi_text_output":
          this.onResponseCb?.(parsed.text);
          break;
          
        case "bidi_interruption":
          this.onInterruptionCb?.();
          this.onTurnCompleteCb?.();
          break;
          
        case "tool_use_stream":
          const toolName = parsed.current_tool_use?.name || "unknown";
          this.onToolStartCb?.(toolName);
          break;
          
        case "tool_result":
          this.onToolEndCb?.();
          break;
          
        case "location_request":
          this.handleLocationRequest(parsed.request_id);
          break;
          
        case "error":
          this.onErrorCb?.(new Error(parsed.message || "Unknown server error"));
          break;
      }
    } catch (e) {
      console.warn("Failed to parse incoming message:", data);
    }
  }

  private handleLocationRequest(requestId: string) {
    const loc = this.userLocation || { latitude: 32.7767, longitude: -96.7970 };
    const locationResponse = {
      type: "location_response",
      request_id: requestId,
      location: {
        latitude: loc.latitude,
        longitude: loc.longitude,
        accuracy: 10.0
      }
    };
    this.ws?.send(JSON.stringify(locationResponse));
  }

  // Utility functions
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }
}
