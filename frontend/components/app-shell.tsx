"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import {
  Blocks,
  ChevronDown,
  Clock3,
  FolderOpen,
  LayoutDashboard,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  Sparkles,
  Sun,
  UserRound,
  UsersRound,
  X,
  Zap,
} from "lucide-react";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

const nav = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/create", label: "Create", icon: Zap },
  { href: "/projects", label: "Projects", icon: FolderOpen },
  { href: "/avatars", label: "Avatars", icon: UsersRound },
  { href: "/templates", label: "Templates", icon: Blocks },
  { href: "/history", label: "History", icon: Clock3 },
];

type ProjectNameState = {
  name: string;
  setName: (name: string) => void;
};

const ProjectNameContext = createContext<ProjectNameState>({
  name: "New Project",
  setName: () => undefined,
});

export const useProjectName = () => useContext(ProjectNameContext);

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const reduceMotion = useReducedMotion();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [projectName, setProjectName] = useState("New Project");
  const [credits, setCredits] = useState<number | null>(1000);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const isCreate = pathname === "/create";
  const isPremiere = pathname === "/demo";

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const savedTheme = (localStorage.getItem("charismate-theme") as "dark" | "light") || "dark";
    setTheme(savedTheme);
    document.documentElement.setAttribute("data-theme", savedTheme);

    const savedSidebar = localStorage.getItem("charismate-sidebar-collapsed") === "true";
    setSidebarCollapsed(savedSidebar);
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setSidebarCollapsed((prev) => {
          const next = !prev;
          localStorage.setItem("charismate-sidebar-collapsed", String(next));
          return next;
        });
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    setTheme(nextTheme);
    localStorage.setItem("charismate-theme", nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
  };

  const toggleSidebar = () => {
    const next = !sidebarCollapsed;
    setSidebarCollapsed(next);
    localStorage.setItem("charismate-sidebar-collapsed", String(next));
  };

  useEffect(() => {
    fetch(`${(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "")}/api/wallet`)
      .then((response) => (response.ok ? response.json() : Promise.reject()))
      .then((data: { remaining?: number; credits?: number; balance?: number; credit_balance?: number; spent?: number }) =>
        setCredits(
          data.remaining ??
            (typeof data.credits === "number" && typeof data.spent === "number"
              ? Math.max(0, data.credits - data.spent)
              : data.credits ?? data.balance ?? data.credit_balance ?? 1000),
        ),
      )
      .catch(() => setCredits(1000));
  }, []);

  const sectionTitle =
    nav.find((item) => pathname === item.href || pathname.startsWith(`${item.href}/`))?.label ||
    "Charismate";

  return (
    <ProjectNameContext.Provider value={{ name: projectName, setName: setProjectName }}>
      <div
        className={`app-shell ${theme === "light" ? "theme-light" : "theme-dark"} ${
          sidebarCollapsed ? "sidebar-collapsed" : ""
        } ${isPremiere ? "premiere-shell" : ""}`}
      >
      <button
        className="mobile-menu-button"
        onClick={() => setMenuOpen((open) => !open)}
        aria-label={menuOpen ? "Close navigation" : "Open navigation"}
      >
        {menuOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <aside className={`sidebar ${menuOpen ? "sidebar-open" : ""} ${sidebarCollapsed ? "collapsed" : ""}`}>
        <Link className="brand" href="/dashboard" aria-label="Charismate dashboard">
          <Image src="/logo.png" width={38} height={38} alt="" priority />
          {!sidebarCollapsed && (
            <span>
              <strong>charismate</strong>
              <small>The Universal Multimodal Video Engine</small>
            </span>
          )}
        </Link>

        <nav aria-label="Primary navigation">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/create" && pathname.startsWith(`${href}/`));
            return (
              <Link
                className={`nav-link ${active ? "active" : ""}`}
                href={href}
                key={href}
                title={sidebarCollapsed ? label : undefined}
              >
                <Icon size={18} aria-hidden="true" />
                {!sidebarCollapsed && <span>{label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          {!sidebarCollapsed ? (
            <div className="pro-card">
              <span className="eyebrow"><Sparkles size={13} /> Pro Plan</span>
              <strong>Unlock Unlimited Charismates</strong>
              <ul className="pro-features">
                <li>✓ Unlimited Videos</li>
                <li>✓ Priority Rendering</li>
                <li>✓ Custom Avatars</li>
                <li>✓ Early Access</li>
              </ul>
              <button type="button">Upgrade Now <Zap size={13} /></button>
            </div>
          ) : (
            <div className="pro-card-compact" title="Pro Plan: Unlimited Charismates">
              <Sparkles size={16} />
            </div>
          )}
          <button className="user-chip" type="button" title={sidebarCollapsed ? "Sullivan (sullivan@charismate.ai)" : undefined}>
            <span className="user-avatar"><UserRound size={16} /></span>
            {!sidebarCollapsed && (
              <>
                <span><strong>Sullivan</strong><small>sullivan@charismate.ai</small></span>
                <ChevronDown size={14} />
              </>
            )}
          </button>
        </div>
      </aside>

      {menuOpen && <button className="nav-backdrop" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}

      <div className="main-column">
        <header className="topbar">
          <div className="project-heading">
            <button
              className="topbar-sidebar-toggle"
              onClick={toggleSidebar}
              type="button"
              aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {sidebarCollapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            </button>
            {isCreate || isPremiere ? (
              <label>
                <span className="sr-only">Project name</span>
                <input
                  value={isPremiere ? "Pioneer Pitch" : projectName}
                  onChange={(event) => setProjectName(event.target.value)}
                  readOnly={isPremiere}
                />
                {!isPremiere && <Pencil size={13} aria-hidden="true" />}
              </label>
            ) : (
              <h1>{sectionTitle}</h1>
            )}
          </div>
          {(isCreate || isPremiere) && (
            <ol className="stepper" aria-label="Creation progress">
              {["Script & Context", "Record Motion", "Render Video"].map((step, index) => (
                <li className={index === 0 ? "current" : ""} key={step}>
                  <span>{index + 1}</span>{step}
                  {index < 2 && <i aria-hidden="true">›</i>}
                </li>
              ))}
            </ol>
          )}
          <div className="topbar-actions">
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              type="button"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
              <span>{theme === "dark" ? "Light" : "Dark"}</span>
            </button>
            <div className="credits">
              <Zap size={15} className="credits-icon" fill="currentColor" />
              <span>{credits === null ? "1,000" : credits.toLocaleString()} Credits</span>
              <button className="credits-add-btn" type="button" aria-label="Buy credits" title="Add credits">
                <Plus size={13} />
              </button>
            </div>
            <div className="header-user-avatar" title="Account">
              <span className="avatar-letter">S</span>
              <ChevronDown size={13} />
            </div>
          </div>
        </header>

        <motion.main
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22 }}
          className="page-content"
        >
          {children}
        </motion.main>
      </div>
      </div>
    </ProjectNameContext.Provider>
  );
}
