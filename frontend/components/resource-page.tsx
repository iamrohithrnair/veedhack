"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Clapperboard, FolderOpen, LoaderCircle, Plus, RefreshCw } from "lucide-react";
import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { getCollection, getProject } from "@/lib/api";
import type { ApiRecord, Project } from "@/lib/types";

type ResourcePageProps = {
  endpoint: string;
  title: string;
  description: string;
  actionLabel?: string;
};

const displayName = (item: ApiRecord) => item.name || item.title || `Item ${item.id}`;

export function ResourcePage({ endpoint, title, description, actionLabel }: ResourcePageProps) {
  const [items, setItems] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const reduceMotion = useReducedMotion();

  const load = () => {
    setLoading(true);
    setError(false);
    getCollection(endpoint)
      .then(setItems)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  useEffect(load, [endpoint]);

  return (
    <section className="resource-page">
      <div className="page-title-row">
        <div><span className="eyebrow">Workspace</span><h2>{title}</h2><p>{description}</p></div>
        {actionLabel && <Link className="primary-button" href="/create"><Plus size={16} />{actionLabel}</Link>}
      </div>

      {loading ? (
        <div className="empty-state"><LoaderCircle className="spin" /><strong>Loading {title.toLowerCase()}…</strong></div>
      ) : error ? (
        <div className="empty-state">
          <RefreshCw />
          <strong>Couldn&apos;t reach the Charismate API</strong>
          <p>Start the backend and try again. No placeholder records are shown.</p>
          <button className="secondary-button" onClick={load}>Try again</button>
        </div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <FolderOpen />
          <strong>No {title.toLowerCase()} yet</strong>
          <p>Your real backend records will appear here as soon as they are available.</p>
          {actionLabel && <Link className="primary-button" href="/create"><Plus size={16} />{actionLabel}</Link>}
        </div>
      ) : (
        <div className="resource-grid">
          {items.map((item, index) => {
            const media = item.thumbnail_url || item.image_url;
            const content = (
              <>
                <div className="resource-media">
                  {typeof media === "string" ? (
                    <Image src={media} alt="" fill sizes="(max-width: 760px) 100vw, 300px" unoptimized />
                  ) : (
                    <Clapperboard size={30} />
                  )}
                  {item.status && <span className="status-pill">{item.status}</span>}
                </div>
                <div className="resource-copy">
                  <strong>{displayName(item)}</strong>
                  <p>{item.description || item.created_at || "Ready in your workspace"}</p>
                  <ArrowRight size={16} />
                </div>
              </>
            );
            return (
              <motion.article
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.04, 0.2) }}
                className="resource-card"
                key={item.id}
              >
                {endpoint === "/api/projects" ? <Link href={`/projects/${item.id}`}>{content}</Link> : content}
              </motion.article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export function DashboardPage() {
  const [projects, setProjects] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    getCollection("/api/projects")
      .then(setProjects)
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="dashboard-page">
      <div className="dashboard-hero">
        <div>
          <span className="eyebrow">AI video studio</span>
          <h2>Turn an idea into a<br /><span>charismatic video.</span></h2>
          <p>Write the script, capture your performance, and render a share-ready avatar video in one workflow.</p>
          <Link className="primary-button" href="/create"><Plus size={16} />Create a video</Link>
        </div>
        <div className="hero-orb"><Image src="/logo.png" alt="" width={230} height={230} priority /></div>
      </div>
      <div className="dashboard-section-head"><h3>Recent projects</h3><Link href="/projects">View all <ArrowRight size={14} /></Link></div>
      {loading ? <div className="panel-loading"><LoaderCircle className="spin" />Loading projects…</div> :
        offline || projects.length === 0 ? (
          <div className="compact-empty">{offline ? "The API is unavailable." : "No projects yet."} Start with your first real creation.</div>
        ) : (
          <div className="resource-grid compact">
            {projects.slice(0, 4).map((project) => (
              <article className="resource-card" key={project.id}>
                <Link href={`/projects/${project.id}`}>
                  <div className="resource-media"><Clapperboard /></div>
                  <div className="resource-copy"><strong>{displayName(project)}</strong><p>{project.status || project.created_at}</p><ArrowRight size={16} /></div>
                </Link>
              </article>
            ))}
          </div>
        )}
    </section>
  );
}

export function ProjectDetail({ id }: { id: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getProject(id).then(setProject).catch(() => setError(true));
  }, [id]);

  if (error) return <div className="empty-state"><RefreshCw /><strong>Project unavailable</strong><p>The backend could not return this project.</p></div>;
  if (!project) return <div className="empty-state"><LoaderCircle className="spin" /><strong>Loading project…</strong></div>;

  return (
    <section className="project-detail">
      <Link className="back-link" href="/projects">← All projects</Link>
      <div className="page-title-row"><div><span className="eyebrow">Project</span><h2>{displayName(project)}</h2><p>{project.status || "Project details"}</p></div></div>
      {project.final_video_url || project.video_url ? <video className="detail-video" src={String(project.final_video_url || project.video_url)} controls playsInline /> : <div className="empty-state"><Clapperboard /><strong>No rendered video yet</strong></div>}
      <div className="detail-grid">
        <div className="detail-card"><span>Topic</span><p>{project.target_prompt || project.topic || "Not provided"}</p></div>
        <div className="detail-card"><span>Avatar direction</span><p>{project.avatar_vibe || "Not provided"}</p></div>
        <div className="detail-card wide"><span>Script</span><p>{project.script || "No script saved for this project."}</p></div>
        {project.extracted && (
          <div className="detail-card wide"><span>Extracted context</span><pre>{JSON.stringify(project.extracted, null, 2)}</pre></div>
        )}
        {project.events && project.events.length > 0 && (
          <div className="detail-card wide">
            <span>Pipeline history</span>
            <div className="history-log">
              {project.events.map((event, index) => (
                <code key={`${event.timestamp || index}-${index}`}>
                  <b>[{event.stage || "event"}]</b> {event.message}
                  {event.payload && Object.keys(event.payload).length > 0 ? <pre>{JSON.stringify(event.payload, null, 2)}</pre> : null}
                </code>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
