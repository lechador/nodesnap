import type { BuildingSnapshot, Mutation } from "./types";

type Request = <T>(path: string, options?: RequestInit) => Promise<T>;

// Called only when opening the current project, never when reading history.
// The server records the upgrade as a normal validated, immutable revision.
export async function ensureArchitecture(
  original: BuildingSnapshot,
  request: Request,
): Promise<{ snapshot: BuildingSnapshot; upgraded: boolean; error?: unknown }> {
  if (original.architecture || original.schema_version !== "0.1.0")
    return { snapshot: original, upgraded: false };
  const path = `/api/v1/projects/${original.project_id}`;
  try {
    const result = await request<Mutation>(`${path}/commands`, {
      method: "POST",
      headers: {
        "If-Match": `"${original.revision_id}"`,
        "Idempotency-Key": `upgrade-architecture:${original.revision_id}`,
      },
      body: JSON.stringify({
        base_revision_id: original.revision_id,
        commands: [
          { type: "upgrade_architecture", command_id: original.revision_id },
        ],
      }),
    });
    const snapshot = await request<BuildingSnapshot>(
      `${path}/revisions/${result.revision_id}`,
    );
    return { snapshot, upgraded: true };
  } catch (error) {
    const status = (error as { status?: number } | null)?.status;
    if (status === 409 || status === 412) {
      // A second tab can win the same upgrade. Use its committed head instead
      // of sending another command or replacing newer work.
      try {
        const head = await request<{ revision_id: string }>(path);
        const snapshot = await request<BuildingSnapshot>(
          `${path}/revisions/${head.revision_id}`,
        );
        if (snapshot.architecture) return { snapshot, upgraded: true };
      } catch {
        // Preserve the original error and readable original revision below.
      }
    }
    return { snapshot: original, upgraded: false, error };
  }
}
