/** 汇编行的词法着色，转码页与学习页共用。 */

import { isPseudo, REG_ALIASES } from '../core/isa.js';
import { escapeHtml } from './bits.js';

const REG_SET = new Set([
  ...Object.keys(REG_ALIASES),
  ...Array.from({ length: 32 }, (_, i) => `x${i}`),
]);

const TOKEN_RE = /(\s+)|(0x[0-9a-fA-F]+|0b[01]+|-?\d+)|([A-Za-z_.$][A-Za-z0-9_.$]*)|([(),])|(.)/g;

/**
 * 把一行汇编渲染成带着色 span 的 HTML。
 * @param {string} raw
 * @returns {string}
 */
export function highlightAsmLine(raw) {
  if (!raw) return '';

  let body = raw;
  let comment = '';
  let cut = -1;
  for (const marker of ['#', '//']) {
    const i = raw.indexOf(marker);
    if (i !== -1 && (cut === -1 || i < cut)) cut = i;
  }
  if (cut !== -1) {
    body = raw.slice(0, cut);
    comment = raw.slice(cut);
  }

  let out = '';
  const lm = /^(\s*)([A-Za-z_.$][A-Za-z0-9_.$]*)(\s*:)/.exec(body);
  if (lm) {
    out += `${escapeHtml(lm[1])}<span class="t-label">${escapeHtml(lm[2])}</span>${escapeHtml(lm[3])}`;
    body = body.slice(lm[0].length);
  }

  let firstWord = true;
  for (const m of body.matchAll(TOKEN_RE)) {
    if (m[1]) {
      out += escapeHtml(m[1]);
      continue;
    }
    if (m[2]) {
      out += `<span class="t-imm">${escapeHtml(m[2])}</span>`;
      continue;
    }
    if (m[3]) {
      const word = m[3];
      if (firstWord) {
        out += `<span class="${isPseudo(word) ? 't-pseudo' : 't-mn'}">${escapeHtml(word)}</span>`;
        firstWord = false;
      } else if (REG_SET.has(word.toLowerCase())) {
        out += `<span class="t-reg">${escapeHtml(word)}</span>`;
      } else {
        out += `<span class="t-label">${escapeHtml(word)}</span>`;
      }
      continue;
    }
    if (m[4]) {
      out += `<span class="t-punct">${escapeHtml(m[4])}</span>`;
      continue;
    }
    out += escapeHtml(m[5]);
  }

  if (comment) out += `<span class="t-com">${escapeHtml(comment)}</span>`;
  return out;
}
