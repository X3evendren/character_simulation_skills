/** Provider Registry — Declarative LLM provider system. Copied nanobot pattern. */

export interface ProviderSpec {
  name: string;
  keywords: string[];
  envKey: string;
  backend: "anthropic" | "openai_compat";
  isGateway: boolean;
  isLocal: boolean;
  defaultApiBase: string;
  supportsPromptCaching: boolean;
  thinkingStyle: "reasoning_content" | "thinking" | "";
  modelOverrides: Record<string, { temperature?: number; maxTokens?: number }>;
}

export const PROVIDERS: ProviderSpec[] = [
  {
    name: "deepseek", keywords: ["deepseek", "v4", "r1"],
    envKey: "DEEPSEEK_API_KEY", backend: "openai_compat",
    isGateway: false, isLocal: false,
    defaultApiBase: "https://api.deepseek.com/v1",
    supportsPromptCaching: false, thinkingStyle: "reasoning_content",
    modelOverrides: {},
  },
  {
    name: "anthropic", keywords: ["claude", "sonnet", "opus", "haiku"],
    envKey: "ANTHROPIC_API_KEY", backend: "anthropic",
    isGateway: false, isLocal: false,
    defaultApiBase: "https://api.anthropic.com/v1",
    supportsPromptCaching: true, thinkingStyle: "thinking",
    modelOverrides: {},
  },
  {
    name: "openai", keywords: ["gpt", "o1", "o3", "o4"],
    envKey: "OPENAI_API_KEY", backend: "openai_compat",
    isGateway: false, isLocal: false,
    defaultApiBase: "https://api.openai.com/v1",
    supportsPromptCaching: false, thinkingStyle: "",
    modelOverrides: {},
  },
  {
    name: "openrouter", keywords: ["openrouter", "open-router"],
    envKey: "OPENROUTER_API_KEY", backend: "openai_compat",
    isGateway: true, isLocal: false,
    defaultApiBase: "https://openrouter.ai/api/v1",
    supportsPromptCaching: false, thinkingStyle: "",
    modelOverrides: {},
  },
  {
    name: "ollama", keywords: ["ollama", "llama", "mistral", "qwen", "gemma"],
    envKey: "OLLAMA_API_KEY", backend: "openai_compat",
    isGateway: false, isLocal: true,
    defaultApiBase: "http://localhost:11434/v1",
    supportsPromptCaching: false, thinkingStyle: "",
    modelOverrides: {},
  },
  {
    name: "vllm", keywords: ["vllm"],
    envKey: "VLLM_API_KEY", backend: "openai_compat",
    isGateway: false, isLocal: true,
    defaultApiBase: "http://localhost:8000/v1",
    supportsPromptCaching: false, thinkingStyle: "",
    modelOverrides: {},
  },
];

/**
 * Multi-level match: API key prefix → base URL keywords → model name keywords → explicit provider name.
 * Copied from nanobot providers/registry.py detect pattern.
 */
export function detectProvider(
  apiKey?: string, baseUrl?: string, model?: string,
): ProviderSpec | undefined {
  // Level 1: API key prefix matching
  if (apiKey) {
    if (apiKey.startsWith("sk-ant-")) return getByName("anthropic");
    if (apiKey.startsWith("sk-or-")) return getByName("openrouter");
    if (apiKey.startsWith("sk-")) return getByName("deepseek"); // default openai compat
  }

  // Level 2: Base URL keyword matching
  if (baseUrl) {
    const urlLower = baseUrl.toLowerCase();
    for (const p of PROVIDERS) {
      if (urlLower.includes(p.defaultApiBase.toLowerCase().replace("https://", "").replace("http://", "").split("/")[0])) return p;
      if (urlLower.includes("11434")) return getByName("ollama");
      if (urlLower.includes("8000")) return getByName("vllm");
    }
  }

  // Level 3: Model name keyword matching
  if (model) {
    const mLower = model.toLowerCase();
    for (const p of PROVIDERS) {
      if (p.keywords.some(kw => mLower.includes(kw))) return p;
    }
  }

  return undefined;
}

export function getByName(name: string): ProviderSpec | undefined {
  return PROVIDERS.find(p => p.name === name);
}

export function getByModel(model: string): ProviderSpec | undefined {
  const mLower = model.toLowerCase();
  return PROVIDERS.find(p => p.keywords.some(kw => mLower.includes(kw)));
}

export interface ResolvedProvider {
  spec: ProviderSpec;
  apiKey: string;
  baseUrl: string;
  model: string;
}

export function resolveProvider(
  providerName: string, model: string, apiKey?: string, baseUrl?: string,
): ResolvedProvider | undefined {
  const spec = getByName(providerName) ?? detectProvider(apiKey, baseUrl, model);
  if (!spec) return undefined;

  const key = apiKey || process.env[spec.envKey] || "";
  const url = baseUrl || spec.defaultApiBase;

  return { spec, apiKey: key, baseUrl: url, model };
}
