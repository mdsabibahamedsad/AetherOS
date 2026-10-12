import { useCallback, useEffect, useLayoutEffect, useMemo, useState } from "react";
import {
  Play,
  Square,
  PauseCircle,
  RotateCcw,
  Activity,
  Cpu,
  HardDrive,
  Clock,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Terminal,
  FileText,
  FolderOpen,
  BookOpen,
  Zap,
  Server,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  ExternalLink,
} from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Select, SelectOption } from "@nous-research/ui/ui/components/select";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Toast } from "@nous-research/ui/ui/components/toast";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { api } from "@/lib/api";
import type { RemoteInstance, RemoteAgentStatus, RemoteTask, RemoteLogEntry } from "@/lib/api";
import { cn, isoTimeAgo, themedBody } from "@/lib/utils";
import { usePageHeader } from "@/contexts/usePageHeader";

const AGENT_STATUS_CONFIG: Record<string, { color: string; icon: typeof Activity; label: string }> = {
  running: { color: "text-emerald-400", icon: Activity, label: "Running" },
  stopped: { color: "text-muted-foreground", icon: Square, label: "Stopped" },
  paused: { color: "text-amber-400", icon: PauseCircle, label: "Paused" },
  error: { color: "text-red-400", icon: AlertTriangle, label: "Error" },
};

const LOG_LEVELS = [
  { value: "", label: "All Levels" },
  { value: "debug", label: "Debug" },
  { value: "info", label: "Info" },
  { value: "warn", label: "Warn" },
  { value: "error", label: "Error" },
];

const WORKSPACE_LINKS = [
  { label: "Files", icon: FolderOpen, path: "/files" },
  { label: "Projects", icon: FileText, path: "/projects" },
  { label: "Knowledge", icon: BookOpen, path: "/knowledge" },
  { label: "Automations", icon: Zap, path: "/automations" },
];

export default function RemoteAgentDashboard() {
  const [instances, setInstances] = useState<RemoteInstance[]>([]);
  const [selectedInstance, setSelectedInstance] = useState<string | null>(null);
  const [agentStatus, setAgentStatus] = useState<RemoteAgentStatus | null>(null);
  const [tasks, setTasks] = useState<RemoteTask[]>([]);
  const [logs, setLogs] = useState<RemoteLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [logLevel, setLogLevel] = useState("");
  const [acting, setActing] = useState<string | null>(null);
  const { toast, showToast } = useToast();
  const { setEnd } = usePageHeader();

  const loadInstances = useCallback(async () => {
    try {
      const res = await api.listRemoteInstances();
      setInstances(res.instances);
      if (res.instances.length > 0 && !selectedInstance) {
        setSelectedInstance(res.instances[0].id);
      }
    } catch (e) {
      showToast(`Failed to load instances: ${e}`, "error");
    }
  }, [selectedInstance, showToast]);

  const loadAgentData = useCallback(async (instanceId: string) => {
    setLoading(true);
    try {
      const [statusRes, tasksRes, logsRes] = await Promise.all([
        api.getRemoteAgentStatus(instanceId).catch(() => null),
        api.getRemoteTasks(instanceId).catch(() => ({ tasks: [] })),
        api.getRemoteLogs(instanceId, { level: logLevel || undefined, lines: 100 }).catch(() => ({ logs: [] })),
      ]);
      setAgentStatus(statusRes);
      setTasks(tasksRes.tasks);
      setLogs(logsRes.logs);
    } catch (e) {
      showToast(`Failed to load agent data: ${e}`, "error");
    } finally {
      setLoading(false);
    }
  }, [logLevel, showToast]);

  useEffect(() => { void loadInstances(); }, [loadInstances]);
  useEffect(() => { if (selectedInstance) void loadAgentData(selectedInstance); }, [selectedInstance, loadAgentData]);

  useLayoutEffect(() => {
    setEnd(
      <div className="flex items-center gap-2">
        <Button ghost size="sm" onClick={() => { if (selectedInstance) void loadAgentData(selectedInstance); }}>
          <RefreshCw className="h-4 w-4 mr-1" />
          Refresh
        </Button>
      </div>,
    );
    return () => setEnd(null);
  }, [setEnd, selectedInstance, loadAgentData]);

  const handleAction = async (action: string) => {
    if (!selectedInstance) return;
    setActing(action);
    try {
      await api.remoteAgentAction(selectedInstance, action);
      showToast(`Agent ${action}`, "success");
      setTimeout(() => { if (selectedInstance) void loadAgentData(selectedInstance); }, 1000);
    } catch (e) {
      showToast(`Action failed: ${e}`, "error");
    } finally {
      setActing(null);
    }
  };

  const selectedInstanceData = instances.find((i) => i.id === selectedInstance);
  const statusCfg = agentStatus ? AGENT_STATUS_CONFIG[agentStatus.status] ?? AGENT_STATUS_CONFIG.stopped : AGENT_STATUS_CONFIG.stopped;
  const StatusIcon = statusCfg.icon;

  return (
    <div className="flex flex-col gap-6">
      <Toast toast={toast} />

      {/* Instance Selector */}
      <div className="flex items-center gap-3">
        <div className="flex-1 max-w-xs">
          <Select value={selectedInstance ?? ""} onValueChange={setSelectedInstance}>
            {instances.map((inst) => (
              <SelectOption key={inst.id} value={inst.id}>
                {inst.name} ({inst.status})
              </SelectOption>
            ))}
          </Select>
        </div>
        {selectedInstanceData && (
          <Badge tone={selectedInstanceData.status === "online" ? "success" : selectedInstanceData.status === "error" ? "destructive" : "warning"}>
            {selectedInstanceData.status}
          </Badge>
        )}
      </div>

      {loading && !agentStatus ? (
        <div className="flex items-center justify-center py-24">
          <Spinner className="text-2xl text-primary" />
        </div>
      ) : !agentStatus ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            {instances.length === 0 ? "No remote instances configured" : "Select an instance to view agent status"}
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Agent Status Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className={cn("h-9 w-9 rounded-lg flex items-center justify-center border border-border/20", statusCfg.color.replace("text-", "bg-").replace("400", "400/20"))}>
                    <StatusIcon className={cn("h-4 w-4", statusCfg.color, agentStatus.status === "running" && "animate-pulse")} />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Agent Status</p>
                    <p className={cn("text-sm font-medium", statusCfg.color)}>{statusCfg.label}</p>
                    {agentStatus.started_at && <p className="text-[10px] text-muted-foreground">Since {isoTimeAgo(agentStatus.started_at)}</p>}
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center border border-border/20">
                    <Cpu className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">CPU Usage</p>
                    <p className="text-sm font-medium">{agentStatus.cpu_percent.toFixed(1)}%</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-blue-400/10 flex items-center justify-center border border-border/20">
                    <HardDrive className="h-4 w-4 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Memory</p>
                    <p className="text-sm font-medium">{agentStatus.memory_used_mb.toFixed(0)} / {agentStatus.memory_total_mb.toFixed(0)} MB</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-4 px-5">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-lg bg-emerald-400/10 flex items-center justify-center border border-border/20">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Tasks Completed</p>
                    <p className="text-sm font-medium">{agentStatus.tasks_completed}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Controls */}
          <Card>
            <CardHeader>
              <CardTitle>Agent Controls</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center gap-2 flex-wrap">
                <Button size="sm" onClick={() => handleAction("start")} disabled={acting !== null || agentStatus.status === "running"}>
                  {acting === "start" ? <Spinner className="h-4 w-4 mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                  Start
                </Button>
                <Button size="sm" ghost onClick={() => handleAction("stop")} disabled={acting !== null || agentStatus.status === "stopped"}>
                  {acting === "stop" ? <Spinner className="h-4 w-4 mr-1" /> : <Square className="h-4 w-4 mr-1" />}
                  Stop
                </Button>
                <Button size="sm" ghost onClick={() => handleAction("pause")} disabled={acting !== null || agentStatus.status !== "running"}>
                  {acting === "pause" ? <Spinner className="h-4 w-4 mr-1" /> : <PauseCircle className="h-4 w-4 mr-1" />}
                  Pause
                </Button>
                <Button size="sm" ghost onClick={() => handleAction("resume")} disabled={acting !== null || agentStatus.status !== "paused"}>
                  {acting === "resume" ? <Spinner className="h-4 w-4 mr-1" /> : <Play className="h-4 w-4 mr-1" />}
                  Resume
                </Button>
                <Button size="sm" ghost onClick={() => handleAction("restart")} disabled={acting !== null}>
                  {acting === "restart" ? <Spinner className="h-4 w-4 mr-1" /> : <RotateCcw className="h-4 w-4 mr-1" />}
                  Restart
                </Button>
              </div>
              {agentStatus.error_message && (
                <p className="text-xs text-destructive mt-2">{agentStatus.error_message}</p>
              )}
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Task List */}
            <Card>
              <CardHeader>
                <CardTitle>Tasks</CardTitle>
              </CardHeader>
              <CardContent>
                {tasks.length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">No tasks</p>
                ) : (
                  <div className="flex flex-col gap-1 max-h-64 overflow-y-auto">
                    {tasks.map((task) => (
                      <div key={task.id} className="flex items-center gap-3 py-2 px-2 rounded text-xs border-b border-border/10 last:border-0">
                        <Badge tone={
                          task.status === "completed" ? "success" :
                          task.status === "running" ? "warning" :
                          task.status === "failed" ? "destructive" : "outline"
                        } className="shrink-0">
                          {task.status}
                        </Badge>
                        <span className="flex-1 truncate">{task.name}</span>
                        <div className="w-16 h-1.5 bg-border/30 rounded-full overflow-hidden shrink-0">
                          <div className="h-full bg-primary rounded-full" style={{ width: `${task.progress}%` }} />
                        </div>
                        <span className="text-muted-foreground w-8 text-right">{task.progress}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Memory Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Memory Usage Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                {Object.keys(agentStatus.memory_breakdown).length === 0 ? (
                  <p className="text-xs text-muted-foreground text-center py-4">No memory data</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {Object.entries(agentStatus.memory_breakdown).map(([key, value]) => (
                      <div key={key} className="flex items-center gap-3 text-xs">
                        <span className="w-24 capitalize text-muted-foreground">{key.replace(/_/g, " ")}</span>
                        <div className="flex-1 h-2 bg-border/30 rounded-full overflow-hidden">
                          <div className="h-full bg-primary/60 rounded-full" style={{ width: `${Math.min(100, value)}%` }} />
                        </div>
                        <span className="w-12 text-right font-mono text-muted-foreground">{value.toFixed(1)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Log Viewer */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Agent Logs</CardTitle>
                <div className="w-32">
                  <Select value={logLevel} onValueChange={setLogLevel}>
                    {LOG_LEVELS.map((l) => (
                      <SelectOption key={l.value} value={l.value}>{l.label}</SelectOption>
                    ))}
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {logs.length === 0 ? (
                <p className="text-xs text-muted-foreground text-center py-4">No log entries</p>
              ) : (
                <div className="max-h-80 overflow-y-auto font-mono text-[11px] bg-black/20 p-3 rounded border border-border/20">
                  {logs.map((log, i) => (
                    <div key={log.id ?? i} className={cn(
                      "py-0.5",
                      log.level === "error" && "text-red-400",
                      log.level === "warn" && "text-amber-400",
                      log.level === "info" && "text-muted-foreground",
                      log.level === "debug" && "text-muted-foreground/50",
                    )}>
                      <span className="text-muted-foreground/50">[{log.timestamp}]</span>{" "}
                      <span className="uppercase font-bold">[{log.level}]</span>{" "}
                      <span className="text-muted-foreground/30">[{log.source}]</span>{" "}
                      {log.message}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Remote Workspace Quick-Links */}
          <Card>
            <CardHeader>
              <CardTitle>Remote Workspace</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {WORKSPACE_LINKS.map((link) => {
                  const Icon = link.icon;
                  return (
                    <button
                      key={link.label}
                      className="flex items-center gap-3 p-3 rounded-lg border border-border/20 hover:border-border/50 transition-colors text-left"
                    >
                      <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center border border-border/20">
                        <Icon className="h-4 w-4 text-primary" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">{link.label}</p>
                      </div>
                      <ExternalLink className="h-3.5 w-3.5 text-muted-foreground" />
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
