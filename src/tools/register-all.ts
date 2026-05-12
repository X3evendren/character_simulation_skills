import { ToolRegistry } from "./registry";
import { readFileTool } from "./builtin/read-file";
import { searchFilesTool } from "./builtin/search-files";
import { searchContentTool } from "./builtin/search-content";
import { writeFileTool } from "./builtin/write-file";
import { editFileTool } from "./builtin/edit-file";
import { execCommandTool } from "./builtin/exec-command";
import { webFetchTool } from "./builtin/web-fetch";
import { webSearchTool } from "./builtin/web-search";

export function registerAllTools(registry: ToolRegistry): void {
  registry.register(readFileTool);
  registry.register(searchFilesTool);
  registry.register(searchContentTool);
  registry.register(writeFileTool);
  registry.register(editFileTool);
  registry.register(execCommandTool);
  registry.register(webFetchTool);
  registry.register(webSearchTool);
}
