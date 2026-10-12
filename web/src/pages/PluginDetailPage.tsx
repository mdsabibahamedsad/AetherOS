import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Package,
  Star,
  Download,
  ArrowLeft,
  ExternalLink,
  GitHub,
  Book,
  Shield,
  Award,
  Clock,
  Tag,
  ChevronDown,
  ChevronUp,
  RotateCw,
  Power,
  Trash2,
  Undo,
  User,
  Calendar,
  AlertTriangle,
  Check,
  X,
  FileText,
  GitBranch,
  Layers,
  Lock,
  Globe,
  Cpu,
  FolderOpen,
  MessageSquare,
  Monitor,
  Mic,
  Bell,
  Camera,
  Clipboard,
  Network,
  HardDrive,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  DownloadCloud,
  RefreshCw,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Switch } from "@nous-research/ui/ui/components/switch";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type {
  PluginMarketEntry,
  PluginDetailResponse,
  PluginReview,
  PluginVersion,
  PluginPermissions,
} from "@/lib/api";
import { usePageHeader } from "@/contexts/usePageHeader";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";

type Tab = "readme" | "versions" | "reviews" | "dependencies" | "permissions" | "screenshots";

const PERMISSION_ICONS: Record<string, typeof FolderOpen> = {
  filesystem: FolderOpen,
  network: Globe,
  environment: Cpu,
  system: Monitor,
  browser: Monitor,
  clipboard: Clipboard,
  microphone: Mic,
  camera: Camera,
  notifications: Bell,
};

const PERMISSION_LABELS: Record<string, string> = {
  filesystem: "File System",
  network: "Network",
  environment: "Environment",
  system: "System",
  browser: "Browser",
  clipboard: "Clipboard",
  microphone: "Microphone",
  camera: "Camera",
  notifications: "Notifications",
};

export default function PluginDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<PluginDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("readme");
  const [installing, setInstalling] = useState(false);
  const [enabled, setEnabled] = useState(true);
  const [screenshotIdx, setScreenshotIdx] = useState(0);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadDetail = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const result = await api.getPluginDetail(id);
      setData(result);
      setEnabled(result.entry.enabled);
    } catch (e) {
      showToast(`Failed to load plugin: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [id, showToast]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button ghost size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Back
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, navigate]);

  const handleInstall = async () => {
    if (!id) return;
    setInstalling(true);
    try {
      await api.installMarketplacePlugin(id);
      showToast("Plugin installed successfully", "success");
      await loadDetail();
    } catch (e) {
      showToast(`Install failed: ${e}`, "error");
    } finally {
      setInstalling(false);
    }
  };

  const handleUpdate = async () => {
    if (!id) return;
    setInstalling(true);
    try {
      await api.updateMarketplacePlugin(id);
      showToast("Plugin updated successfully", "success");
      await loadDetail();
    } catch (e) {
      showToast(`Update failed: ${e}`, "error");
    } finally {
      setInstalling(false);
    }
  };

  const handleRemove = async () => {
    if (!id) return;
    setInstalling(true);
    try {
      await api.removeMarketplacePlugin(id);
      showToast("Plugin removed", "success");
      navigate("/marketplace");
    } catch (e) {
      showToast(`Remove failed: ${e}`, "error");
    } finally {
      setInstalling(false);
    }
  };

  const handleRollback = async (version: string) => {
    if (!id) return;
    try {
      await api.rollbackPlugin(id, version);
      showToast(`Rolled back to ${version}`, "success");
      await loadDetail();
    } catch (e) {
      showToast(`Rollback failed: ${e}`, "error");
    }
  };

  const handleToggleEnabled = async () => {
    if (!id) return;
    const next = !enabled;
    try {
      await api.setPluginEnabled(id, next);
      setEnabled(next);
      showToast(next ? "Plugin enabled" : "Plugin disabled", "success");
    } catch (e) {
      showToast(`Failed: ${e}`, "error");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Plugin not found
        </CardContent>
      </Card>
    );
  }

  const { entry, reviews, versions, rating_distribution } = data;
  const screenshots = entry.screenshots ?? [];
  const entryUrl = `/marketplace/${encodeURIComponent(entry.id)}`;

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Header */}
      <div className={cn(
        "relative border border-border/40 bg-card/60 backdrop-blur-sm p-6",
      )}>
        <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent pointer-events-none" />
        <div className="relative flex flex-col sm:flex-row gap-6">
          <div className="h-16 w-16 rounded-xl bg-gradient-to-br from-primary/30 to-primary/10 flex items-center justify-center text-2xl shrink-0 border border-border/30">
            {entry.icon || <Package className="h-8 w-8" />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="font-semibold text-lg">{entry.name}</h1>
                  {entry.official && <Award className="h-4 w-4 text-amber-400" />}
                  {entry.verified && <Shield className="h-4 w-4 text-emerald-400" />}
                  <Badge tone="outline">v{entry.version}</Badge>
                  {entry.license && <Badge tone="secondary">{entry.license}</Badge>}
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {entry.author}
                  </span>
                  <span className="flex items-center gap-1">
                    <Star className="h-3 w-3 text-amber-400" />
                    {entry.rating.toFixed(1)} ({entry.review_count} reviews)
                  </span>
                  <span className="flex items-center gap-1">
                    <Download className="h-3 w-3" />
                    {entry.downloads.toLocaleString()} downloads
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    Updated {isoTimeAgo(entry.updated_at)}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {entry.installed ? (
                  <>
                    <div className="flex items-center gap-2">
                      <Switch checked={enabled} onCheckedChange={handleToggleEnabled} />
                      <span className="text-xs">{enabled ? "Enabled" : "Disabled"}</span>
                    </div>
                    {entry.has_update && (
                      <Button
                        className="uppercase"
                        size="sm"
                        disabled={installing}
                        onClick={handleUpdate}
                        prefix={installing ? <Spinner /> : <DownloadCloud />}
                      >
                        Update
                      </Button>
                    )}
                    <Button
                      destructive
                      ghost
                      size="sm"
                      disabled={installing}
                      onClick={handleRemove}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </>
                ) : (
                  <Button
                    className="uppercase"
                    size="sm"
                    disabled={installing}
                    onClick={handleInstall}
                    prefix={installing ? <Spinner /> : <Download />}
                  >
                    {installing ? "Installing..." : "Install"}
                  </Button>
                )}
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-3">{entry.description}</p>
            <div className="flex items-center gap-2 mt-3 flex-wrap">
              {entry.tags.map((tag) => (
                <Badge key={tag} tone="outline" className="text-[10px]">{tag}</Badge>
              ))}
              <Badge tone="secondary" className="text-[10px]">{entry.category}</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Links */}
      <div className="flex items-center gap-3">
        {entry.homepage && (
          <a href={entry.homepage} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <Globe className="h-3.5 w-3.5" /> Homepage <ExternalLink className="h-3 w-3" />
          </a>
        )}
        {entry.repository && (
          <a href={entry.repository} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <GitBranch className="h-3.5 w-3.5" /> Repository <ExternalLink className="h-3 w-3" />
          </a>
        )}
        {entry.documentation && (
          <a href={entry.documentation} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
            <Book className="h-3.5 w-3.5" /> Documentation <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>

      {/* Screenshots carousel */}
      {screenshots.length > 0 && (
        <div className="relative rounded border border-border/30 overflow-hidden">
          <div className="aspect-video bg-muted/20 flex items-center justify-center">
            {screenshots[screenshotIdx] ? (
              <img
                src={screenshots[screenshotIdx]}
                alt={`Screenshot ${screenshotIdx + 1}`}
                className="w-full h-full object-cover"
              />
            ) : (
              <Monitor className="h-12 w-12 text-muted-foreground/30" />
            )}
          </div>
          {screenshots.length > 1 && (
            <>
              <Button
                ghost
                size="icon"
                className="absolute left-2 top-1/2 -translate-y-1/2 bg-background/60 backdrop-blur-sm"
                onClick={() => setScreenshotIdx((i) => Math.max(0, i - 1))}
                disabled={screenshotIdx === 0}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                ghost
                size="icon"
                className="absolute right-2 top-1/2 -translate-y-1/2 bg-background/60 backdrop-blur-sm"
                onClick={() => setScreenshotIdx((i) => Math.min(screenshots.length - 1, i + 1))}
                disabled={screenshotIdx >= screenshots.length - 1}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5">
                {screenshots.map((_, i) => (
                  <button
                    key={i}
                    className={cn(
                      "h-1.5 rounded-full transition-all",
                      i === screenshotIdx ? "w-4 bg-foreground/60" : "w-1.5 bg-foreground/20",
                    )}
                    onClick={() => setScreenshotIdx(i)}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-border/30 overflow-x-auto">
        {([
          { id: "readme" as Tab, label: "Readme", icon: Book },
          { id: "versions" as Tab, label: "Versions", icon: GitBranch },
          { id: "reviews" as Tab, label: "Reviews", icon: MessageSquare },
          { id: "dependencies" as Tab, label: "Dependencies", icon: Layers },
          { id: "permissions" as Tab, label: "Permissions", icon: Lock },
          { id: "screenshots" as Tab, label: "Screenshots", icon: Monitor },
        ]).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-3 text-xs font-medium border-b-2 transition-colors whitespace-nowrap",
              activeTab === tab.id
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <tab.icon className="h-3.5 w-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="min-h-[300px]">
        {activeTab === "readme" && (
          <Card>
            <CardContent className="p-6">
              {entry.readme ? (
                <div className="prose prose-sm max-w-none text-muted-foreground">
                  {entry.readme.split("\n").map((line, i) => (
                    <p key={i} className="text-sm leading-relaxed">{line || "\u00A0"}</p>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground/60">No readme available.</p>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "versions" && (
          <div className="flex flex-col gap-2">
            {versions.length === 0 && (
              <Card>
                <CardContent className="py-6 text-center text-sm text-muted-foreground">
                  No version history available.
                </CardContent>
              </Card>
            )}
            {versions.map((v, i) => (
              <Card key={v.version}>
                <CardContent className="flex items-start gap-4 py-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">v{v.version}</span>
                      {i === 0 && <Badge tone="success">Current</Badge>}
                      <span className="text-xs text-muted-foreground">
                        {isoTimeAgo(v.published_at)}
                      </span>
                      {v.size && (
                        <span className="text-xs text-muted-foreground">
                          {(v.size / 1024).toFixed(1)} KB
                        </span>
                      )}
                    </div>
                    {v.changelog && (
                      <p className="text-xs text-muted-foreground whitespace-pre-wrap">
                        {v.changelog}
                      </p>
                    )}
                  </div>
                  {entry.installed && i > 0 && (
                    <Button
                      ghost
                      size="sm"
                      onClick={() => handleRollback(v.version)}
                    >
                      <Undo className="h-3.5 w-3.5 mr-1" />
                      Rollback
                    </Button>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {activeTab === "reviews" && (
          <div className="flex flex-col gap-3">
            {/* Rating summary */}
            <Card>
              <CardContent className="p-4 flex items-center gap-6">
                <div className="text-center">
                  <div className="text-3xl font-bold">{entry.rating.toFixed(1)}</div>
                  <div className="flex items-center gap-0.5 mt-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <Star
                        key={star}
                        className={cn(
                          "h-3 w-3",
                          star <= Math.round(entry.rating) ? "text-amber-400 fill-amber-400" : "text-muted-foreground/30",
                        )}
                      />
                    ))}
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">{entry.review_count} reviews</div>
                </div>
                <div className="flex-1 flex flex-col gap-1">
                  {[5, 4, 3, 2, 1].map((star) => {
                    const count = rating_distribution[star] ?? 0;
                    const max = Math.max(...Object.values(rating_distribution), 1);
                    const pct = (count / max) * 100;
                    return (
                      <div key={star} className="flex items-center gap-2 text-xs">
                        <span className="w-3 text-muted-foreground">{star}</span>
                        <Star className="h-2.5 w-2.5 text-amber-400" />
                        <div className="flex-1 h-1.5 bg-muted/30 rounded-full overflow-hidden">
                          <div className="h-full bg-amber-400/60 rounded-full" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="w-6 text-right text-muted-foreground">{count}</span>
                      </div>
                    );
                  })}
                </div>
              </CardContent>
            </Card>

            {reviews.length === 0 && (
              <Card>
                <CardContent className="py-6 text-center text-sm text-muted-foreground">
                  No reviews yet.
                </CardContent>
              </Card>
            )}
            {reviews.map((review) => (
              <Card key={review.id}>
                <CardContent className="py-3 px-4">
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium">{review.user}</span>
                      <div className="flex items-center gap-0.5">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star
                            key={star}
                            className={cn(
                              "h-2.5 w-2.5",
                              star <= review.rating ? "text-amber-400 fill-amber-400" : "text-muted-foreground/30",
                            )}
                          />
                        ))}
                      </div>
                    </div>
                    <span className="text-[11px] text-muted-foreground">{isoTimeAgo(review.created_at)}</span>
                  </div>
                  {review.title && <p className="text-xs font-medium mb-0.5">{review.title}</p>}
                  <p className="text-xs text-muted-foreground">{review.content}</p>
                  {review.helpful_count > 0 && (
                    <p className="text-[11px] text-muted-foreground/60 mt-1">
                      {review.helpful_count} found helpful
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {activeTab === "dependencies" && (
          <Card>
            <CardContent className="p-6">
              {entry.dependencies && entry.dependencies.length > 0 ? (
                <div className="flex flex-col gap-2">
                  {entry.dependencies.map((dep, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm px-3 py-2 border border-border/20 rounded">
                      <Package className="h-3.5 w-3.5 text-muted-foreground" />
                      <span>{dep}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground/60">No dependencies.</p>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "permissions" && (
          <PermissionsDisplay permissions={entry.permissions} />
        )}

        {activeTab === "screenshots" && (
          <Card>
            <CardContent className="p-6">
              {screenshots.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {screenshots.map((url, i) => (
                    <div key={i} className="aspect-video bg-muted/20 rounded border border-border/20 overflow-hidden">
                      <img src={url} alt={`Screenshot ${i + 1}`} className="w-full h-full object-cover" />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground/60">No screenshots available.</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function PermissionsDisplay({ permissions }: { permissions?: PluginPermissions }) {
  if (!permissions || Object.keys(permissions).length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-sm text-muted-foreground/60">This plugin declares no special permissions.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {Object.entries(permissions).map(([key, value]) => {
        const Icon = PERMISSION_ICONS[key] ?? Lock;
        const label = PERMISSION_LABELS[key] ?? key;
        return (
          <Card key={key}>
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs font-medium">{label}</span>
              </div>
              {typeof value === "boolean" ? (
                <div className="flex items-center gap-1.5">
                  {value ? (
                    <>
                      <Check className="h-3 w-3 text-emerald-400" />
                      <span className="text-xs text-muted-foreground">Granted</span>
                    </>
                  ) : (
                    <>
                      <X className="h-3 w-3 text-muted-foreground/50" />
                      <span className="text-xs text-muted-foreground/50">Not requested</span>
                    </>
                  )}
                </div>
              ) : typeof value === "object" && value !== null ? (
                <div className="flex flex-col gap-1">
                  {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{k}</span>
                      <span>{Array.isArray(v) ? v.join(", ") : String(v)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-muted-foreground">{String(value)}</span>
              )}
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
