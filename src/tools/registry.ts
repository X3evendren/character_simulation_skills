/** Tool Registry — register, lookup, generate OpenAI function definitions. */

import type { ToolDef, ToolResult, ToolContext, PermissionResult } from "./types";
import { PermissionRules, TerminalConfirm } from "./permission";
import { ResultStorage } from "./result-storage";
import { randomUUID } from "crypto";
import type { GuardPipeline } from "../guard/pipeline";

export class ToolRegistry {
  private tools = new Map<string, ToolDef>();
  private resultStorage = new ResultStorage(process.cwd());
  private terminalConfirm = new TerminalConfirm();
  guardPipeline?: GuardPipeline;

  register(tool: ToolDef): void {
    this.tools.set(tool.name, tool);
    if (tool.aliases) {
      for (const alias of tool.aliases) {
        this.tools.set(alias, tool);
      }
    }
  }

  get(name: string): ToolDef | undefined {
    return this.tools.get(name);
  }

  /** Generate OpenAI function-calling tool definitions. */
  getDefinitions(): Array<Record<string, unknown>> {
    const defs: Array<Record<string, unknown>> = [];
    const seen = new Set<string>();
    for (const tool of this.tools.values()) {
      if (seen.has(tool.name)) continue;
      seen.add(tool.name);
      defs.push({
        type: "function",
        function: {
          name: tool.name,
          description: tool.description,
          parameters: this._zodToJsonSchema(tool.parameters),
        },
      });
    }
    return defs;
  }

  /** Full execution pipeline: validate → permission → execute → format → store. */
  async execute(name: string, params: any, ctx: ToolContext): Promise<ToolResult> {
    const tool = this.get(name);
    if (!tool) {
      return { success: false, error: `Unknown tool: ${name}`, output: `Error: unknown tool "${name}"`, truncated: false };
    }

    // Step 1: Zod schema validation
    const parsed = tool.parameters.safeParse(params);
    if (!parsed.success) {
      const msg = parsed.error.issues.map(e => `${e.path.join(".")}: ${e.message}`).join("; ");
      return { success: false, error: msg, output: `Invalid params: ${msg}`, truncated: false };
    }

    // Step 2: Permission check
    const permResult = await this._checkPermission(tool, parsed.data, ctx);
    if (permResult.behavior === "deny") {
      return { success: false, error: permResult.reason, output: `Denied: ${permResult.reason}`, truncated: false };
    }
    if (permResult.behavior === "ask") {
      const approved = await this.terminalConfirm.confirm(tool, parsed.data, ctx);
      if (!approved) {
        return { success: false, error: "User denied", output: "Denied by user.", truncated: false };
      }
    }

    // Step 2.5: Guardrail — tool call validation
    if (this.guardPipeline) {
      const guardCheck = await this.guardPipeline.checkToolCall({
        name: tool.name,
        arguments: parsed.data as Record<string, unknown>,
      });
      if (!guardCheck.allowed) {
        return { success: false, error: guardCheck.reason ?? "Blocked by guardrail", output: `Blocked: ${guardCheck.reason}`, truncated: false };
      }
    }

    // Step 3: Execute
    let result: ToolResult;
    try {
      result = await tool.execute(parsed.data, ctx);
    } catch (e: any) {
      return { success: false, error: e.message, output: tool.formatError(e.message, parsed.data), truncated: false };
    }

    // Step 3.5: Guardrail — tool result validation
    if (this.guardPipeline) {
      this.guardPipeline.checkToolResult({
        name: tool.name,
        success: result.success,
        output: result.output,
        error: result.error,
      });
    }

    // Step 4: Format + store
    const toolUseId = randomUUID();
    if (result.success && result.data !== undefined) {
      const formatted = tool.formatResult(result.data, parsed.data);
      result.output = this.resultStorage.process(toolUseId, formatted, tool.name);
    } else if (!result.success) {
      result.output = tool.formatError(result.error ?? "unknown error", parsed.data);
    }

    return result;
  }

  get length(): number {
    return new Set([...this.tools.values()].map(t => t.name)).size;
  }

  private async _checkPermission(tool: ToolDef, params: any, ctx: ToolContext): Promise<PermissionResult> {
    // For exec_command, check dangerous patterns first
    if (tool.name === "exec_command" && params.command) {
      const audit = PermissionRules.auditCommand(params.command);
      if (audit.blocked) {
        return { behavior: "deny", reason: audit.reason };
      }
    }
    return PermissionRules.evaluate(tool, params, ctx);
  }

  private _zodToJsonSchema(schema: any): Record<string, unknown> {
    // Use zod's built-in toJSONSchema or zod-to-json-schema
    try {
      // zod v3 has zod.toJSONSchema or we use the shape directly
      if (typeof schema.toJSONSchema === "function") return schema.toJSONSchema();
    } catch {}
    // Fallback: extract from zod object shape
    try {
      const shape = schema._def?.shape?.();
      if (shape) {
        const props: Record<string, unknown> = {};
        const required: string[] = [];
        for (const [key, field] of Object.entries(shape) as [string, any][]) {
          const fieldType = this._fieldToJsonType(field);
          props[key] = fieldType;
          if (!field.isOptional?.()) required.push(key);
        }
        return { type: "object", properties: props, required };
      }
    } catch {}
    return { type: "object", properties: {} };
  }

  private _fieldToJsonType(field: any): Record<string, unknown> {
    let def = field._def ?? field;
    // Unwrap ZodOptional / ZodDefault / ZodNullable
    while (def.typeName === "ZodOptional" || def.typeName === "ZodDefault" || def.typeName === "ZodNullable") {
      def = def.innerType?._def ?? def.innerType ?? def;
      if (!def.typeName) break;
    }
    const zodType = def.typeName ?? "";
    const desc = def.description ?? "";
    const schema: Record<string, unknown> = {};

    // Map Zod type names to JSON Schema types
    const typeMap: Record<string, string> = {
      ZodString: "string", ZodNumber: "number", ZodBoolean: "boolean",
      ZodArray: "array", ZodObject: "object", ZodNull: "null",
      ZodEnum: "string", ZodBigInt: "integer",
    };
    const jsonType = typeMap[zodType] || "string";
    schema.type = jsonType;
    if (desc) schema.description = desc;

    // Enum values
    if (zodType === "ZodEnum" && def.values) {
      schema.enum = def.values;
    }
    return schema;
  }
}
