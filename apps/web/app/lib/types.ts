import type { components } from "./contracts";

// FastAPI serializes all Pydantic defaults. OpenAPI models also describe input
// defaults as optional; require emitted keys without copying the Python schema.
// Nullability is preserved.
type Serialized<T> = T extends (infer U)[]
  ? Serialized<U>[]
  : T extends object
    ? { [K in keyof T]-?: Serialized<T[K]> }
    : T;
type Schema<K extends keyof components["schemas"]> = Serialized<
  components["schemas"][K]
>;
export type Point = number[];
export type Units = "imperial" | "metric";
export type Level = Schema<"Level">;
export type Space = Schema<"Space">;
export type Wall = Schema<"Wall">;
export type Opening = Schema<"Opening">;
export type Slab = Schema<"Slab">;
export type Stair = Schema<"Stair">;
export type SpaceMetric = Schema<"SpaceMetrics">;
export type Architecture = Schema<"Architecture">;
export type BuildingSnapshot = Schema<"ProjectSnapshot">;
export interface Issue {
  code: string;
  message: string;
  field?: string;
  element_id?: string;
}
export interface Method {
  id: string;
  discipline: string;
  purpose: string;
  method_state: string;
  source: string;
  exclusions: string;
}
export interface Result {
  method_id: string;
  revision_id: string;
  method_state: string;
  execution_status: string;
  check_outcome: string;
  freshness_status: string;
  quantities: Record<string, unknown> | null;
  issues: Issue[];
  [key: string]: unknown;
}
export interface ExportRecord {
  artifact_id: string;
  model_artifact_id: string;
  manifest_artifact_id: string;
  revision_id: string;
  revision_number: number;
  file_sha256: string;
  sheets: string[];
  document_presence: string;
  review_status: string;
}
export interface Revision {
  revision_id: string;
  revision_number: number;
  created_at: string;
  parent_revision_id: string | null;
}
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  revision?: number;
  status?: "blocked" | "error" | "completed";
}
export interface ConversationResponse {
  execution_status: string;
  explanation?: string;
  issue?: Issue;
  model?: string;
  committed_revision_id?: string;
  committed_revision_number?: number;
}
export interface Mutation {
  revision_id: string;
  revision_number: number;
  execution_status?: string;
  issue?: Issue;
  solver_status?: string;
}

export interface ProjectSummary {
  project_id: string;
  revision_id: string;
  revision_number: number;
  title: string;
  created_at: string;
  content_hash: string;
}
export interface BriefTurn {
  role: "user" | "assistant";
  text: string;
}
export interface DesignResponse {
  execution_status: string;
  explanation?: string;
  issue?: Issue;
  project_id?: string;
  committed_revision_id?: string;
  revision_number?: number;
  title?: string;
  assumptions?: unknown[];
}
