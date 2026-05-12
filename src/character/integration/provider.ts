/**
 * LLM Provider — OpenAI SDK wrapper for DeepSeek / any OpenAI-compatible API.
 * Ported from core/provider.py
 */
import OpenAI from "openai";

export interface LLMResponse {
  content: string;
  reasoningContent: string;
  usage: Record<string, number>;
  finishReason: string;
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
    if (!choice) return { content: "", reasoningContent: "", usage: {}, finishReason: "stop" };
    return {
      content: choice.message?.content ?? "",
      reasoningContent: (choice.message as any)?.reasoning_content ?? "",
      usage: resp.usage ? { promptTokens: resp.usage.prompt_tokens, completionTokens: resp.usage.completion_tokens, totalTokens: resp.usage.total_tokens } : {},
      finishReason: choice.finish_reason ?? "stop",
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
    const stream = await this.client.chat.completions.create({
      model: _model || this.model,
      messages: messages as any,
      temperature,
      max_tokens: maxTokens,
      stream: true,
    }, { signal });

    let content = "";
    let reasoningContent = "";
    let finishReason = "stop";
    let usage: Record<string, number> = {};

    for await (const chunk of stream) {
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
      }
      if (chunk.usage) {
        usage = { promptTokens: chunk.usage.prompt_tokens, completionTokens: chunk.usage.completion_tokens, totalTokens: chunk.usage.total_tokens };
      }
    }

    return { content, reasoningContent, usage, finishReason };
  }
}
