import assert from "node:assert/strict";
import test from "node:test";

import { DOWNLOAD_ROUTES, SBI_PORTAL_URL, isAllowedSbiUrl } from "../src/routes.js";

test("SBIポータルURLは許可されたHTTPS URLである", () => {
  assert.equal(isAllowedSbiUrl(SBI_PORTAL_URL), true);
});

test("許可されていないURLを開かない", () => {
  assert.equal(isAllowedSbiUrl("http://www.sbisec.co.jp/ETGate"), false);
  assert.equal(isAllowedSbiUrl("https://www.sbisec.co.jp.attacker.example/"), false);
  assert.equal(isAllowedSbiUrl("https://example.com/"), false);
  assert.equal(isAllowedSbiUrl("not a url"), false);
});

test("各ダウンロード案内には識別子・形式・手順がある", () => {
  assert.ok(DOWNLOAD_ROUTES.length > 0);
  for (const route of DOWNLOAD_ROUTES) {
    assert.match(route.id, /^[a-z-]+$/);
    assert.ok(["HTML", "CSV"].includes(route.file));
    assert.ok(route.steps.length >= 2);
  }
});
