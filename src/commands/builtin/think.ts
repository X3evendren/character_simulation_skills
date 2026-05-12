import type { PromptCommand, CommandContext } from "../types";

/**
 * /think — inject a reflective prompt for the character.
 * Example: /think 我今天心情不好 → expands to "请以角色身份，对'我今天心情不好'进行深度反思..."
 */
export const thinkCommand: PromptCommand = {
  type: "prompt",
  name: "think",
  description: "Ask the character to reflect deeply on something",
  aliases: ["reflect"],
  getPromptForCommand(args: string, ctx: CommandContext): string {
    const name = ctx.agent.config.name;
    return `【深度反思模式】

${name}，请用你的角色身份，对以下内容进行深度反思：

"${args || "最近的经历和感受"}"

请从你的内心出发，探索：
1. 这件事触动了你的哪些情感
2. 你内心有什么不愿意承认但真实存在的感受
3. 这件事与你的誓约、自我认知有何关联

用你的方式表达。不是分析，而是呈现。`;
  },
};
