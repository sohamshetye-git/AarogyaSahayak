/**
 * Real Microphone Audio Capture & Speech-to-Text Orchestration Service
 * 
 * Implements strict state machine:
 * IDLE -> REQUESTING_PERMISSION -> RECORDING -> PROCESSING -> TRANSCRIPT_READY -> CONFIRMED
 * Error states:
 * PERMISSION_DENIED | NO_AUDIO | PROVIDER_UNAVAILABLE | FAILED | CANCELLED | INSECURE_ORIGIN
 * 
 * Never substitutes fake / hardcoded transcripts.
 */

import { apiClient } from "@aarogya/api-client";

export type AudioRecordingState =
  | "IDLE"
  | "REQUESTING_PERMISSION"
  | "RECORDING"
  | "PROCESSING"
  | "TRANSCRIPT_READY"
  | "CONFIRMED"
  | "PERMISSION_DENIED"
  | "NO_AUDIO"
  | "PROVIDER_UNAVAILABLE"
  | "FAILED"
  | "CANCELLED"
  | "INSECURE_ORIGIN";

export interface AudioCaptureConfig {
  maxDurationSeconds?: number;
  silenceThresholdMs?: number;
  sampleRate?: number;
}

export interface AudioCaptureResult {
  audioBase64?: string;
  blob?: Blob;
  durationSeconds: number;
  transcript: string;
  detectedLanguage: string;
  confidence: number;
  provider: string;
  status: AudioRecordingState;
  errorMessage?: string;
}

export class AudioCaptureService {
  private mediaRecorder: MediaRecorder | null = null;
  private audioStream: MediaStream | null = null;
  private audioChunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private maxDurationTimer: any = null;
  private startTime: number = 0;
  private activeState: AudioRecordingState = "IDLE";
  private speechRecognitionInstance: any = null;
  private webSpeechTranscript: string = "";

  public getState(): AudioRecordingState {
    return this.activeState;
  }

  /**
   * Check if current browser context supports secure microphone capture (localhost or HTTPS)
   */
  public static isSecureContext(): boolean {
    if (typeof window === "undefined") return true;
    if (window.isSecureContext) return true;
    const hostname = window.location.hostname;
    return hostname === "localhost" || hostname === "127.0.0.1" || hostname.endsWith(".local");
  }

  /**
   * Check microphone capability in current environment
   */
  public static isMicrophoneSupported(): boolean {
    if (typeof navigator === "undefined") return false;
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  /**
   * Start genuine microphone capture
   */
  public async startRecording(
    language: string = "mr-IN",
    onLevelChange?: (level: number) => void,
    onStateChange?: (state: AudioRecordingState) => void,
    config: AudioCaptureConfig = {}
  ): Promise<void> {
    const maxSec = config.maxDurationSeconds || 30;

    if (!AudioCaptureService.isSecureContext()) {
      this.activeState = "INSECURE_ORIGIN";
      if (onStateChange) onStateChange(this.activeState);
      throw new Error(
        "Microphone recording requires a secure origin (HTTPS or localhost). Please check your connection security."
      );
    }

    if (!AudioCaptureService.isMicrophoneSupported()) {
      this.activeState = "FAILED";
      if (onStateChange) onStateChange(this.activeState);
      throw new Error("Microphone is not supported in this browser or WebView.");
    }

    this.activeState = "REQUESTING_PERMISSION";
    if (onStateChange) onStateChange(this.activeState);

    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
    } catch (err: any) {
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        this.activeState = "PERMISSION_DENIED";
      } else {
        this.activeState = "FAILED";
      }
      if (onStateChange) onStateChange(this.activeState);
      throw err;
    }

    this.audioChunks = [];
    this.startTime = Date.now();
    this.activeState = "RECORDING";
    if (onStateChange) onStateChange(this.activeState);

    // Setup audio analyser for waveform/sound volume
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.audioContext = new AudioCtx();
        const source = this.audioContext.createMediaStreamSource(this.audioStream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 64;
        source.connect(this.analyser);

        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const checkLevel = () => {
          if (this.activeState !== "RECORDING" || !this.analyser) return;
          this.analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < bufferLength; i++) {
            sum += dataArray[i];
          }
          const average = sum / bufferLength;
          const normalized = Math.min(100, Math.round((average / 255) * 100));
          if (onLevelChange) onLevelChange(normalized);
          requestAnimationFrame(checkLevel);
        };
        requestAnimationFrame(checkLevel);
      }
    } catch (e) {
      console.warn("AudioContext metering initialization error:", e);
    }

    // Try parallel browser SpeechRecognition for immediate client feedback
    this.webSpeechTranscript = "";
    if (typeof window !== "undefined") {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          this.speechRecognitionInstance = new SpeechRecognition();
          this.speechRecognitionInstance.lang = language;
          this.speechRecognitionInstance.continuous = true;
          this.speechRecognitionInstance.interimResults = true;
          this.speechRecognitionInstance.onresult = (event: any) => {
            let current = "";
            for (let i = 0; i < event.results.length; i++) {
              current += event.results[i][0].transcript;
            }
            this.webSpeechTranscript = current.trim();
          };
          this.speechRecognitionInstance.start();
        } catch (e) {
          console.warn("WebSpeech parallel start skipped:", e);
        }
      }
    }

    // Determine supported mime type
    let mimeType = "audio/webm";
    if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
      mimeType = "audio/webm;codecs=opus";
    } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
      mimeType = "audio/mp4";
    } else if (MediaRecorder.isTypeSupported("audio/ogg")) {
      mimeType = "audio/ogg";
    }

    try {
      this.mediaRecorder = new MediaRecorder(this.audioStream, { mimeType });
    } catch (e) {
      this.mediaRecorder = new MediaRecorder(this.audioStream);
    }

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        this.audioChunks.push(e.data);
      }
    };

    this.mediaRecorder.start(250); // Slice chunks every 250ms

    // Max duration auto-stop
    this.maxDurationTimer = setTimeout(() => {
      if (this.activeState === "RECORDING") {
        this.stopRecording(language, onStateChange);
      }
    }, maxSec * 1000);
  }

  /**
   * Stop recording, process audio blob, and run STT adapter chain
   */
  public async stopRecording(
    language: string = "mr-IN",
    onStateChange?: (state: AudioRecordingState) => void
  ): Promise<AudioCaptureResult> {
    if (this.maxDurationTimer) {
      clearTimeout(this.maxDurationTimer);
      this.maxDurationTimer = null;
    }

    if (this.speechRecognitionInstance) {
      try {
        this.speechRecognitionInstance.stop();
      } catch (e) {}
    }

    const durationSeconds = Math.max(1, Math.round((Date.now() - this.startTime) / 1000));

    return new Promise((resolve) => {
      if (!this.mediaRecorder || this.mediaRecorder.state === "inactive") {
        this.cleanup();
        this.activeState = "NO_AUDIO";
        if (onStateChange) onStateChange(this.activeState);
        resolve({
          durationSeconds: 0,
          transcript: "",
          detectedLanguage: language,
          confidence: 0,
          provider: "NONE",
          status: "NO_AUDIO",
          errorMessage: "No active audio recording found."
        });
        return;
      }

      this.mediaRecorder.onstop = async () => {
        this.activeState = "PROCESSING";
        if (onStateChange) onStateChange(this.activeState);

        const mimeType = this.mediaRecorder?.mimeType || "audio/webm";
        const audioBlob = new Blob(this.audioChunks, { type: mimeType });
        this.cleanup();

        if (audioBlob.size === 0) {
          this.activeState = "NO_AUDIO";
          if (onStateChange) onStateChange(this.activeState);
          resolve({
            blob: audioBlob,
            durationSeconds,
            transcript: "",
            detectedLanguage: language,
            confidence: 0,
            provider: "NONE",
            status: "NO_AUDIO",
            errorMessage: "No sound was captured. Please check your microphone."
          });
          return;
        }

        // Convert blob to base64
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = async () => {
          const base64Data = (reader.result as string).split(",")[1];

          // 1. Try Backend STT adapter
          try {
            const res = await apiClient.transcribeCitizenVoice({
              audio_base64: base64Data,
              preferred_language: language,
              audio_format: mimeType.includes("mp4") ? "mp4" : "webm",
              duration_seconds: durationSeconds
            });

            const data = res?.data || res;
            if (data?.transcript && data.transcript.trim().length > 0) {
              this.activeState = "TRANSCRIPT_READY";
              if (onStateChange) onStateChange(this.activeState);
              resolve({
                audioBase64: base64Data,
                blob: audioBlob,
                durationSeconds,
                transcript: data.transcript.trim(),
                detectedLanguage: data.detected_language || language,
                confidence: data.confidence || 0.9,
                provider: data.provider || "BACKEND_STT",
                status: "TRANSCRIPT_READY"
              });
              return;
            }
          } catch (backendErr) {
            console.warn("Backend STT failed, evaluating client fallback:", backendErr);
          }

          // 2. Fallback to browser WebSpeech if it captured spoken words
          if (this.webSpeechTranscript && this.webSpeechTranscript.trim().length > 0) {
            this.activeState = "TRANSCRIPT_READY";
            if (onStateChange) onStateChange(this.activeState);
            resolve({
              audioBase64: base64Data,
              blob: audioBlob,
              durationSeconds,
              transcript: this.webSpeechTranscript.trim(),
              detectedLanguage: language,
              confidence: 0.85,
              provider: "BROWSER_SPEECH_RECOGNITION",
              status: "TRANSCRIPT_READY"
            });
            return;
          }

          // 3. Honest provider unavailable response (Zero hardcoded Marathi/Hindi text)
          this.activeState = "PROVIDER_UNAVAILABLE";
          if (onStateChange) onStateChange(this.activeState);
          resolve({
            audioBase64: base64Data,
            blob: audioBlob,
            durationSeconds,
            transcript: "",
            detectedLanguage: language,
            confidence: 0,
            provider: "NONE",
            status: "PROVIDER_UNAVAILABLE",
            errorMessage:
              "Speech recognition could not convert the audio. Please speak clearly or type your message."
          });
        };
      };

      this.mediaRecorder.stop();
    });
  }

  /**
   * Cancel and discard recording
   */
  public cancelRecording(onStateChange?: (state: AudioRecordingState) => void) {
    if (this.maxDurationTimer) {
      clearTimeout(this.maxDurationTimer);
      this.maxDurationTimer = null;
    }
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
    }
    if (this.speechRecognitionInstance) {
      try {
        this.speechRecognitionInstance.abort();
      } catch (e) {}
    }
    this.cleanup();
    this.activeState = "CANCELLED";
    if (onStateChange) onStateChange(this.activeState);
  }

  private cleanup() {
    if (this.audioStream) {
      this.audioStream.getTracks().forEach((track) => track.stop());
      this.audioStream = null;
    }
    if (this.audioContext && this.audioContext.state !== "closed") {
      try {
        this.audioContext.close();
      } catch (e) {}
      this.audioContext = null;
    }
    this.analyser = null;
  }
}

export const audioCaptureService = new AudioCaptureService();
