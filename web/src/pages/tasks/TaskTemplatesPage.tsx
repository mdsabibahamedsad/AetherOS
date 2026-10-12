import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, Bot, Play, Star, Plus, Search } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@nous-research/ui/ui/components/card";
import { Badge } from "@nous-research/ui/ui/components/badge";
import { Button } from "@nous-research/ui/ui/components/button";
import { Spinner } from "@nous-research/ui/ui/components/spinner";
import { Input } from "@nous-research/ui/ui/components/input";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription,
} from "@nous-research/ui/ui/components/dialog";
import { useToast } from "@nous-research/ui/hooks/use-toast";
import { useI18n } from "@/i18n";
import { usePageHeader } from "@/contexts/usePageHeader";
import { useTaskStore } from "@/store/task-store";

const CATEGORY_LABELS: Record<string, string> = {
  research_report: "Research Reports",
  software_development: "Software Development",
  data_analysis: "Data Analysis",
  content_creation: "Content Creation",
  email_campaign: "Email Campaigns",
  business_automation: "Business Automation",
  personal_assistant: "Personal Assistant",
  custom: "Custom",
};

function formatDuration(seconds: number): string {
  if (!seconds) return "\u2014";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function TaskTemplatesPage() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { setTitle, setDescription } = usePageHeader();
  const { showToast } = useToast();
  const { templates, loading, fetchTemplates, submitTemplate } = useTaskStore();

  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [executing, setExecuting] = useState<string | null>(null);

  useEffect(() => {
    setTitle("Task Templates");
    setDescription("Reusable workflow templates");
    fetchTemplates();
  }, []);

  const categories = Array.from(new Set(templates.map(t => t.category)));
  const filtered = templates.filter(t => {
    if (categoryFilter !== "all" && t.category !== categoryFilter) return false;
    if (search && !t.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const handleExecute = useCallback(async (templateId: string) => {
    setExecuting(templateId);
    try {
      const plan = await submitTemplate(templateId);
      if (plan) {
        showToast({ title: "Template executing", description: `Plan ${plan.id} created from template` });
        navigate(`/tasks/${plan.id}`);
      }
    } finally {
      setExecuting(null);
    }
  }, [submitTemplate, showToast, navigate]);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Task Templates</h1>
          <p className="text-muted-foreground">Reusable workflows for common tasks</p>
        </div>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Search templates..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <select
          className="border rounded px-2 py-1 text-sm"
          value={categoryFilter}
          onChange={e => setCategoryFilter(e.target.value)}
        >
          <option value="all">All Categories</option>
          {categories.map(c => (
            <option key={c} value={c}>{CATEGORY_LABELS[c] || c}</option>
          ))}
        </select>
      </div>

      {loading && <Spinner />}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map(tpl => (
          <Card key={tpl.id}>
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between">
                <CardTitle className="text-sm">{tpl.name}</CardTitle>
                {tpl.is_builtin && <Star className="h-3 w-3 text-yellow-500" />}
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{tpl.description}</p>
              <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                <span className="flex items-center gap-1"><Clock className="h-3 w-3" /> {formatDuration(tpl.estimated_duration)}</span>
                <Badge variant="outline" className="text-xs">
                  {CATEGORY_LABELS[tpl.category] || tpl.category}
                </Badge>
              </div>
              <div className="flex gap-1 mt-2">
                {tpl.tags.slice(0, 3).map(tag => (
                  <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                ))}
              </div>
              <div className="mt-3">
                <Button
                  size="sm"
                  className="w-full"
                  onClick={() => handleExecute(tpl.id)}
                  disabled={executing === tpl.id}
                >
                  {executing === tpl.id ? (
                    <Spinner className="mr-1 h-3 w-3" />
                  ) : (
                    <Play className="mr-1 h-3 w-3" />
                  )}
                  Execute
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
