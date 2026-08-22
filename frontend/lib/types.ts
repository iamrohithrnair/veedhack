export type ApiRecord = {
  id: string;
  name?: string;
  title?: string;
  status?: string;
  description?: string;
  thumbnail_url?: string;
  image_url?: string;
  video_url?: string;
  created_at?: string;
  updated_at?: string;
  [key: string]: unknown;
};

export type Project = ApiRecord & {
  topic?: string;
  target_prompt?: string;
  avatar_vibe?: string;
  tone?: string;
  script?: string;
  audio_url?: string;
  avatar_image_url?: string;
  driving_video_url?: string;
  video_url?: string;
  final_video_url?: string;
  extracted?: Record<string, unknown>;
  events?: StreamEvent[];
};

export type StreamEvent = {
  event?: string;
  type?: string;
  stage?: string;
  level?: string;
  message?: string;
  status?: string;
  progress?: number;
  script?: string;
  audio_url?: string;
  video_url?: string;
  final_video_url?: string;
  url?: string;
  data?: unknown;
  payload?: Record<string, unknown>;
  timestamp?: string;
  [key: string]: unknown;
};

export type CreateProjectInput = {
  name: string;
  target_prompt: string;
  avatar_vibe: string;
};

export type GenerateScriptInput = {
  project_id: string;
  topic: string;
  avatar_vibe: string;
  tone?: string;
};
