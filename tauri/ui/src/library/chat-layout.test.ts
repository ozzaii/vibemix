/**
 * @vitest-environment node
 */

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync("src/library/library.css", "utf8");

function ruleFor(selector: string): string {
  const start = css.indexOf(selector);
  expect(start, `missing selector: ${selector}`).toBeGreaterThanOrEqual(0);
  const bodyStart = css.indexOf("{", start);
  const bodyEnd = css.indexOf("}", bodyStart);
  expect(bodyStart, `missing rule body start: ${selector}`).toBeGreaterThanOrEqual(0);
  expect(bodyEnd, `missing rule body end: ${selector}`).toBeGreaterThan(bodyStart);
  return css.slice(bodyStart + 1, bodyEnd);
}

describe("Viber chat layout CSS", () => {
  it("keeps the lit chat slab as the only vertical scroll container", () => {
    const frame = ruleFor(':is(body, .vmx-lib-app)[data-mode="chat"] .vmx-lib-frame');
    const centerPanel = ruleFor(':is(body, .vmx-lib-app)[data-mode="chat"] .vmx-lib-panel:nth-child(2)');
    const centerBody = ruleFor(
      ':is(body, .vmx-lib-app)[data-mode="chat"] .vmx-lib-panel:nth-child(2) .vmx-lib-panel-bd',
    );
    const thread = ruleFor(':is(body, .vmx-lib-app)[data-mode="chat"] .vmx-lib-chat-thread');

    expect(frame).toMatch(/overflow:\s*visible/);
    expect(centerPanel).toMatch(/overflow:\s*visible/);
    expect(centerBody).toMatch(/overflow:\s*visible/);
    expect(centerBody).toMatch(/padding:\s*0/);
    expect(thread).toMatch(/overflow-y:\s*auto/);
  });
});
