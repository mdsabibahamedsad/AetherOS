import { useMemo } from "react";
import { CheckCircle2, XCircle, Clock, Play, Pause, AlertTriangle, ArrowDown } from "lucide-react";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { cn } from "@/lib/utils";

interface GraphNode {
  id: string;
  task_id: string;
  node_type: string;
  label: string;
  status: string;
  level: number;
  metadata?: Record<string, unknown>;
}

interface GraphEdge {
  source: string;
  target: string;
  edge_type: string;
  condition: string;
  label: string;
}

interface ExecutionGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
  levels: string[][];
}

const STATUS_ICONS: Record<string, any> = {
  completed: CheckCircle2,
  running: Play,
  failed: XCircle,
  cancelled: XCircle,
  pending: Clock,
  paused: Pause,
  blocked: AlertTriangle,
};

const STATUS_COLORS: Record<string, string> = {
  completed: "border-green-500 bg-green-50 dark:bg-green-950/20",
  running: "border-blue-500 bg-blue-50 dark:bg-blue-950/20",
  failed: "border-red-500 bg-red-50 dark:bg-red-950/20",
  cancelled: "border-gray-500 bg-gray-50 dark:bg-gray-950/20",
  pending: "border-gray-300 bg-gray-50 dark:bg-gray-950/10",
  paused: "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
  blocked: "border-orange-500 bg-orange-50 dark:bg-orange-950/20",
};

export function TaskGraphView({ graph }: { graph: ExecutionGraph }) {
  const nodeMap = useMemo(() => {
    const map: Record<string, GraphNode> = {};
    for (const n of graph.nodes) map[n.id] = n;
    return map;
  }, [graph]);

  const edgesBySource = useMemo(() => {
    const map: Record<string, GraphEdge[]> = {};
    for (const e of graph.edges) {
      if (!map[e.source]) map[e.source] = [];
      map[e.source].push(e);
    }
    return map;
  }, [graph]);

  if (!graph.nodes.length) {
    return <div className="text-sm text-muted-foreground py-8 text-center">No graph data available</div>;
  }

  return (
    <div className="space-y-6 overflow-x-auto">
      {graph.levels.map((level, levelIdx) => (
        <div key={levelIdx}>
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline" className="text-xs">Level {levelIdx + 1}</Badge>
            {level.length > 1 && (
              <span className="text-xs text-muted-foreground">({level.length} parallel tasks)</span>
            )}
          </div>
          <div className="flex gap-3 flex-wrap">
            {level.map(nodeId => {
              const node = nodeMap[nodeId];
              if (!node) return null;
              const Icon = STATUS_ICONS[node.status] || Clock;
              const colorClass = STATUS_COLORS[node.status] || STATUS_COLORS.pending;
              const outgoing = edgesBySource[node.id] || [];

              return (
                <div key={node.id} className="flex flex-col items-center">
                  <div className={cn(
                    "border-2 rounded-lg p-3 min-w-[140px] text-center",
                    colorClass,
                  )}>
                    <div className="flex items-center justify-center gap-1 mb-1">
                      <Icon className="h-3.5 w-3.5" />
                      <span className="text-[10px] font-medium uppercase text-muted-foreground">
                        {node.node_type}
                      </span>
                    </div>
                    <p className="text-xs font-medium truncate max-w-[120px]">{node.label}</p>
                    {node.metadata?.role && (
                      <p className="text-[10px] text-muted-foreground mt-0.5">
                        {node.metadata.role as string}
                      </p>
                    )}
                    <div className="mt-1">
                      <Badge
                        variant={node.status === "completed" ? "success" : node.status === "running" ? "warning" : "outline"}
                        className="text-[9px] px-1 py-0"
                      >
                        {node.status}
                      </Badge>
                    </div>
                  </div>
                  {outgoing.length > 0 && (
                    <div className="flex flex-col items-center mt-1">
                      <ArrowDown className="h-3 w-3 text-muted-foreground" />
                      <div className="flex gap-1 mt-0.5">
                        {outgoing.map((edge, ei) => (
                          <Badge key={ei} variant="outline" className="text-[8px] px-1 py-0">
                            {edge.condition || "dep"}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
