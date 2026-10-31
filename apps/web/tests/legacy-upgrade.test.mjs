import test from "node:test";
import assert from "node:assert/strict";
import { ensureArchitecture } from "../app/lib/legacy-upgrade.ts";

const original = {
  project_id: "saved-villa",
  revision_id: "original-revision",
  revision_number: 1,
  schema_version: "0.1.0",
  architecture: null,
};
const upgraded = {
  ...original,
  revision_id: "restored-revision",
  revision_number: 2,
  schema_version: "0.2.0",
  architecture: { revision_id: "restored-revision" },
};

test("modern buildings open without any migration request", async () => {
  const result = await ensureArchitecture(upgraded, () => {
    assert.fail("A current building must not be rewritten on open");
  });
  assert.equal(result.snapshot, upgraded);
  assert.equal(result.upgraded, false);
});

test("opening an old villa uses a replayable typed command and loads its committed revision", async () => {
  const requests = [];
  const request = async (path, options) => {
    requests.push({ path, options });
    return options ? { revision_id: upgraded.revision_id } : upgraded;
  };
  const before = structuredClone(original);
  const result = await ensureArchitecture(original, request);
  await ensureArchitecture(original, request);
  assert.deepEqual(requests[0], requests[2], "Retries must use identical receipts and payloads");
  assert.equal(requests[0].path, "/api/v1/projects/saved-villa/commands");
  assert.equal(requests[0].options.headers["If-Match"], '"original-revision"');
  assert.deepEqual(JSON.parse(requests[0].options.body), {
    base_revision_id: original.revision_id,
    commands: [{ type: "upgrade_architecture", command_id: original.revision_id }],
  });
  assert.equal(requests[1].path, "/api/v1/projects/saved-villa/revisions/restored-revision");
  assert.equal(result.snapshot, upgraded);
  assert.equal(result.upgraded, true);
  assert.deepEqual(original, before);
});

for (const status of [409, 412]) {
  test(`a competing tab's ${status} loads its newer head without another mutation`, async () => {
    const requests = [];
    const winner = { ...upgraded, revision_id: "concurrent-edit", revision_number: 3 };
    const result = await ensureArchitecture(original, async (path, options) => {
      requests.push({ path, options });
      if (options) throw Object.assign(new Error("Concurrent upgrade"), { status });
      return path.endsWith("/concurrent-edit") ? winner : { revision_id: winner.revision_id };
    });
    assert.equal(result.snapshot, winner);
    assert.equal(result.upgraded, true);
    assert.equal(requests.filter((r) => r.options).length, 1);
  });
}

test("unsupported saved geometry remains readable with its actual error and no seed replacement", async () => {
  const error = Object.assign(new Error("Custom service layout needs review"), { status: 422 });
  let count = 0;
  const result = await ensureArchitecture(original, async () => {
    count += 1;
    throw error;
  });
  assert.equal(count, 1);
  assert.equal(result.snapshot, original);
  assert.equal(result.error, error);
  assert.equal(result.upgraded, false);
});
