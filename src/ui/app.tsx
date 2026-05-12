/** Ink App — Span-based layout with Controller integration. */
import React, { useState, useEffect, useRef } from "react";
import { Box, Text, useInput, useApp, useStdout } from "ink";
import { CharacterAgent } from "../character/index";
import { OpenAICompatProvider } from "../character/integration/provider";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { registerBuiltinCommands, router, isCommandInput } from "../commands/index";
import { HistoryStore } from "../history";
import { SpanState } from "./span-renderer";
import { GenerationController } from "../generation/controller";
import { InflightSummarizer } from "../generation/inflight-summarizer";
import { SpanBasedGenerator } from "../character/integration/dual-track";
import type { Span, SpanOp, ToolResult } from "../generation/types";

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_DIR = resolve(__dirname, "../../config");
const API_KEY = process.env.DEEPSEEK_API_KEY || "";
const API_BASE = process.env.DEEPSEEK_API_BASE || "https://api.deepseek.com";

export function App() {
  const { exit } = useApp();
  const { stdout } = useStdout();
  const [agent, setAgent] = useState<CharacterAgent | null>(null);
  const [agentName, setAgentName] = useState("林雨");
  const [input, setInput] = useState("");
  const [cursor, setCursor] = useState(0);
  const [status, setStatus] = useState("init...");
  const [genStatus, setGenStatus] = useState("idle");
  const history = useRef(new HistoryStore()).current;
  const savedInput = useRef("");
  const initRef = useRef(false);

  // Span-based rendering
  const spanState = useRef(new SpanState()).current;
  const controllerRef = useRef<GenerationController | null>(null);
  const [, forceRender] = useState(0);

  // Subscribe SpanState to React re-renders
  useEffect(() => {
    return spanState.subscribe(() => forceRender(n => n + 1));
  }, []);

  const rows = stdout?.rows ?? 24;
  const maxMsg = Math.max(3, rows - 3);

  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;
    (async () => {
      try {
        const gen = new OpenAICompatProvider("deepseek-v4-pro", API_KEY, API_BASE);
        const psych = new OpenAICompatProvider("deepseek-v4-flash", API_KEY, API_BASE);
        const a = new CharacterAgent({
          configDir: CONFIG_DIR, genProvider: gen, psychProvider: psych,
          genModel: "deepseek-v4-pro", psychModel: "deepseek-v4-flash",
        });
        await a.initialize();
        registerBuiltinCommands();
        setAgent(a);
        setAgentName(a.config.name);

        // Build controller
        const inflightSummarizer = new InflightSummarizer(psych);
        const spanGenerator = new SpanBasedGenerator(gen, gen, a.toolRegistry);

        const controllerAdapter = createControllerAdapter(a, spanState);
        const controller = new GenerationController(spanState, inflightSummarizer, controllerAdapter);
        controller.setGenerator(spanGenerator);
        controllerRef.current = controller;

        setStatus("");
        setGenStatus("idle");
      } catch (e: any) { setStatus(`Error: ${e.message}`); }
    })();
  }, []);

  // ═══════════════════════════════════════
  // Submit handler
  // ═══════════════════════════════════════
  const submitText = async (text: string) => {
    if (!agent) return;

    if (text === "/quit") { agent.shutdown().then(() => exit()); return; }
    if (text === "/stats") {
      const s = agent.params.snapshot();
      const top = Object.entries(s as Record<string, number>)
        .filter(([, v]) => Math.abs(v) > 0.1).slice(0, 6)
        .map(([k, v]) => `${k}:${v > 0 ? "+" : ""}${v}`).join(", ");
      // Add as locked span for display
      const statsSpan: Span = { id: `stats_${Date.now()}`, layer: "locked", text: `s=${agent.saturation.s.toFixed(3)} ${top}`, startPos: 0, endPos: 0, committedAt: Date.now() };
      spanState.apply({ type: "append", span: statsSpan });
      return;
    }
    if (isCommandInput(text)) {
      router.dispatch(text, { agent, args: "", raw: text }).then(r => {
        if (r.output) {
          const cmdSpan: Span = { id: `cmd_${Date.now()}`, layer: "locked", text: r.output!, startPos: 0, endPos: 0, committedAt: Date.now() };
          spanState.apply({ type: "append", span: cmdSpan });
        }
      });
      return;
    }

    // Add user input as locked span
    const userSpan: Span = { id: `usr_${Date.now()}`, layer: "locked", text: `❯ ${text}`, startPos: 0, endPos: 0, committedAt: Date.now() };
    spanState.apply({ type: "append", span: userSpan });

    setGenStatus("generating");
    const t0 = Date.now();

    try {
      if (controllerRef.current) {
        await controllerRef.current.handleTurn(text);
      }
    } catch {
      setStatus("Error");
    }

    const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
    setGenStatus("idle");
    setStatus(`${agentName} · s=${agent.saturation.s.toFixed(2)} · ${elapsed}s · t${agent.turnCount}`);
  };

  // ═══════════════════════════════════════
  // Input handling
  // ═══════════════════════════════════════
  useInput((val: string, key: any) => {
    if (key.return) {
      const text = input.trim();
      if (!text) return;
      setInput(""); setCursor(0);
      history.add(text); history.resetCursor();
      submitText(text);
    } else if (key.upArrow) {
      const beforeCursor = input.slice(0, cursor);
      if (!beforeCursor.includes("\n")) {
        if (history.atNewest) savedInput.current = input;
        const entry = history.up();
        if (entry !== null) { setInput(entry); setCursor(entry.length); }
      } else {
        const lines = beforeCursor.split("\n");
        const prevLen = lines[lines.length - 2]?.length ?? 0;
        const curLen = lines[lines.length - 1]?.length ?? 0;
        setCursor(c => c - curLen - 1 - Math.max(0, curLen - prevLen));
      }
    } else if (key.downArrow) {
      const afterCursor = input.slice(cursor);
      if (!afterCursor.includes("\n")) {
        const entry = history.down();
        if (entry !== null) { setInput(entry); setCursor(entry.length); }
        else if (savedInput.current) { setInput(savedInput.current); setCursor(savedInput.current.length); savedInput.current = ""; }
      } else {
        const curEnd = input.indexOf("\n", cursor);
        const curLen = (curEnd === -1 ? input.length : curEnd) - (input.lastIndexOf("\n", cursor - 1) + 1);
        const nextStart = (curEnd === -1 ? input.length : curEnd) + 1;
        const nextEnd = input.indexOf("\n", nextStart);
        const nextLen = (nextEnd === -1 ? input.length : nextEnd) - nextStart;
        setCursor(nextStart + Math.min(curLen, nextLen));
      }
    } else if (key.leftArrow) { setCursor(c => Math.max(0, c - 1)); }
    else if (key.rightArrow) { setCursor(c => Math.min(input.length, c + 1)); }
    else if (key.home || (val === "a" && key.ctrl)) { setCursor(0); }
    else if (key.end || (val === "e" && key.ctrl)) { setCursor(input.length); }
    else if (key.backspace && cursor > 0) {
      setInput(p => p.slice(0, cursor - 1) + p.slice(cursor));
      setCursor(c => c - 1);
    } else if (key.delete && cursor < input.length) {
      setInput(p => p.slice(0, cursor) + p.slice(cursor + 1));
    } else if (val && !key.ctrl && !key.meta && !key.tab && !key.escape) {
      setInput(p => p.slice(0, cursor) + val + p.slice(cursor));
      setCursor(c => c + val.length);
    }
  });

  const cursorChar = cursor >= input.length ? '█' : '▌';
  const inputDisplay = input.slice(0, cursor) + cursorChar + input.slice(cursor);

  // ═══════════════════════════════════════
  // Render
  // ═══════════════════════════════════════
  const allSpans = spanState.getAllSpans();
  const visibleSpans = allSpans.length <= maxMsg ? allSpans : allSpans.slice(-maxMsg);

  return React.createElement(Box, { flexDirection: "column", height: "100%" },
    // Header
    React.createElement(Text, { bold: true, color: "cyan" }, `  ${agentName}`),

    // Messages — spans flow chronologically top-to-bottom
    React.createElement(Box, { flexDirection: "column", flexGrow: 1 },
      ...visibleSpans.map(s =>
        React.createElement(Text, { key: s.id, dimColor: s.layer === "fluid" }, s.text || " ")
      ),
    ),

    // Fixed input area at bottom
    React.createElement(Box, { flexDirection: "column", flexShrink: 0 },
      React.createElement(Text, { dimColor: true }, `  ${status}`),
      React.createElement(Text, { dimColor: true }, `  ${"─".repeat((stdout?.columns ?? 80) - 4)}`),
      ...inputDisplay.split("\n").map((line, i) =>
        React.createElement(Text, {
          key: `in_${i}`,
          color: i === inputDisplay.split("\n").length - 1 ? "cyan" : "white",
        }, `  ${i === 0 ? "❯ " : "  "}${line || " "}`)
      ),
    ),
  );
}

// ═══════════════════════════════════════
// ControllerAgent adapter (wraps CharacterAgent until Phase 6 refactor)
// ═══════════════════════════════════════

function createControllerAdapter(agent: CharacterAgent, spanState: SpanState) {
  return {
    getCommittedSpans(): Span[] {
      return spanState.getAllSpans();
    },
    snapshot: {
      formatForPrompt() { return agent.snapshot.formatForPrompt(); },
      freeze() { return agent.snapshot.freeze({}); },
      markDirty() { agent.snapshot.markDirty(); },
    },
    psychologyEngine: agent.psychologyEngine,
    selfModel: agent.selfModel,
    temporalHorizon: agent.temporalHorizon,
    affectiveResidue: agent.affectiveResidue,
    driveSublimator: agent.driveSublimator,
    drives: agent.drives,
    groundTruth: agent.groundTruth,
    config: {
      name: agent.config.name,
      traits: agent.config.traits,
      essence: agent.config.essence as string | undefined,
      rules: agent.config.rules as string | undefined,
    },
    async runColdPath(turnCtx: any) {
      return agent.runColdPath({ input: turnCtx.input, response: turnCtx.response ?? "" });
    },
    consumeStaleSlow(results: any[]) {
      agent.consumeStaleSlow(results);
    },
  };
}
