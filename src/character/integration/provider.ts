/**
 * LLM Provider — OpenAI SDK wrapper for DeepSeek / any OpenAI-compatible API.
 * Ported from core/provider.py
 */
import OpenAI from "openai";

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface LLMResponse {
  content: string;
  reasoningContent: string;
  usage: Record<string, number>;
  finishReason: string;
  toolCalls: ToolCall[];
}

export class OpenAICompatProvider {
  public model: string;
  public client: OpenAI;

  constructor(model: string, apiKey: string, baseUrl: string) {
    this.model = model;
    this.client = new OpenAI({
      apiKey: apiKey || "not-needed",
      baseURL: baseUrl,
      maxRetries: 0,
    });
  }

  async chat(
    messages: Array<{ role: string; content: string }>,
    temperature = 0.7,
    maxTokens = 4096,
    _tools?: any,
    _model = "",
    signal?: AbortSignal,
  ): Promise<LLMResponse> {
    const resp = await this.client.chat.completions.create({
      model: _model || this.model,
      messages: messages as any,
      temperature,
      max_tokens: maxTokens,
    }, { signal });
    const choice = resp.choices?.[0];
    if (!choice) return { content: "", reasoningContent: "", usage: {}, finishReason: "stop", toolCalls: [] };
    const toolCalls: ToolCall[] = (choice.message?.tool_calls ?? []).map((tc: any) => ({
      id: tc.id, name: tc.function.name, arguments: JSON.parse(tc.function.arguments),
    }));
    return {
      content: choice.message?.content ?? "",
      reasoningContent: (choice.message as any)?.reasoning_content ?? "",
      usage: resp.usage ? { promptTokens: resp.usage.prompt_tokens, completionTokens: resp.usage.completion_tokens, totalTokens: resp.usage.total_tokens } : {},
      finishReason: choice.finish_reason ?? "stop",
      toolCalls,
    };
  }

  async chatStream(
    messages: Array<{ role: string; content: string }>,
    temperature = 0.7,
    maxTokens = 4096,
    _tools?: any,
    onDelta?: (text: string) => Promise<void>,
    _model = "",
    signal?: AbortSignal,
  ): Promise<LLMResponse> {
    const resp = await this.client.chat.completions.create({
      model: _model || this.model,
      messages: messages as any,
      temperature,
      max_tokens: maxTokens,
      stream: true,
      tools: _tools,
    }, { signal });

    let content = "";
    let reasoningContent = "";
    let finishReason = "stop";
    let usage: Record<string, number> = {};
    const toolCallAcc: Map<number, { id: string; name: string; args: string }> = new Map();

    for await (const chunk of resp) {
      if (signal?.aborted) break;
      if (chunk.choices?.[0]) {
        const delta = chunk.choices[0].delta;
        if (delta?.content) {
          content += delta.content;
          if (onDelta) await onDelta(delta.content);
        }
        const rc = (delta as any)?.reasoning_content;
        if (rc) reasoningContent += rc;
        if (chunk.choices[0].finish_reason) finishReason = chunk.choices[0].finish_reason;
        // Accumulate tool calls from stream deltas
        for (const tc of delta?.tool_calls ?? []) {
          const idx = tc.index as number;
          if (!toolCallAcc.has(idx)) toolCallAcc.set(idx, { id: tc.id ?? "", name: "", args: "" });
          const acc = toolCallAcc.get(idx)!;
          if (tc.id) acc.id = tc.id;
          if (tc.function?.name) acc.name += tc.function.name;
          if (tc.function?.arguments) acc.args += tc.function.arguments;
        }
      }
      if (chunk.usage) {
        usage = { promptTokens: chunk.usage.prompt_tokens, completionTokens: chunk.usage.completion_tokens, totalTokens: chunk.usage.total_tokens };
      }
    }

    const toolCalls: ToolCall[] = [...toolCallAcc.values()].map(tc => ({
      id: tc.id,
      name: tc.name,
      arguments: tryParseJson(tc.args),
    }));

    return { content, reasoningContent, usage, finishReason, toolCalls };
  }
}

function tryParseJson(s: string): Record<string, unknown> {
  try { return JSON.parse(s); } catch { return {}; }
}
