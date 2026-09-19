import type { Prio } from "../api/types";

const MUTE_KEY = "gridup.alarmAudioMuted";

export function isAlarmAudioMuted(): boolean {
  try {
    return localStorage.getItem(MUTE_KEY) === "1";
  } catch {
    return false;
  }
}

export function setAlarmAudioMuted(muted: boolean): void {
  try {
    localStorage.setItem(MUTE_KEY, muted ? "1" : "0");
  } catch {
    // localStorage kapaliysa sessizce devam et
  }
}

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!audioCtx) {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (Ctx) audioCtx = new Ctx();
  }
  if (audioCtx && audioCtx.state === "suspended") {
    void audioCtx.resume();
  }
  return audioCtx;
}

/**
 * Kontrol odasi icin Web Audio API tabanli sakin ama net uyari tonu.
 * Harici MP3/WAV gerektirmez (GK4: %100 cevrimeyici, sifir dosya bagimliligi).
 */
export function playAlarmChime(prio: Prio = "P1"): void {
  if (isAlarmAudioMuted()) return;
  const ctx = getAudioContext();
  if (!ctx) return;

  const now = ctx.currentTime;
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();

  osc.type = "sine";
  gain.connect(ctx.destination);
  osc.connect(gain);

  if (prio === "P1") {
    // P1: Cift tonlu net dikkat cagrisi (880 Hz -> 659 Hz, 300 ms)
    osc.frequency.setValueAtTime(880, now);
    osc.frequency.setValueAtTime(659, now + 0.12);

    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(0.18, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.12, now + 0.14);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.32);

    osc.start(now);
    osc.stop(now + 0.33);
  } else {
    // P2 / Diger: Tek tonlu yumusak gong (587 Hz, 200 ms)
    osc.frequency.setValueAtTime(587.33, now);

    gain.gain.setValueAtTime(0.001, now);
    gain.gain.exponentialRampToValueAtTime(0.12, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);

    osc.start(now);
    osc.stop(now + 0.23);
  }
}
