import { DataState } from "@/components/data-state";
import type { RouteState } from "@/lib/data";

type Props = {
  state: RouteState<unknown>;
  missingEnvBody: string;
  errorTitle: string;
  emptyTitle: string;
  emptyBody: string;
  className?: string;
};

export function DataGate({
  state,
  missingEnvBody,
  errorTitle,
  emptyTitle,
  emptyBody,
  className,
}: Props) {
  if (state.status === "ready") {
    return null;
  }

  const content =
    state.status === "missing_env" ? (
      <DataState title="Supabase environment required" body={missingEnvBody} />
    ) : state.status === "error" ? (
      <DataState title={errorTitle} body={state.message} />
    ) : (
      <DataState title={emptyTitle} body={emptyBody} />
    );

  return className ? <div className={className}>{content}</div> : content;
}
