import { apiClient } from "@aarogya/api-client";
import { SupportedLanguage } from "@aarogya/i18n";

export type TtsButtonState = "idle" | "loading" | "playing" | "error";

export type TtsStateListener = (states: Record<string, TtsButtonState>) => void;

class TtsPlayerService {
  private currentAudio: HTMLAudioElement | null = null;
  private currentBlobUrl: string | null = null;
  private audioContext: AudioContext | null = null;
  private currentSourceNode: AudioBufferSourceNode | null = null;
  private activeLocale: string | null = null;
  private states: Record<string, TtsButtonState> = {};
  private listeners: Set<TtsStateListener> = new Set();
  private ongoingRequestLocale: string | null = null;

  public subscribe(listener: TtsStateListener): () => void {
    this.listeners.add(listener);
    listener({ ...this.states });
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notify() {
    const copy = { ...this.states };
    this.listeners.forEach((fn) => fn(copy));
  }

  private setState(locale: string, state: TtsButtonState) {
    this.states[locale] = state;
    this.notify();
  }

  public getState(locale: string): TtsButtonState {
    return this.states[locale] || "idle";
  }

  /**
   * Synchronously creates or resumes the Web Audio Context during a user gesture click.
   */
  public ensureAudioContextUnlocked(): AudioContext | null {
    if (typeof window === "undefined") return null;
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return null;

    if (!this.audioContext || this.audioContext.state === "closed") {
      this.audioContext = new AudioCtx();
    }
    if (this.audioContext.state === "suspended") {
      this.audioContext.resume().catch(() => {
        // user activation might still unlock on play
      });
    }
    return this.audioContext;
  }

  /**
   * Stop any actively playing audio, Web Audio node, or speech synthesis and revoke allocated resources.
   */
  public stop() {
    if (this.currentSourceNode) {
      try {
        this.currentSourceNode.stop();
        this.currentSourceNode.disconnect();
      } catch (err) {
        // ignore
      }
      this.currentSourceNode = null;
    }

    if (this.currentAudio) {
      try {
        this.currentAudio.pause();
        this.currentAudio.currentTime = 0;
        this.currentAudio.src = "";
      } catch (err) {
        // ignore pause errors
      }
      this.currentAudio = null;
    }

    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = null;
    }

    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (err) {
        // ignore synthesis cancel errors
      }
    }

    if (this.activeLocale) {
      this.setState(this.activeLocale, "idle");
      this.activeLocale = null;
    }
  }

  /**
   * Safely decodes base64 string into an ArrayBuffer
   */
  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }

  /**
   * Checks if the browser has an installed speech voice for this exact locale.
   */
  private findMatchingBrowserVoice(locale: string): SpeechSynthesisVoice | null {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return null;
    }
    const voices = window.speechSynthesis.getVoices() || [];
    const prefix = locale.split("-")[0].toLowerCase();
    
    // Look for exact locale match e.g. mr-IN, hi-IN, ta-IN, gu-IN
    const exact = voices.find((v) => v.lang.toLowerCase().replace("_", "-") === locale.toLowerCase());
    if (exact) return exact;

    // Look for same language prefix only (never fallback to English voice for Indic text)
    const sameLang = voices.find((v) => v.lang.toLowerCase().startsWith(prefix));
    return sameLang || null;
  }

  /**
   * Primary method triggered from user click flow.
   */
  public async playPreview(locale: SupportedLanguage | string, text: string): Promise<boolean> {
    // 1. If currently playing this exact locale, toggle to stop
    if (this.activeLocale === locale && this.getState(locale) === "playing") {
      this.stop();
      return true;
    }

    // 2. Stop any existing playback of other locales first
    this.stop();

    // 3. Synchronously unlock/resume AudioContext on the user's click gesture
    const audioCtx = this.ensureAudioContextUnlocked();

    this.ongoingRequestLocale = locale;
    this.activeLocale = locale;
    this.setState(locale, "loading");

    try {
      // 4. Request audio from backend Sarvam bulbul:v3 gateway
      const res = await apiClient.synthesizeSpeech({
        text: text.trim(),
        language_code: locale,
        context: "LANGUAGE_PREVIEW",
      });

      // 5. Strictly validate non-empty audio_base64
      if (!res || !res.audio_base64 || typeof res.audio_base64 !== "string" || res.audio_base64.trim().length === 0) {
        throw new Error("EMPTY_AUDIO_RESPONSE");
      }

      // Check if user changed or cancelled during network fetch
      if (this.activeLocale !== locale) {
        return false;
      }

      // 6. Decode base64 to ArrayBuffer
      const arrayBuffer = this.base64ToArrayBuffer(res.audio_base64);

      // 7. Try Web Audio API decode and play first
      if (audioCtx) {
        try {
          if (audioCtx.state === "suspended") {
            await audioCtx.resume();
          }
          // Decode audio buffer (copy buffer to avoid detached buffer issues)
          const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
          
          if (this.activeLocale !== locale) return false;

          const source = audioCtx.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(audioCtx.destination);
          this.currentSourceNode = source;

          source.onended = () => {
            if (this.activeLocale === locale) {
              this.setState(locale, "idle");
              this.activeLocale = null;
            }
            if (this.currentSourceNode === source) {
              this.currentSourceNode = null;
            }
          };

          source.start(0);
          this.setState(locale, "playing");
          this.ongoingRequestLocale = null;
          return true;
        } catch (webAudioErr) {
          console.warn("[TTS] WebAudio decode failed, attempting HTMLAudio fallback", webAudioErr);
        }
      }

      // 8. Fallback to HTMLAudioElement with Blob URL
      const mimeType = res.mime_type || "audio/wav";
      const blob = new Blob([arrayBuffer], { type: mimeType });
      const blobUrl = URL.createObjectURL(blob);
      this.currentBlobUrl = blobUrl;

      const audio = new Audio(blobUrl);
      this.currentAudio = audio;

      audio.onended = () => {
        if (this.activeLocale === locale) {
          this.setState(locale, "idle");
          this.activeLocale = null;
        }
        if (this.currentBlobUrl) {
          URL.revokeObjectURL(this.currentBlobUrl);
          this.currentBlobUrl = null;
        }
        this.currentAudio = null;
      };

      audio.onerror = () => {
        if (this.activeLocale === locale) {
          this.setState(locale, "error");
          this.activeLocale = null;
        }
      };

      await audio.play();
      this.setState(locale, "playing");
      this.ongoingRequestLocale = null;
      return true;

    } catch (err) {
      console.warn(`[TTS] Sarvam TTS playback failed for locale '${locale}':`, err);

      // 9. If backend TTS failed, check for exact matching browser speech voice
      const browserVoice = this.findMatchingBrowserVoice(locale);
      if (browserVoice && typeof window !== "undefined" && "speechSynthesis" in window) {
        try {
          console.info(`[TTS] SARVAM_FAILED_BROWSER_FALLBACK_USED for locale ${locale}`);
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.voice = browserVoice;
          utterance.lang = browserVoice.lang;
          utterance.rate = 0.95;

          utterance.onend = () => {
            if (this.activeLocale === locale) {
              this.setState(locale, "idle");
              this.activeLocale = null;
            }
          };

          utterance.onerror = () => {
            if (this.activeLocale === locale) {
              this.setState(locale, "error");
              this.activeLocale = null;
            }
          };

          window.speechSynthesis.speak(utterance);
          this.setState(locale, "playing");
          this.ongoingRequestLocale = null;
          return true;
        } catch {
          // ignore
        }
      }

      // 10. Only mark the failing locale as error
      this.setState(locale, "error");
      this.activeLocale = null;
      this.ongoingRequestLocale = null;
      return false;
    }
  }
}

export const ttsPlayerService = new TtsPlayerService();
