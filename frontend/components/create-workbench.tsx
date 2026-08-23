"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  AudioLines,
  Camera,
  CameraOff,
  Check,
  CircleStop,
  Clapperboard,
  Download,
  LoaderCircle,
  Play,
  Plus,
  RefreshCcw,
  Send,
  Sparkles,
  TerminalSquare,
  Video,
  WandSparkles,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  createProject,
  generateScript,
  getCollection,
  getProject,
  renderVideo,
  updateProject,
} from "@/lib/api";
import type { ApiRecord, StreamEvent } from "@/lib/types";
import { useProjectName } from "@/components/app-shell";
import { FieldActions } from "@/components/field-actions";

const DEFAULT_TOPIC = "Why fine-tuning LLMs manually is obsolete with Pioneer AI.";
const DEFAULT_VIBE = "A dramatic, wise 18th-century philosopher in an oil painting style.";

const SCRIPT_STATUSES = new Set(["researching", "extracting", "writing", "voicing", "scripting"]);
const RENDER_STATUSES = new Set(["rendering", "uploading"]);

function busyFromStatus(status?: string): "script" | "render" | null {
  if (!status) return null;
  if (RENDER_STATUSES.has(status)) return "render";
  if (SCRIPT_STATUSES.has(status)) return "script";
  return null;
}

function scriptFromEvents(events: StreamEvent[]): string {
  const deltas = events
    .filter((event) => event.stage === "script_delta")
    .map((event) => eventValue(event, "delta"))
    .filter((value): value is string => typeof value === "string");
  return deltas.join("");
}

function isAbortError(cause: unknown): boolean {
  return cause instanceof DOMException
    ? cause.name === "AbortError"
    : cause instanceof Error && cause.name === "AbortError";
}

const PERSONA_PRESETS = [
  { id: "theatrical", label: "🎭 Theatrical & Unhinged", desc: "Grand classical flair & existential tragedy" },
  { id: "funny", label: "😂 Funny & Satirical", desc: "Witty comedic timing & sharp hilarious analogies" },
  { id: "serious", label: "💼 Serious & Authoritative", desc: "Executive briefing, sober data-backed urgency" },
  { id: "quirky", label: "🧪 Quirky & Eccentric", desc: "Delightfully weird metaphors & nerd enthusiasm" },
  { id: "cheeky", label: "😏 Cheeky & Provocative", desc: "Playful swagger, calling out industry nonsense" },
  { id: "deep", label: "🌌 Deep & Philosophical", desc: "Poetic, introspective late-night 3am epiphany" },
  { id: "hype", label: "⚡ High-Energy Hype", desc: "Relentless creator momentum & electric excitement" },
  { id: "empathetic", label: "☕ Empathetic & Warm", desc: "Heartfelt, vulnerable mentor coffee chat" },
];

function eventValue(event: StreamEvent, key: string): unknown {
  if (event[key] !== undefined) return event[key];
  if (event.data && typeof event.data === "object") return (event.data as Record<string, unknown>)[key];
  if (event.payload && event.payload[key] !== undefined) return event.payload[key];
  return undefined;
}

function eventLabel(event: StreamEvent) {
  const message = eventValue(event, "message");
  if (typeof message === "string") return message;
  const label = event.stage || event.type || event.event || event.status;
  return label || JSON.stringify(event);
}

function CameraRecorder({ onRecording }: { onRecording: (blob: Blob | null) => void }) {
  const liveRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [cameraIndex, setCameraIndex] = useState(0);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(10);
  const [clipUrl, setClipUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  const stopStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (liveRef.current) liveRef.current.srcObject = null;
    setIsCameraOn(false);
  }, []);

  const startCamera = useCallback(async (deviceId?: string): Promise<MediaStream | null> => {
    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: deviceId
          ? { deviceId: { exact: deviceId }, width: { ideal: 1280 }, height: { ideal: 720 } }
          : { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      setIsCameraOn(true);
      if (liveRef.current) {
        liveRef.current.srcObject = stream;
        liveRef.current.play().catch(() => undefined);
      }
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      setDevices(allDevices.filter((device) => device.kind === "videoinput"));
      setError("");
      return stream;
    } catch (err) {
      console.error("Camera access error:", err);
      setError("Camera access was denied or is unavailable. Please allow camera permissions in your browser.");
      setIsCameraOn(false);
      return null;
    }
  }, []);

  useEffect(() => {
    if (isCameraOn && liveRef.current && streamRef.current) {
      liveRef.current.srcObject = streamRef.current;
      liveRef.current.play().catch(() => undefined);
    }
  }, [isCameraOn]);

  const toggleCamera = async () => {
    if (recording) return;
    if (isCameraOn) {
      stopStream();
    } else {
      await startCamera();
    }
  };

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    stopStream();
  }, [stopStream]);

  useEffect(() => {
    if (!clipUrl) return;
    return () => URL.revokeObjectURL(clipUrl);
  }, [clipUrl]);

  const stopRecording = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = null;
    if (recorderRef.current?.state === "recording") recorderRef.current.stop();
    setRecording(false);
  }, []);

  const beginRecording = async () => {
    let stream = streamRef.current;
    if (!stream || !isCameraOn) {
      stream = await startCamera();
    }
    if (!stream) return;
    if (typeof MediaRecorder === "undefined") {
      setError("MediaRecorder is not supported in this browser.");
      return;
    }

    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "video/webm" });
      const url = URL.createObjectURL(blob);
      setClipUrl(url);
      onRecording(blob);
    };
    recorder.start();
    setSeconds(10);
    setRecording(true);
    let remaining = 10;
    timerRef.current = setInterval(() => {
      remaining -= 1;
      setSeconds(remaining);
      if (remaining <= 0) stopRecording();
    }, 1000);
  };

  const switchCamera = async () => {
    if (devices.length < 2 || recording || !isCameraOn) return;
    const next = (cameraIndex + 1) % devices.length;
    setCameraIndex(next);
    await startCamera(devices[next].deviceId);
  };

  const retake = async () => {
    setClipUrl(null);
    onRecording(null);
    setSeconds(10);
    if (!isCameraOn) await startCamera();
  };

  return (
    <div className="camera-recorder">
      <div className="camera-stage">
        {clipUrl ? (
          <video className="recorded-feed" src={clipUrl} controls playsInline />
        ) : (
          <>
            <video
              className="live-feed"
              ref={liveRef}
              autoPlay
              muted
              playsInline
              style={{ display: isCameraOn ? "block" : "none" }}
            />
            {isCameraOn && (
              <button
                className="camera-stage-toggle-btn"
                onClick={stopStream}
                type="button"
                title="Turn off camera"
              >
                <CameraOff size={14} /> Turn Off
              </button>
            )}
            {!isCameraOn && (
              <div className="camera-standby">
                <CameraOff size={32} />
                <strong>Camera is off</strong>
                <p>Turn on the camera to preview, or click Record to start on demand.</p>
                <button className="camera-permission" onClick={() => startCamera()} type="button">
                  <Camera size={16} /> Turn on camera
                </button>
              </div>
            )}
          </>
        )}
        {recording && <span className="recording-badge"><i />REC</span>}
        {isCameraOn && !clipUrl && (
          <span className="camera-time">00:{String(10 - seconds).padStart(2, "0")} / 00:10</span>
        )}
        {isCameraOn && !clipUrl && (
          <>
            <span className="corner corner-a" /><span className="corner corner-b" />
            <span className="corner corner-c" /><span className="corner corner-d" />
          </>
        )}
      </div>
      {error && <p className="inline-error">{error}</p>}
      <div className="camera-controls">
        <button onClick={retake} type="button" aria-label="Retake recording">
          <RefreshCcw size={17} />
          <span>Retake</span>
        </button>
        <button
          className={`record-button ${recording ? "recording" : ""}`}
          onClick={recording ? stopRecording : beginRecording}
          type="button"
          aria-label={recording ? "Stop recording" : "Start ten second recording"}
          title={recording ? "Stop recording" : "Record 10-second driving take"}
        >
          {recording ? <CircleStop size={25} /> : <span />}
        </button>
        <button
          onClick={toggleCamera}
          disabled={recording}
          type="button"
          aria-label={isCameraOn ? "Turn camera off" : "Turn camera on"}
          title={isCameraOn ? "Turn camera off" : "Turn camera on"}
        >
          {isCameraOn ? <CameraOff size={17} /> : <Camera size={17} />}
          <span>{isCameraOn ? "Turn Off" : "Turn On"}</span>
        </button>
      </div>
    </div>
  );
}

export function CreateWorkbench() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const reduceMotion = useReducedMotion();
  const { name: projectName, setName: setProjectName } = useProjectName();
  const [topic, setTopic] = useState(DEFAULT_TOPIC);
  const [vibe, setVibe] = useState(DEFAULT_VIBE);
  const [script, setScript] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const [projectId, setProjectId] = useState("");
  const [recording, setRecording] = useState<Blob | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [busy, setBusy] = useState<"script" | "render" | null>(null);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState<number | null>(null);
  const [finalVideo, setFinalVideo] = useState("");
  const [mode, setMode] = useState<"move" | "replace">("replace");
  const [avatars, setAvatars] = useState<ApiRecord[]>([]);
  const [avatarImageUrl, setAvatarImageUrl] = useState("");
  const [recentProjects, setRecentProjects] = useState<ApiRecord[]>([]);
  const [tone, setTone] = useState("theatrical");
  const projectIdRef = useRef("");
  const sseActiveRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    projectIdRef.current = projectId;
  }, [projectId]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const applyProject = useCallback((project: Awaited<ReturnType<typeof getProject>>) => {
    setProjectId(project.id);
    localStorage.setItem("charismate_active_project_id", project.id);
    if (typeof project.name === "string" && project.name.trim()) setProjectName(project.name);
    if (typeof project.target_prompt === "string") setTopic(project.target_prompt);
    if (typeof project.avatar_vibe === "string") setVibe(project.avatar_vibe);
    if (typeof project.tone === "string") setTone(project.tone);
    const projectEvents = Array.isArray(project.events) ? (project.events as StreamEvent[]) : [];
    if (projectEvents.length) setEvents(projectEvents);
    const streamed = scriptFromEvents(projectEvents);
    if (typeof project.script === "string" && project.script.trim()) setScript(project.script);
    else if (streamed) setScript(streamed);
    if (typeof project.audio_url === "string" && project.audio_url) setAudioUrl(project.audio_url);
    if (typeof project.final_video_url === "string" && project.final_video_url) {
      setFinalVideo(project.final_video_url);
    }
    if (typeof project.avatar_image_url === "string" && project.avatar_image_url) {
      setAvatarImageUrl(project.avatar_image_url);
    }
    setBusy(busyFromStatus(project.status));
    if (project.status === "completed") setProgress(100);
    if (project.status === "failed") {
      setError("Job processing failed. Check live terminal for details.");
    }
  }, [setProjectName]);

  const loadProjectData = useCallback(async (id: string) => {
    try {
      applyProject(await getProject(id));
    } catch {
      // ignore
    }
  }, [applyProject]);

  useEffect(() => {
    getCollection("/api/avatars").then(setAvatars).catch(() => setAvatars([]));
    getCollection("/api/projects").then(setRecentProjects).catch(() => setRecentProjects([]));

    const paramId = searchParams.get("project_id");
    const storedId = localStorage.getItem("charismate_active_project_id");
    const targetId = paramId || storedId;
    if (targetId) {
      loadProjectData(targetId);
      return;
    }
    const avatarParam = searchParams.get("avatar") || searchParams.get("avatar_url");
    const vibeParam = searchParams.get("vibe");
    const topicParam = searchParams.get("topic");
    if (avatarParam) setAvatarImageUrl(avatarParam);
    if (vibeParam) setVibe(vibeParam);
    if (topicParam) setTopic(topicParam);
  }, [searchParams, loadProjectData]);

  useEffect(() => {
    if (!projectId || busy === null) return;
    const interval = setInterval(async () => {
      try {
        const project = await getProject(projectId);
        if (!project || projectIdRef.current !== projectId) return;
        if (!sseActiveRef.current) {
          applyProject(project);
        } else if (
          project.status === "script_ready" ||
          project.status === "completed" ||
          project.status === "failed"
        ) {
          applyProject(project);
        }
        if (project.status === "completed" || project.status === "script_ready") {
          getCollection("/api/projects").then(setRecentProjects).catch(() => undefined);
        }
      } catch {
        // ignore
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [projectId, busy, applyProject]);

  const handleNewProject = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    sseActiveRef.current = false;
    setProjectId("");
    projectIdRef.current = "";
    localStorage.removeItem("charismate_active_project_id");
    setProjectName("New Project");
    setTopic(DEFAULT_TOPIC);
    setVibe(DEFAULT_VIBE);
    setTone("theatrical");
    setScript("");
    setAudioUrl("");
    setFinalVideo("");
    setEvents([]);
    setBusy(null);
    setProgress(null);
    setError("");
    setRecording(null);
    setAvatarImageUrl("");
    router.replace("/create");
  };

  useEffect(() => {
    if (!projectId || !projectName.trim()) return;
    const timer = window.setTimeout(() => {
      updateProject(projectId, { name: projectName.trim() }).catch(() => undefined);
    }, 500);
    return () => window.clearTimeout(timer);
  }, [projectId, projectName]);

  const appendEvent = (event: StreamEvent, forProjectId: string) => {
    if (projectIdRef.current !== forProjectId) return;
    setEvents((current) => [...current, event]);
    const nextScript = eventValue(event, "script");
    const scriptDelta = eventValue(event, "delta");
    const nextAudio = eventValue(event, "audio_url");
    const nextVideo = eventValue(event, "final_video_url");
    const nextProgress = eventValue(event, "progress");
    if (typeof nextScript === "string") setScript(nextScript);
    else if (typeof scriptDelta === "string") setScript((current) => current + scriptDelta);
    if (typeof nextAudio === "string") setAudioUrl(nextAudio);
    if (typeof nextVideo === "string") setFinalVideo(nextVideo);
    if (typeof nextProgress === "number") setProgress(Math.max(0, Math.min(100, nextProgress)));
    if (event.level === "error" || event.stage === "error") {
      setError(event.message || "The pipeline failed. Check the live terminal for details.");
    }
  };

  const ensureProject = async () => {
    if (projectId) return projectId;
    const project = await createProject({
      name: projectName.trim() || topic.trim().slice(0, 72) || "Untitled project",
      target_prompt: topic,
      avatar_vibe: vibe,
    });
    setProjectId(project.id);
    projectIdRef.current = project.id;
    localStorage.setItem("charismate_active_project_id", project.id);
    getCollection("/api/projects").then(setRecentProjects).catch(() => undefined);
    return project.id;
  };

  const handleGenerate = async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy("script");
    setError("");
    setEvents([]);
    setScript("");
    setAudioUrl("");
    setFinalVideo("");
    try {
      const id = await ensureProject();
      projectIdRef.current = id;
      sseActiveRef.current = true;
      await generateScript(
        { project_id: id, topic, avatar_vibe: vibe, tone },
        (event) => appendEvent(event, id),
        controller.signal,
      );
    } catch (cause) {
      if (!isAbortError(cause)) {
        setError(cause instanceof Error ? cause.message : "Script generation failed.");
      }
    } finally {
      sseActiveRef.current = false;
      if (projectIdRef.current) {
        await loadProjectData(projectIdRef.current);
      }
    }
  };

  const handleRender = async () => {
    if (!recording || !script || !audioUrl) {
      setError("Generate a script with audio and record ten seconds of driving motion first.");
      return;
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy("render");
    setError("");
    setProgress(null);
    setFinalVideo("");
    try {
      const id = await ensureProject();
      projectIdRef.current = id;
      const form = new FormData();
      form.append("project_id", id);
      form.append("avatar_vibe", vibe);
      form.append("audio_url", audioUrl);
      form.append("mode", mode);
      if (avatarImageUrl) form.append("avatar_image_url", avatarImageUrl);
      form.append("driving_video", recording, "motion.webm");
      sseActiveRef.current = true;
      await renderVideo(form, (event) => appendEvent(event, id), controller.signal);
    } catch (cause) {
      if (!isAbortError(cause)) {
        setError(cause instanceof Error ? cause.message : "Video render failed.");
      }
    } finally {
      sseActiveRef.current = false;
      if (projectIdRef.current) {
        await loadProjectData(projectIdRef.current);
      }
    }
  };

  return (
    <section className="workbench">
      <div className="work-panel script-panel">
        <div className="panel-heading workbench-panel-heading">
          <div className="panel-heading-title">
            <span>Step 1</span>
            <h2>Generate script & context</h2>
          </div>
          <div className="workbench-job-controls">
            <button
              className="new-job-btn"
              onClick={handleNewProject}
              type="button"
              title="Start a new video project without waiting"
            >
              <Plus size={13} /> New Job
            </button>
            {recentProjects.length > 0 && (
              <select
                className="job-selector"
                value={projectId}
                onChange={(e) => {
                  if (e.target.value) {
                    loadProjectData(e.target.value);
                  } else {
                    handleNewProject();
                  }
                }}
                title="Switch between past or in-progress jobs"
              >
                <option value="">Current Draft</option>
                {recentProjects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.status === "completed" ? "✓ " : busyFromStatus(String(p.status || "")) ? "⏳ " : p.status === "script_ready" ? "▸ " : "• "}
                    {String(p.name || p.id).slice(0, 24)}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>
        <div className="field">
          <div className="field-header">
            <span>1. What&apos;s your video about?</span>
            <FieldActions value={topic} onChange={setTopic} />
          </div>
          <textarea maxLength={250} value={topic} onChange={(event) => setTopic(event.target.value)} />
          <small>{topic.length} / 250</small>
        </div>
        <div className="field">
          <div className="field-header">
            <span>2. Persona & Script Tone <i>Customize tone of voice</i></span>
          </div>
          <select
            className="persona-tone-select"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
          >
            {PERSONA_PRESETS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label} — {p.desc}
              </option>
            ))}
          </select>
        </div>
        <div className="generation-options">
          <div>
            <span className="option-label">Motion mode</span>
            <div className="mode-switch" role="group" aria-label="Avatar motion mode">
              <button className={mode === "move" ? "active" : ""} onClick={() => setMode("move")} type="button">Move</button>
              <button className={mode === "replace" ? "active" : ""} onClick={() => setMode("replace")} type="button">Replace</button>
            </div>
          </div>
          <label>
            <span className="option-label">Saved avatar</span>
            <select value={avatarImageUrl} onChange={(event) => setAvatarImageUrl(event.target.value)}>
              <option value="">Generate a new avatar</option>
              {avatars.map((avatar) => (
                <option key={avatar.id} value={String(avatar.image_url || "")}>{avatar.name || "Saved avatar"}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="field">
          <div className="field-header">
            <span>3. Avatar vibe <i>Describe your character</i></span>
            <FieldActions value={vibe} onChange={setVibe} />
          </div>
          <textarea maxLength={250} value={vibe} onChange={(event) => setVibe(event.target.value)} />
          <small>{vibe.length} / 250</small>
        </div>
        <button className="gradient-button" disabled={busy !== null || !topic.trim()} onClick={handleGenerate} type="button">
          {busy === "script" ? <LoaderCircle className="spin" size={16} /> : <WandSparkles size={16} />}
          {busy === "script" ? "Generating from API…" : "Generate script & extract context"}
        </button>

        <div className="section-divider"><span>{script ? <><Check size={12} />Script generated</> : "Generated output"}</span></div>
        <div className="field script-output">
          <div className="field-header">
            <span>Your script</span>
            <FieldActions value={script} onChange={setScript} />
          </div>
          <div className="quote-mark">“</div>
          <textarea
            placeholder="Your generated script will appear here from the live API."
            value={script}
            onChange={(event) => setScript(event.target.value)}
          />
        </div>
        <div className="audio-player">
          <AudioLines size={17} />
          {audioUrl ? (
            <audio controls src={audioUrl}>Your browser does not support audio.</audio>
          ) : (
            <><button disabled aria-label="Audio unavailable"><Play size={13} fill="currentColor" /></button><div className="waveform" aria-hidden="true">{Array.from({ length: 28 }, (_, index) => <i key={index} />)}</div><span>—:—</span></>
          )}
        </div>
      </div>

      <div className="work-panel motion-panel">
        <div className="panel-heading"><span>Step 2</span><h2>Record driving motion</h2></div>
        <div className="teleprompter-head">
          <span><Video size={14} />Teleprompter</span>
          <FieldActions value={script} onChange={setScript} copyLabel="Copy" clearLabel="Clear" />
        </div>
        <div className="teleprompter">
          {script ? <p>{script}</p> : <p className="placeholder">Generate a script to load your teleprompter.</p>}
        </div>
        <div className="teleprompter-head"><span><Camera size={14} />Camera</span><small>Keep your face centered</small></div>
        <CameraRecorder onRecording={setRecording} />
        <button className="gradient-button render-button" disabled={busy !== null || !recording || !script || !audioUrl} onClick={handleRender} type="button">
          {busy === "render" ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}
          {busy === "render" ? "Rendering from API…" : "Charismate it — Render video"}
        </button>
        <p className="button-hint">Your motion drives the avatar in the final video.</p>
      </div>

      <div className="work-panel terminal-panel">
        <div className="terminal-title"><span><TerminalSquare size={15} />Live terminal</span>{events.length > 0 && <button onClick={() => setEvents([])} type="button">Clear</button>}</div>
        <div className="terminal-output" role="log" aria-live="polite">
          {events.length === 0 ? (
            <div className="terminal-empty"><Send size={20} /><p>Live backend events will appear here when generation begins.</p></div>
          ) : events.map((event, index) => (
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, x: -5 }}
              animate={{ opacity: 1, x: 0 }}
              className="terminal-line"
              key={`${index}-${eventLabel(event)}`}
            >
              <span>{event.stage === "done" || event.status === "complete" || event.type === "complete" ? <Check size={12} /> : <i />}</span>
              <code>
                <b>[{event.stage || event.type || "event"}]</b> {eventLabel(event)}
                {event.payload && Object.keys(event.payload).length > 0 && event.stage !== "script_delta" ? (
                  <pre>{JSON.stringify(event.payload, null, 2)}</pre>
                ) : null}
                <time>{event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ""}</time>
              </code>
            </motion.div>
          ))}
        </div>
        {progress !== null && (
          <div className="render-progress">
            <div><span>Rendering final video…</span><strong>{Math.round(progress)}%</strong></div>
            <div className="progress-track"><motion.i animate={{ width: `${progress}%` }} /></div>
          </div>
        )}
        <AnimatePresence mode="wait">
          {finalVideo ? (
            <motion.div initial={reduceMotion ? false : { opacity: 0 }} animate={{ opacity: 1 }} className="final-video" key="video">
              <video src={finalVideo} controls playsInline />
              <div><span><Check size={14} />Your Charismate is ready</span><a href={finalVideo} download><Download size={14} />Download</a></div>
            </motion.div>
          ) : (
            <motion.div className="render-preview" key="preview">
              <div className="preview-glow"><Clapperboard size={38} /></div>
              <span>Final render</span><p>Your completed video will appear here from the API.</p>
            </motion.div>
          )}
        </AnimatePresence>
        {error && <div className="api-error">{error}</div>}
      </div>
    </section>
  );
}
