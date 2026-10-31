"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import { errorMessage } from "./format";
function wav(samples: Float32Array) {
  const b = new ArrayBuffer(44 + samples.length * 2),
    v = new DataView(b);
  const s = (o: number, t: string) =>
    [...t].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
  s(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  s(8, "WAVEfmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);
  v.setUint16(22, 1, true);
  v.setUint32(24, 16000, true);
  v.setUint32(28, 32000, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  s(36, "data");
  v.setUint32(40, samples.length * 2, true);
  samples.forEach((x, i) =>
    v.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x)) * 32767, true),
  );
  return new Blob([b], { type: "audio/wav" });
}
export function useMicrophone(
  projectId: string | undefined,
  onText: (s: string) => void,
  onError: (s: string) => void,
) {
  const [state, setState] = useState<
      "idle" | "requesting" | "recording" | "transcribing"
    >("idle"),
    [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null),
    timer = useRef<ReturnType<typeof setInterval> | null>(null),
    cancelled = useRef(false),
    generation = useRef(0),
    active = useRef(false);
  function cleanup() {
    if (timer.current) clearInterval(timer.current);
    recorder.current?.stream.getTracks().forEach((t) => t.stop());
  }
  useEffect(
    () => () => {
      cancelled.current = true;
      generation.current++;
      active.current = false;
      if (recorder.current?.state === "recording") recorder.current.stop();
      cleanup();
    },
    [],
  );
  function stop(cancel = false) {
    cancelled.current = cancel;
    if (cancel) {
      generation.current++;
      active.current = false;
    }
    if (recorder.current?.state === "recording") recorder.current.stop();
    cleanup();
    if (cancel) setState("idle");
  }
  async function start() {
    if (active.current) return;
    active.current = true;
    cancelled.current = false;
    const run = ++generation.current;
    const isCurrent = () => run === generation.current && !cancelled.current;
    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!isCurrent()) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const r = new MediaRecorder(stream);
      recorder.current = r;
      cancelled.current = false;
      const chunks: Blob[] = [];
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = async () => {
        if (!isCurrent()) return;
        cleanup();
        setState("transcribing");
        let context: AudioContext | undefined;
        try {
          context = new AudioContext();
          const b = await context.decodeAudioData(
            await new Blob(chunks).arrayBuffer(),
          );
          const off = new OfflineAudioContext(
            1,
            Math.ceil(Math.min(b.duration, 60) * 16000),
            16000,
          );
          const source = off.createBufferSource();
          source.buffer = b;
          source.connect(off.destination);
          source.start();
          const rendered = await off.startRendering();
          if (!isCurrent()) return;
          const data = new FormData();
          data.append(
            "audio",
            wav(rendered.getChannelData(0)),
            "recording.wav",
          );
          const response = await api<{
            text?: string;
            issue?: { message: string };
          }>(
            projectId
              ? `/api/v1/projects/${projectId}/transcriptions`
              : "/api/v1/transcriptions",
            {
              method: "POST",
              body: data,
            },
          );
          if (!isCurrent()) return;
          if (response.text) onText(response.text);
          else
            throw new Error(
              response.issue?.message ??
                "No speech was transcribed. Try again or type your request.",
            );
        } catch (e) {
          if (isCurrent()) onError(errorMessage(e));
        } finally {
          await context?.close();
          if (isCurrent()) {
            active.current = false;
            setState("idle");
          }
        }
      };
      r.start();
      setSeconds(0);
      setState("recording");
      let elapsed = 0;
      timer.current = setInterval(() => {
        setSeconds(++elapsed);
        if (elapsed >= 60) stop();
      }, 1000);
    } catch (e) {
      if (!isCurrent()) return;
      active.current = false;
      onError(
        `Microphone unavailable. You can still type your request. ${errorMessage(e)}`,
      );
      setState("idle");
    }
  }
  return { state, seconds, start, stop };
}
