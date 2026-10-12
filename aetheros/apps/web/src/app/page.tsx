export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="flex flex-col items-center gap-6 text-center">
        <h1 className="text-5xl font-bold tracking-tight">
          <span className="text-primary">Aether</span>OS
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">
          Orchestrate, monitor, and manage your AI workforce.
        </p>
        <div className="mt-4 flex gap-4">
          <a
            href="/dashboard"
            className="rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            Dashboard
          </a>
          <a
            href="/api/health"
            className="rounded-md border border-border px-6 py-2.5 text-sm font-medium transition-colors hover:bg-accent"
          >
            Health Check
          </a>
        </div>
        <StatusBadge />
      </div>
    </main>
  );
}

async function StatusBadge() {
  let healthy = false;
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/health`,
      { signal: AbortSignal.timeout(3000) },
    );
    healthy = res.ok;
  } catch {
    healthy = false;
  }

  return (
    <div className="mt-8 flex items-center gap-2 text-sm text-muted-foreground">
      <span
        className={`inline-block h-2 w-2 rounded-full ${healthy ? "bg-green-500" : "bg-destructive"}`}
      />
      API {healthy ? "connected" : "unreachable"}
    </div>
  );
}
