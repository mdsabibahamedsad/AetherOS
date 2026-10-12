import { Button } from '../components/button'
import { $route, openLogDir } from '../store'
import { ArrowLeft, ExternalLink, FileText } from 'lucide-react'

const ABOUT_SECTIONS = [
  {
    title: 'Aetheros Setup',
    items: [
      { label: 'Version', value: '0.0.1' },
      { label: 'Publisher', value: 'AetherOS' },
      { label: 'Target', value: 'Aetheros Personal AI Agent' },
    ],
  },
  {
    title: 'System',
    items: [
      { label: 'Platform', value: getPlatform() },
      { label: 'Architecture', value: getArch() },
    ],
  },
]

function getPlatform(): string {
  if (navigator.userAgent.includes('Windows')) return 'Windows'
  if (navigator.userAgent.includes('Mac')) return 'macOS'
  if (navigator.userAgent.includes('Linux')) return 'Linux'
  return 'Unknown'
}

function getArch(): string {
  return navigator.userAgent.includes('x86_64') ||
    navigator.userAgent.includes('Win64')
    ? 'x86_64'
    : navigator.userAgent.includes('aarch64') ||
        navigator.userAgent.includes('ARM64')
      ? 'arm64'
      : 'Unknown'
}

export default function About() {
  return (
    <div className="aetheros-fade-in flex h-full flex-col px-12 py-8">
      <div className="flex-1">
        <div className="mb-6">
          <h1 className="text-lg font-semibold text-foreground">
            About Aetheros Setup
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Installer information and system details.
          </p>
        </div>

        <div className="space-y-6">
          {ABOUT_SECTIONS.map((section) => (
            <div key={section.title}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {section.title}
              </h2>
              <div className="divide-y divide-border rounded-lg border border-border">
                {section.items.map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between px-4 py-2.5"
                  >
                    <span className="text-sm text-muted-foreground">
                      {item.label}
                    </span>
                    <span className="text-sm font-medium text-foreground">
                      {item.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 space-y-2">
          <a
            href="https://aetheros.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ExternalLink size={14} />
            Visit Aetheros website
          </a>

          <button
            type="button"
            onClick={() => void openLogDir()}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <FileText size={14} />
            Open log folder
          </button>
        </div>

        <div className="mt-8 rounded-lg border border-border/60 bg-card/30 px-4 py-3">
          <p className="text-xs leading-relaxed text-muted-foreground/70">
            Copyright &copy; 2026 AetherOS. All rights reserved.
            <br />
            Aetheros is built with Tauri, React, and Rust.
          </p>
        </div>
      </div>

      <div className="mt-6 border-t border-border pt-4">
        <Button
          variant="ghost"
          onClick={() => $route.set('welcome')}
          className="inline-flex items-center gap-2"
        >
          <ArrowLeft size={16} />
          Back
        </Button>
      </div>
    </div>
  )
}
