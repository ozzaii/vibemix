// SPDX-License-Identifier: Apache-2.0
// Plan 29-07 — vitest spec for the renderer-side stripper.

import { describe, it, expect } from 'vitest';
import {
  EVIDENCE_CITATION_RE,
  stripDrillFields,
  stripUncitedSentences,
} from '../stripper-roundtrip';

describe('stripUncitedSentences', () => {
  it('keeps cited sentence, drops uncited', () => {
    const out = stripUncitedSentences('Cited [ev:A@1]. Uncited.');
    expect(out.text).toBe('Cited [ev:A@1].');
    expect(out.strippedCount).toBe(1);
  });

  it('returns empty for empty input', () => {
    expect(stripUncitedSentences('')).toEqual({ text: '', strippedCount: 0 });
  });

  it('matches all 7 EBNF sources', () => {
    for (const src of ['ev', 'aud', 'midi', 'track', 'screen', 'mix', 'tend']) {
      const out = stripUncitedSentences(`Test [${src}:body@01:00].`);
      expect(out.strippedCount).toBe(0);
      expect(out.text).toBeTruthy();
    }
  });

  it('drops everything when no citations', () => {
    const out = stripUncitedSentences('First. Second. Third.');
    expect(out.text).toBe('');
    expect(out.strippedCount).toBe(3);
  });

  it('handles question and exclamation boundaries', () => {
    const out = stripUncitedSentences(
      'Cited one [ev:M@1]! Bad. Cited two [track:t1]?',
    );
    expect(out.strippedCount).toBe(1);
    expect(out.text).toContain('[ev:M@1]');
    expect(out.text).toContain('[track:t1]');
  });
});

describe('stripDrillFields', () => {
  it('cleans all 3 advice fields independently', () => {
    const drill = {
      situation: 'S',
      behavior: 'Cited [ev:M@1]. Uncited.',
      impact: 'Uncited only.',
      action_recommended: 'Cited [track:t1].',
      citation: '[ev:M@1]',
    };
    const { drill: cleaned, strippedTotal } = stripDrillFields(drill);
    expect(cleaned.behavior).toBe('Cited [ev:M@1].');
    // ``impact`` becomes empty after strip → fallback to original (still
    // shown to user; renderer flags via ErrorBanner per ws-client).
    expect(cleaned.impact).toBe('Uncited only.');
    expect(cleaned.action_recommended).toBe('Cited [track:t1].');
    expect(strippedTotal).toBe(2);
  });

  it('zero strip when all sentences cited', () => {
    const drill = {
      situation: 'S',
      behavior: 'B [ev:M@1].',
      impact: 'I [ev:P@2].',
      action_recommended: 'A [track:t1].',
      citation: '[ev:M@1]',
    };
    const { strippedTotal } = stripDrillFields(drill);
    expect(strippedTotal).toBe(0);
  });
});

describe('EVIDENCE_CITATION_RE', () => {
  it('rejects whitespace inside brackets', () => {
    expect(EVIDENCE_CITATION_RE.test('[ev: foo]')).toBe(false);
  });

  it('rejects empty brackets', () => {
    expect(EVIDENCE_CITATION_RE.test('[]')).toBe(false);
  });

  it('accepts multi-citation comma form', () => {
    expect(EVIDENCE_CITATION_RE.test('[ev:A@1,track:t1]')).toBe(true);
  });
});
