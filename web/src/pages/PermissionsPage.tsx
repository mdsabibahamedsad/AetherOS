import { useEffect, useState } from "react";
import {
  Lock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  RefreshCw,
  Search,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@aetheros/ui/ui/components/card";
import { Button } from "@aetheros/ui/ui/components/button";
import { Badge } from "@aetheros/ui/ui/components/badge";
import { Spinner } from "@aetheros/ui/ui/components/spinner";
import { Input } from "@aetheros/ui/ui/components/input";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";

interface GrantEntry {
  permission: string;
  grantee: string;
  granted_at: number;
  expires_at: number;
  duration: string;
  reason: string;
}

interface PermissionCategory {
  category: string;
  actions: string[];
}

export default function PermissionsPage() {
  const [grants, setGrants] = useState<GrantEntry[]>([]);
  const [categories, setCategories] = useState<PermissionCategory[]>([]);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const { t } = useI18n();
  const { setEnd } = usePageHeader();

  useEffect(() => {
    setEnd(
      <div className="relative w-full min-w-0 sm:max-w-xs">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input
          className="h-8 pl-8 pr-7 text-xs"
          placeholder="Search permissions..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <Button ghost size="xs" className="absolute right-1.5 top-1/2 -translate-y-1/2" onClick={() => setSearchQuery("")}>
            <X className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
    return () => setEnd(null);
  }, [searchQuery, setEnd, t.common.clear, t.common.search]);

  useEffect(() => {
    Promise.all([
      api.getPermissions().catch(() => ({ grants: [] })),
      api.getPermissionCategories().catch(() => ({ categories: [] })),
      api.getPermissionStats().catch(() => null),
    ]).then(([g, c, s]) => {
      setGrants(g.grants ?? []);
      setCategories(c.categories ?? []);
      setStats(s);
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Spinner className="text-2xl text-primary" />
      </div>
    );
  }

  const durationLabel = (d: string) => {
    const labels: Record<string, string> = { once: "Single use", session: "Session", hour: "1 hour", day: "24 hours", week: "7 days", month: "30 days", permanent: "Permanent" };
    return labels[d] ?? d;
  };

  const isExpired = (expires_at: number) => expires_at > 0 && expires_at < Date.now() / 1000;

  const filteredGrants = grants.filter((g) => {
    if (searchQuery && !g.permission.toLowerCase().includes(searchQuery.toLowerCase()) && !g.grantee.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    if (selectedCategory && !g.permission.startsWith(selectedCategory)) return false;
    return true;
  });

  const activeGrants = filteredGrants.filter((g) => !isExpired(g.expires_at));
  const expiredGrants = filteredGrants.filter((g) => isExpired(g.expires_at));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <Lock className="h-5 w-5 text-midground" />
        <h1 className="text-lg font-bold">Permissions</h1>
        <Badge tone="secondary" className="text-xs">{stats?.total_grants ?? 0} grants</Badge>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Sidebar: categories */}
        <aside className="lg:col-span-1">
          <div className="border border-border bg-muted/20">
            <div className="px-3 py-2 border-b border-border">
              <span className="font-mondwest text-display text-xs tracking-[0.12em] text-text-secondary">Categories</span>
            </div>
            <div className="p-2 space-y-px max-h-[400px] overflow-y-auto">
              <button
                onClick={() => setSelectedCategory(null)}
                className={`w-full text-left px-2 py-1.5 text-xs transition-colors ${!selectedCategory ? "bg-midground/10 text-midground" : "text-text-secondary hover:text-midground"}`}
              >
                All ({grants.length})
              </button>
              {categories.map((cat) => {
                const count = grants.filter((g) => g.permission.startsWith(cat.category)).length;
                if (count === 0) return null;
                return (
                  <button
                    key={cat.category}
                    onClick={() => setSelectedCategory(cat.category)}
                    className={`w-full text-left px-2 py-1.5 text-xs transition-colors flex items-center justify-between ${selectedCategory === cat.category ? "bg-midground/10 text-midground" : "text-text-secondary hover:text-midground"}`}
                  >
                    <span className="capitalize">{cat.category}</span>
                    <span className="text-text-tertiary">{count}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </aside>

        {/* Main: grants list */}
        <div className="lg:col-span-3 space-y-4">
          {/* Active grants */}
          <Card>
            <CardHeader className="py-3 px-4">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-success" />
                  Active Permissions
                </CardTitle>
                <Badge tone="secondary" className="text-xs">{activeGrants.length}</Badge>
              </div>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {activeGrants.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No active permissions.</p>
              ) : (
                <div className="space-y-1">
                  {activeGrants.map((g) => (
                    <div key={`${g.permission}|${g.grantee}`} className="flex items-center gap-3 py-2 px-3 hover:bg-muted/30 border border-transparent hover:border-border transition-colors text-sm">
                      <Lock className="h-3.5 w-3.5 text-midground/60 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <code className="text-xs font-mono">{g.permission}</code>
                          <span className="text-xs text-muted-foreground">&rarr;</span>
                          <span className="text-xs font-medium truncate">{g.grantee}</span>
                        </div>
                        <div className="text-[10px] text-muted-foreground">
                          {durationLabel(g.duration)} &middot; {g.reason ? g.reason : "No reason"}
                        </div>
                      </div>
                      {g.duration === "permanent" ? (
                        <Badge tone="info" className="text-[10px]">Permanent</Badge>
                      ) : g.expires_at > 0 ? (
                        <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(g.expires_at * 1000).toLocaleDateString()}
                        </span>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Expired grants */}
          {expiredGrants.length > 0 && (
            <Card>
              <CardHeader className="py-3 px-4">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <XCircle className="h-4 w-4 text-muted-foreground" />
                    Expired
                  </CardTitle>
                  <Badge tone="secondary" className="text-xs">{expiredGrants.length}</Badge>
                </div>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="space-y-1">
                  {expiredGrants.map((g) => (
                    <div key={`${g.permission}|${g.grantee}`} className="flex items-center gap-3 py-2 px-3 text-sm text-muted-foreground/60">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                      <code className="text-xs font-mono">{g.permission}</code>
                      <span className="text-xs">&rarr;</span>
                      <span className="text-xs">{g.grantee}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Stats card */}
          {stats && (
            <Card>
              <CardHeader className="py-3 px-4">
                <CardTitle className="text-sm">Statistics</CardTitle>
              </CardHeader>
              <CardContent className="px-4 pb-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center">
                  <div>
                    <div className="text-lg font-bold">{stats.total_permissions as number}</div>
                    <div className="text-[10px] text-muted-foreground">Categories</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold">{stats.total_grants as number}</div>
                    <div className="text-[10px] text-muted-foreground">Total Grants</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold">{stats.rules as number}</div>
                    <div className="text-[10px] text-muted-foreground">Rules</div>
                  </div>
                  <div>
                    <div className="text-lg font-bold">{stats.pending_requests as number}</div>
                    <div className="text-[10px] text-muted-foreground">Pending</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
