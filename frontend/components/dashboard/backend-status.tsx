import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BackendStatus as BackendStatusData } from "@/types/health";

type BackendStatusProps = {
  status: BackendStatusData | null;
};

export function BackendStatus({ status }: BackendStatusProps) {
  return (
    <Card className="supporting-card h-full">
      <CardHeader className="section-card-header">
        <p className="metric-label">System health</p>
        <CardTitle className="text-lg">Analysis engine</CardTitle>
      </CardHeader>
      <CardContent className="flex items-center gap-4 p-6">
        <span
          aria-hidden="true"
          className={`h-3 w-3 rounded-full shadow-[0_0_18px_currentColor] ${
            status === null
              ? "bg-amber-400 text-amber-400"
              : status.available
                ? "bg-primary text-primary"
                : "bg-red-500 text-red-500"
          }`}
        />
        <div>
          <p className="text-sm font-bold">
            {status === null
              ? "Checking backend"
              : status.available
                ? "Backend Connected"
                : "Backend Disconnected"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {status === null
              ? "Waiting for FastAPI health response"
              : status.available
              ? status.health.service
              : "FastAPI health check could not be reached"}
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
