"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  Clapperboard,
  Image as ImageIcon,
  LoaderCircle,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  Upload,
  UserPlus,
  Video,
  WandSparkles,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { deleteAvatar, generateAvatar, getCollection, uploadAvatar } from "@/lib/api";
import type { ApiRecord } from "@/lib/types";
import { FieldActions } from "@/components/field-actions";

export default function AvatarsPage() {
  const router = useRouter();
  const reduceMotion = useReducedMotion();
  const [avatars, setAvatars] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // Modal states
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Generate form state
  const [genName, setGenName] = useState("");
  const [genPrompt, setGenPrompt] = useState("");
  const [genVibe, setGenVibe] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState("");

  // Upload form state
  const [upName, setUpName] = useState("");
  const [upVibe, setUpVibe] = useState("");
  const [upFile, setUpFile] = useState<File | null>(null);
  const [upPreview, setUpPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [upError, setUpError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadAvatars = () => {
    setLoading(true);
    setError(false);
    getCollection("/api/avatars")
      .then(setAvatars)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(loadAvatars, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!genName.trim() || !genPrompt.trim()) {
      setGenError("Please provide both a name and a character prompt.");
      return;
    }
    setGenerating(true);
    setGenError("");
    try {
      const created = await generateAvatar({
        name: genName.trim(),
        prompt: genPrompt.trim(),
        vibe: genVibe.trim() || undefined,
      });
      setAvatars((prev) => [created, ...prev]);
      setShowGenerateModal(false);
      setGenName("");
      setGenPrompt("");
      setGenVibe("");
    } catch (err) {
      setGenError(err instanceof Error ? err.message : "Failed to generate avatar.");
    } finally {
      setGenerating(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setUpFile(file);
      const url = URL.createObjectURL(file);
      setUpPreview(url);
      if (!upName.trim()) {
        const cleanName = file.name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
        setUpName(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!upFile) {
      setUpError("Please choose an image file to upload.");
      return;
    }
    if (!upName.trim()) {
      setUpError("Please provide an avatar name.");
      return;
    }
    setUploading(true);
    setUpError("");
    try {
      const formData = new FormData();
      formData.append("name", upName.trim());
      if (upVibe.trim()) formData.append("vibe", upVibe.trim());
      formData.append("image_file", upFile);

      const created = await uploadAvatar(formData);
      setAvatars((prev) => [created, ...prev]);
      setShowUploadModal(false);
      setUpName("");
      setUpVibe("");
      setUpFile(null);
      setUpPreview(null);
    } catch (err) {
      setUpError(err instanceof Error ? err.message : "Failed to upload avatar.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      await deleteAvatar(id);
      setAvatars((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete avatar.");
    }
  };

  return (
    <section className="resource-page">
      <div className="page-title-row">
        <div>
          <span className="eyebrow">Character Studio</span>
          <h2>Avatars</h2>
          <p>Create AI personas or upload real portrait photos to drive your videos.</p>
        </div>
        <div className="header-button-group">
          <button
            className="secondary-button"
            onClick={() => {
              setUpError("");
              setShowUploadModal(true);
            }}
            type="button"
          >
            <Upload size={15} /> Upload Photo
          </button>
          <button
            className="primary-button"
            onClick={() => {
              setGenError("");
              setShowGenerateModal(true);
            }}
            type="button"
          >
            <WandSparkles size={15} /> Generate with AI
          </button>
        </div>
      </div>

      {loading ? (
        <div className="empty-state">
          <LoaderCircle className="spin" size={24} />
          <strong>Loading avatar library…</strong>
        </div>
      ) : error ? (
        <div className="empty-state">
          <RefreshCw size={24} />
          <strong>Couldn&apos;t reach the Charismate API</strong>
          <p>Make sure the backend is running and try again.</p>
          <button className="secondary-button" onClick={loadAvatars} type="button">
            Try again
          </button>
        </div>
      ) : avatars.length === 0 ? (
        <div className="empty-state">
          <UserPlus size={36} />
          <strong>No avatars in your library yet</strong>
          <p>Generate an AI character with Flux / Nano-Banana or upload your own portrait photo to get started.</p>
          <div className="empty-state-actions">
            <button
              className="primary-button"
              onClick={() => setShowGenerateModal(true)}
              type="button"
            >
              <Sparkles size={15} /> Generate AI Avatar
            </button>
            <button
              className="secondary-button"
              onClick={() => setShowUploadModal(true)}
              type="button"
            >
              <Upload size={15} /> Upload Photo
            </button>
          </div>
        </div>
      ) : (
        <div className="resource-grid">
          {avatars.map((avatar, index) => {
            const imgUrl = String(avatar.image_url || avatar.thumbnail_url || "");
            return (
              <motion.article
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.04, 0.2) }}
                className="resource-card avatar-gallery-card"
                key={avatar.id}
              >
                <div className="resource-media avatar-media">
                  {imgUrl ? (
                    <Image src={imgUrl} alt={String(avatar.name || "Avatar")} fill sizes="(max-width: 760px) 100vw, 320px" unoptimized />
                  ) : (
                    <Clapperboard size={32} />
                  )}
                  {avatar.vibe ? <span className="status-pill">{String(avatar.vibe).slice(0, 24)}</span> : null}
                </div>
                <div className="resource-copy avatar-copy">
                  <div>
                    <strong>{String(avatar.name || "Unnamed Avatar")}</strong>
                    <p>{String(avatar.vibe || avatar.created_at || "Custom Avatar")}</p>
                  </div>
                  <div className="avatar-card-actions">
                    <Link
                      className="avatar-use-btn"
                      href={`/create?avatar=${encodeURIComponent(imgUrl)}${avatar.vibe ? `&vibe=${encodeURIComponent(String(avatar.vibe))}` : ""}`}
                      title="Use this avatar in a video project"
                    >
                      <Video size={13} />
                      <span>Use</span>
                    </Link>
                    <button
                      className="avatar-delete-btn"
                      onClick={() => handleDelete(String(avatar.id), String(avatar.name || "avatar"))}
                      type="button"
                      aria-label="Delete avatar"
                      title="Delete avatar"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </motion.article>
            );
          })}
        </div>
      )}

      {/* Generate Avatar Modal */}
      <AnimatePresence>
        {showGenerateModal && (
          <div className="modal-backdrop" onClick={() => !generating && setShowGenerateModal(false)}>
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="modal-box"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-header">
                <div>
                  <span className="eyebrow"><WandSparkles size={12} /> Fal.ai Nano-Banana</span>
                  <h3>Generate AI Avatar</h3>
                </div>
                <button
                  className="modal-close-btn"
                  disabled={generating}
                  onClick={() => setShowGenerateModal(false)}
                  type="button"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleGenerate} className="modal-form">
                <div className="field">
                  <div className="field-header">
                    <span>Character Name</span>
                    <FieldActions value={genName} onChange={setGenName} />
                  </div>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 18th-Century Philosopher, Alex Vance, Tech Host"
                    value={genName}
                    onChange={(e) => setGenName(e.target.value)}
                    disabled={generating}
                  />
                </div>

                <div className="field">
                  <div className="field-header">
                    <span>Visual Prompt / Style <i>Detailed visual description</i></span>
                    <FieldActions value={genPrompt} onChange={setGenPrompt} />
                  </div>
                  <textarea
                    required
                    placeholder="e.g. A dramatic, wise 18th-century philosopher in an oil painting style, studio lighting, looking directly at camera"
                    value={genPrompt}
                    onChange={(e) => setGenPrompt(e.target.value)}
                    disabled={generating}
                  />
                </div>

                <div className="field">
                  <div className="field-header">
                    <span>Vibe / Tag <i>(Optional)</i></span>
                    <FieldActions value={genVibe} onChange={setGenVibe} />
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. Dramatic Outrage, Confident Founder, Calm Sage"
                    value={genVibe}
                    onChange={(e) => setGenVibe(e.target.value)}
                    disabled={generating}
                  />
                </div>

                {genError && <div className="api-error">{genError}</div>}

                <div className="modal-actions">
                  <button
                    className="secondary-button"
                    disabled={generating}
                    onClick={() => setShowGenerateModal(false)}
                    type="button"
                  >
                    Cancel
                  </button>
                  <button className="primary-button" disabled={generating || !genName.trim() || !genPrompt.trim()} type="submit">
                    {generating ? <LoaderCircle className="spin" size={15} /> : <Sparkles size={15} />}
                    {generating ? "Generating with Fal.ai…" : "Generate Avatar"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Upload Avatar Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <div className="modal-backdrop" onClick={() => !uploading && setShowUploadModal(false)}>
            <motion.div
              initial={reduceMotion ? false : { opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              className="modal-box"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="modal-header">
                <div>
                  <span className="eyebrow"><Upload size={12} /> Studio Upload</span>
                  <h3>Upload Custom Avatar Photo</h3>
                </div>
                <button
                  className="modal-close-btn"
                  disabled={uploading}
                  onClick={() => setShowUploadModal(false)}
                  type="button"
                >
                  <X size={18} />
                </button>
              </div>

              <form onSubmit={handleUpload} className="modal-form">
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/jpg,image/webp,image/avif"
                  ref={fileInputRef}
                  style={{ display: "none" }}
                  onChange={handleFileChange}
                  disabled={uploading}
                />

                <div
                  className="upload-dropzone"
                  onClick={() => !uploading && fileInputRef.current?.click()}
                >
                  {upPreview ? (
                    <div className="upload-preview-wrap">
                      <Image src={upPreview} alt="Preview" width={110} height={110} unoptimized />
                      <p>Click to choose a different photo</p>
                    </div>
                  ) : (
                    <div className="upload-prompt">
                      <ImageIcon size={32} />
                      <strong>Click to upload an image</strong>
                      <p>PNG, JPG, WEBP up to 25MB. Front-facing portraits with good lighting work best.</p>
                    </div>
                  )}
                </div>

                <div className="field">
                  <div className="field-header">
                    <span>Avatar Name</span>
                    <FieldActions value={upName} onChange={setUpName} />
                  </div>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Sarah Jenkins (VP Sales)"
                    value={upName}
                    onChange={(e) => setUpName(e.target.value)}
                    disabled={uploading}
                  />
                </div>

                <div className="field">
                  <div className="field-header">
                    <span>Vibe / Role <i>(Optional)</i></span>
                    <FieldActions value={upVibe} onChange={setUpVibe} />
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. Warm and Confident, Executive Explainer"
                    value={upVibe}
                    onChange={(e) => setUpVibe(e.target.value)}
                    disabled={uploading}
                  />
                </div>

                {upError && <div className="api-error">{upError}</div>}

                <div className="modal-actions">
                  <button
                    className="secondary-button"
                    disabled={uploading}
                    onClick={() => setShowUploadModal(false)}
                    type="button"
                  >
                    Cancel
                  </button>
                  <button className="primary-button" disabled={uploading || !upFile || !upName.trim()} type="submit">
                    {uploading ? <LoaderCircle className="spin" size={15} /> : <Upload size={15} />}
                    {uploading ? "Uploading to Fal…" : "Save Avatar"}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </section>
  );
}
