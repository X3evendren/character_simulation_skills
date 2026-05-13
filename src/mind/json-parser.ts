/**
 * JSON/XML Parser — Extract structured data from LLM raw output.
 */
export function extractJSON(rawOutput: string): Record<string, unknown> {
  let text = rawOutput.trim();
  text = text.replace(/^﻿|​|‌|‍|⁠/g, "");

  const fenceMatch = text.match(/`{3,}\s*(?:json)?\s*\n(.*?)\n\s*`{3,}/s);
  if (fenceMatch) {
    text = fenceMatch[1].trim();
  } else {
    const start = text.indexOf("{");
    const end = text.lastIndexOf("}");
    if (start >= 0 && end > start) {
      text = text.slice(start, end + 1);
    }
  }

  text = text.replace(/,(\s*[}\]])/g, "$1");

  try { return JSON.parse(text); } catch { /* continue */ }

  // Try single-quote JSON
  try { return JSON.parse(text.replace(/'/g, '"')); } catch { /* continue */ }

  // Try to fix truncated JSON
  const openBraces = (text.match(/\{/g) ?? []).length - (text.match(/\}/g) ?? []).length;
  const openBrackets = (text.match(/\[/g) ?? []).length - (text.match(/\]/g) ?? []).length;

  if (openBraces > 0 || openBrackets > 0) {
    let fixed = text.replace(/,(\s*)$/g, "$1");
    const closer = "]".repeat(Math.max(0, openBrackets)) + "}".repeat(Math.max(0, openBraces));
    const quoteCount = (fixed.match(/"/g) ?? []).length;

    if (quoteCount % 2 !== 0) {
      try { return JSON.parse(fixed + '": null' + closer); } catch { /* continue */ }
    }

    const lastColon = fixed.lastIndexOf(":");
    if (lastColon > 0) {
      const beforeColon = fixed.slice(0, lastColon).trimEnd();
      if (beforeColon.endsWith('"')) {
        try { return JSON.parse(beforeColon + ': null' + closer); } catch { /* continue */ }
      }
    }

    try { return JSON.parse(fixed + closer); } catch { /* continue */ }
  }

  return {};
}

export function extractXML(rawOutput: string, tag: string): string | null {
  const pattern = new RegExp(`<${tag}>(.*?)</${tag}>`, "s");
  const match = rawOutput.match(pattern);
  return match ? match[1].trim() : null;
}

export function extractXMLAttr(rawOutput: string, tag: string, attr: string): string | null {
  const pattern = new RegExp(`<${tag}\\s[^>]*${attr}="([^"]*)"`);
  const match = rawOutput.match(pattern);
  return match ? match[1] : null;
}
