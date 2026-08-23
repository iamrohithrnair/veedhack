"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  AudioLines,
  Camera,
  Check,
  Clapperboard,
  Download,
  LoaderCircle,
  Play,
  Send,
  Sparkles,
  TerminalSquare,
  Video,
  WandSparkles,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { getShowcase, mediaUrl } from "@/lib/api";
import type { StreamEvent } from "@/lib/types";

const TOPIC = "Why fine-tuning LLMs manually is obsolete with Pioneer AI.";
const VIBE = "A dramatic, wise 18th-century philosopher in an oil painting style.";
const FALLBACK_SCRIPT =
  "Hark! Manual fine-tuning is a clock-devil, devouring teams while LLMs rot. Let Pioneer AI handle it—use the LLM API and switch models today!";
const FALLBACK_ENTITIES = {
  Core_Subject: "Pioneer AI",
  Pain_Point: "Manual fine-tuning devouring teams while LLMs rot",
  Emotional_Vibe: "Theatrical Outrage",
  Action_Hook: "Let Pioneer AI handle it — switch models today",
};

type Phase =
  | "idle"
  | "typing"
  | "script"
  | "teleprompter"
  | "record"
  | "render"
  | "reveal";

function sleep(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(() => resolve(), ms);
    signal?.addEventListener("abort", () => {
      window.clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    });
  });
}

function eventLabel(event: StreamEvent) {
  return event.message || event.stage || "event";
}

function presentEntities(raw: Record<string, string> | undefined) {
  const subject = raw?.Core_Subject || "";
  if (!subject || subject.split(",").length > 2) return FALLBACK_ENTITIES;
  return {
    Core_Subject: raw?.Core_Subject || FALLBACK_ENTITIES.Core_Subject,
    Pain_Point: raw?.Pain_Point || FALLBACK_ENTITIES.Pain_Point,
    Emotional_Vibe: raw?.Emotional_Vibe || FALLBACK_ENTITIES.Emotional_Vibe,
    Action_Hook: raw?.Action_Hook || FALLBACK_ENTITIES.Action_Hook,
  };
}

export function StudioPremiere() {
  const reduceMotion = useReducedMotion();
  const [topic, setTopic] = useState("");
  const [vibe, setVibe] = useState("");
  const [script, setScript] = useState("");
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [audioUrl, setAudioUrl] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");
  const [drivingUrl, setDrivingUrl] = useState("");
  const [finalVideo, setFinalVideo] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(10);
  const [pulse, setPulse] = useState<"generate" | "render" | null>(null);
  const [ready, setReady] = useState(false);
  const payloadRef = useRef({
    script: FALLBACK_SCRIPT,
    entities: FALLBACK_ENTITIES,
    audio: "",
    avatar: "",
    driving: "",
    final: "",
  });
  const abortRef = useRef<AbortController | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    terminalRef.current?.scrollTo({ top: terminalRef.current.scrollHeight });
  }, [events]);

  const pushEvent = (event: StreamEvent) => {
    setEvents((current) => [...current, { timestamp: new Date().toISOString(), ...event }]);
  };

  const run = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const { signal } = controller;
    const payload = payloadRef.current;

    setTopic("");
    setVibe("");
    setScript("");
    setEvents([]);
    setAudioUrl("");
    setFinalVideo("");
    setProgress(null);
    setRecording(false);
    setSeconds(10);
    setPulse(null);
    setPhase("typing");

    try {
      await sleep(900, signal);
      for (let index = 1; index <= TOPIC.length; index += 1) {
        setTopic(TOPIC.slice(0, index));
        await sleep(28, signal);
      }
      await sleep(400, signal);
      for (let index = 1; index <= VIBE.length; index += 1) {
        setVibe(VIBE.slice(0, index));
        await sleep(22, signal);
      }

      setPulse("generate");
      await sleep(700, signal);
      setPhase("script");
      setPulse(null);
      pushEvent({ stage: "tavily", level: "info", message: "Extracting industry context..." });
      await sleep(1400, signal);
      pushEvent({
        stage: "tavily",
        level: "success",
        message: "Industry context extracted",
        payload: { result_count: 5 },
      });
      await sleep(700, signal);
      pushEvent({ stage: "gliner", level: "info", message: "Slicing data with tuned GLiNER2..." });
      await sleep(1600, signal);
      pushEvent({
        stage: "gliner",
        level: "success",
        message: "Structured context extracted",
        payload: { entities: payload.entities },
      });
      await sleep(600, signal);
      pushEvent({ stage: "openai", level: "info", message: "Writing unhinged script..." });

      const words = payload.script.split(/(\s+)/);
      let assembled = "";
      for (const chunk of words) {
        assembled += chunk;
        setScript(assembled);
        pushEvent({ stage: "script_delta", message: "Script token", payload: { delta: chunk } });
        await sleep(chunk.trim() ? 90 : 40, signal);
      }
      pushEvent({ stage: "openai", level: "success", message: "Script complete", payload: { script: payload.script } });
      await sleep(400, signal);
      pushEvent({ stage: "tts", level: "info", message: "Generating onyx voice track..." });
      await sleep(1400, signal);
      setAudioUrl(payload.audio);
      pushEvent({ stage: "tts", level: "success", message: "Voice track uploaded" });
      pushEvent({
        stage: "done",
        level: "success",
        message: "Script pipeline complete",
        payload: { entities: payload.entities, script: payload.script },
      });

      setPhase("teleprompter");
      await sleep(1600, signal);
      setPhase("record");
      setRecording(true);
      for (let remaining = 10; remaining >= 0; remaining -= 1) {
        setSeconds(remaining);
        await sleep(1000, signal);
      }
      setRecording(false);

      setPulse("render");
      await sleep(800, signal);
      setPhase("render");
      setPulse(null);
      setProgress(8);
      pushEvent({ stage: "avatar", level: "info", message: "Generating avatar image" });
      await sleep(1800, signal);
      setProgress(28);
      pushEvent({ stage: "avatar", level: "success", message: "Avatar ready" });
      pushEvent({ stage: "animate", level: "info", message: "Animating avatar with Wan-Animate" });
      await sleep(3200, signal);
      setProgress(62);
      pushEvent({ stage: "animate", level: "success", message: "Animation complete" });
      pushEvent({ stage: "lipsync", level: "info", message: "Synchronizing speech with VEED Lipsync v2" });
      await sleep(2800, signal);
      setProgress(92);
      pushEvent({ stage: "lipsync", level: "success", message: "Lip-sync complete" });
      await sleep(600, signal);
      setProgress(100);
      setFinalVideo(payload.final);
      setPhase("reveal");
      pushEvent({
        stage: "done",
        level: "success",
        message: "Video render complete",
        payload: { final_video_url: payload.final },
      });
    } catch (error) {
      if (!(error instanceof DOMException && error.name === "AbortError")) {
        throw error;
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    getShowcase()
      .then((showcase) => {
        if (cancelled) return;
        payloadRef.current = {
          script: showcase.script || FALLBACK_SCRIPT,
          entities: presentEntities(showcase.entities),
          audio: mediaUrl(showcase.files["audio.mp3"]),
          avatar: mediaUrl(showcase.files["avatar.png"]),
          driving: mediaUrl(showcase.files["driving.mp4"]),
          final: mediaUrl(showcase.files["final.mp4"]),
        };
        setAvatarUrl(payloadRef.current.avatar);
        setDrivingUrl(payloadRef.current.driving);
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) return;
    const start = window.setTimeout(() => {
      run().catch(() => undefined);
    }, 700);
    return () => {
      window.clearTimeout(start);
      abortRef.current?.abort();
    };
  }, [ready, run]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "r" && !event.metaKey && !event.ctrlKey) {
        event.preventDefault();
        run().catch(() => undefined);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [run]);

  const generating = phase === "script";
  const rendering = phase === "render";

  return (
    <section className="workbench premiere-workbench" aria-label="Charismate studio">
      <div className="work-panel script-panel">
        <div className="panel-heading workbench-panel-heading">
          <div className="panel-heading-title">
            <span>Step 1</span>
            <h2>Generate script & context</h2>
          </div>
        </div>
        <div className="field">
          <div className="field-header">
            <span>1. What&apos;s your video about?</span>
          </div>
          <textarea maxLength={250} value={topic} readOnly />
          <small>{topic.length} / 250</small>
        </div>
        <div className="generation-options">
          <div>
            <span className="option-label">Motion mode</span>
            <div className="mode-switch" role="group" aria-label="Avatar motion mode">
              <button type="button">Move</button>
              <button className="active" type="button">Replace</button>
            </div>
          </div>
          <label>
            <span className="option-label">Saved avatar</span>
            <select disabled value="">
              <option value="">Generate a new avatar</option>
            </select>
          </label>
        </div>
        <div className="field">
          <div className="field-header">
            <span>2. Avatar vibe <i>Describe your character</i></span>
          </div>
          <textarea maxLength={250} value={vibe} readOnly />
          <small>{vibe.length} / 250</small>
        </div>
        <button className={`gradient-button ${pulse === "generate" ? "pulse-action" : ""}`} disabled type="button">
          {generating ? <LoaderCircle className="spin" size={16} /> : <WandSparkles size={16} />}
          {generating ? "Generating from API…" : "Generate script & extract context"}
        </button>

        <div className="section-divider">
          <span>{script ? <><Check size={12} />Script generated</> : "Generated output"}</span>
        </div>
        <div className="field script-output">
          <div className="field-header"><span>Your script</span></div>
          <div className="quote-mark">“</div>
          <textarea readOnly value={script} placeholder="Your generated script will appear here from the live API." />
        </div>
        <div className="audio-player">
          <AudioLines size={17} />
          {audioUrl ? (
            <audio controls src={audioUrl} autoPlay={phase === "teleprompter" || phase === "record"}>
              Your browser does not support audio.
            </audio>
          ) : (
            <>
              <button disabled aria-label="Audio unavailable"><Play size={13} fill="currentColor" /></button>
              <div className="waveform" aria-hidden="true">{Array.from({ length: 28 }, (_, index) => <i key={index} />)}</div>
              <span>—:—</span>
            </>
          )}
        </div>
      </div>

      <div className="work-panel motion-panel">
        <div className="panel-heading"><span>Step 2</span><h2>Record driving motion</h2></div>
        <div className="teleprompter-head">
          <span><Video size={14} />Teleprompter</span>
        </div>
        <div className="teleprompter">
          {script ? <p>{script}</p> : <p className="placeholder">Generate a script to load your teleprompter.</p>}
        </div>
        <div className="teleprompter-head"><span><Camera size={14} />Camera</span><small>Keep your face centered</small></div>
        <div className="camera-recorder">
          <div className="camera-stage">
            {drivingUrl && (phase === "record" || phase === "render" || phase === "reveal") ? (
              <video className="live-feed" src={drivingUrl} autoPlay muted loop playsInline />
            ) : avatarUrl && phase !== "idle" && phase !== "typing" ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img className="live-feed" src={avatarUrl} alt="" />
            ) : (
              <div className="camera-standby">
                <Camera size={32} />
                <strong>Camera standing by</strong>
                <p>Driving motion is captured after the script lands.</p>
              </div>
            )}
            {recording && <span className="recording-badge"><i />REC</span>}
            {(phase === "record" || recording) && (
              <span className="camera-time">00:{String(10 - seconds).padStart(2, "0")} / 00:10</span>
            )}
          </div>
        </div>
        <button className={`gradient-button render-button ${pulse === "render" ? "pulse-action" : ""}`} disabled type="button">
          {rendering ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}
          {rendering ? "Rendering from API…" : "Charismate it — Render video"}
        </button>
        <p className="button-hint">Your motion drives the avatar in the final video.</p>
      </div>

      <div className="work-panel terminal-panel">
        <div className="terminal-title"><span><TerminalSquare size={15} />Live terminal</span></div>
        <div className="terminal-output" ref={terminalRef} role="log" aria-live="polite">
          {events.length === 0 ? (
            <div className="terminal-empty"><Send size={20} /><p>Live backend events will appear here when generation begins.</p></div>
          ) : events.map((event, index) => (
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              className="terminal-line"
              key={`${index}-${event.stage}-${event.message}`}
            >
              <span>{event.stage === "done" ? <Check size={12} /> : <i />}</span>
              <code>
                <b>[{event.stage || "event"}]</b> {eventLabel(event)}
                {event.payload && Object.keys(event.payload).length > 0 && event.stage !== "script_delta" ? (
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                ) : null}
              </code>
            </motion.div>
          ))}
        </div>
        {progress !== null && phase !== "reveal" && (
          <div className="render-progress">
            <div><span>Rendering final video…</span><strong>{Math.round(progress)}%</strong></div>
            <div className="progress-track"><motion.i animate={{ width: `${progress}%` }} /></div>
          </div>
        )}
        <AnimatePresence mode="wait">
          {finalVideo ? (
            <motion.div initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} className="final-video" key="video">
              <video src={finalVideo} controls autoPlay playsInline />
              <div>
                <span><Check size={14} />Your Charismate is ready</span>
                <a href={finalVideo} download><Download size={14} />Download</a>
              </div>
            </motion.div>
          ) : (
            <motion.div className="render-preview" key="preview">
              <div className="preview-glow"><Clapperboard size={38} /></div>
              <span>Final render</span>
              <p>Your completed video will appear here from the API.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
