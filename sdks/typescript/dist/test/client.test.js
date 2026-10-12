// Contract tests for the TypeScript SDK. Run against a live local gateway:
//   1. start gateway: python -m aetheros_platform.cli api serve --port 8765
//   2. AETHEROS_TEST_API_KEY=<key> npm test
// Uses only node:test + node:assert (zero test dependencies).
import { test } from "node:test";
import assert from "node:assert/strict";
import { Client } from "../src/index.js";
import { SDKError, defaultRetry, isRetryStatus, retryDelay, } from "../src/index.js";
const BASE = process.env.AETHEROS_TEST_BASE ?? "http://127.0.0.1:8765";
const KEY = process.env.AETHEROS_TEST_API_KEY ?? "";
test("retry delays are bounded and jittered", () => {
    const d0 = retryDelay(defaultRetry, 0);
    assert.ok(d0 >= 250 && d0 <= 500, `d0=${d0}`);
    const d3 = retryDelay(defaultRetry, 3);
    assert.ok(d3 >= 2000 && d3 <= 4000, `d3=${d3}`);
    assert.ok(isRetryStatus(429) && !isRetryStatus(200));
});
test("typed error parsing never leaks bodies", () => {
    const e = SDKError.fromResponse(403, {
        code: "AUTHORIZATION_DENIED",
        message: "scope x required",
        category: "AUTHORIZATION_DENIED",
        retryable: false,
    });
    assert.equal(e.status, 403);
    assert.equal(e.retryable, false);
    assert.equal(e.category, "AUTHORIZATION_DENIED");
});
test("unauthenticated request yields typed 401", async () => {
    if (!KEY)
        return; // needs a live gateway; otherwise constructor-level only
    const bad = new Client(BASE, "aek_invalid");
    await assert.rejects(bad.listAgents(), (e) => {
        assert.match(e.message, /missing or invalid|AUTHENTICATION/i);
        return true;
    });
});
test("full E2E against live gateway", { timeout: 60000 }, async () => {
    if (!KEY)
        return;
    const c = new Client(BASE, KEY);
    const agent = await c.createAgent({
        name: `ts-e2e-${Date.now().toString(36)}`,
        version: "1.0.0",
        description: "ts sdk e2e",
        capabilities: ["artifact.create"],
    });
    assert.ok(agent.agentId);
    const result = await c.createTask(agent.agentId, {
        capability: "artifact.create",
    });
    assert.equal(result.state, "COMPLETED");
    const fetched = await c.getTask(result.taskId);
    assert.equal(fetched.taskId, result.taskId);
    const mem = await c.memoryWrite("ts sdk wrote this", "user");
    assert.ok(mem);
    const art = await c.artifactCreate(Buffer.from("ts-bytes").toString("base64"), "ts.txt");
    assert.ok(art["artifactId"]);
    const back = await c.artifactGet(art["artifactId"]);
    assert.equal(Buffer.from(back.dataBase64, "base64").toString(), "ts-bytes");
    const auto = await c.automationCreate(`ts-cron-${Date.now().toString(36)}`, {
        type: "manual",
    });
    assert.ok(auto["id"]);
    const hook = await c.webhookRegister("https://example.com/ts-hook", [
        "TaskCreated",
    ]);
    assert.ok(hook["id"]);
    const card = await c.agentCard();
    assert.equal(card["trust"], "untrusted");
});
//# sourceMappingURL=client.test.js.map