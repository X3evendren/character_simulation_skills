/**
 * Slash command parser — 
 * Extracts command name and arguments from /command input.
 */

export interface ParsedSlashCommand {
  /** The command name (without /) */
  name: string;
  /** Everything after the command name */
  args: string;
  /** Original full input */
  raw: string;
}

/**
 * Parse "/stats --full" → { name: "stats", args: "--full", raw: "/stats --full" }
 * Handle edge cases: empty command, whitespace-only, multiple slashes
 */
export function parseSlashCommand(input: string): ParsedSlashCommand | null {
  if (!input.startsWith("/")) return null;

  // Strip leading /
  const rest = input.slice(1).trim();
  if (!rest) return null; // Input was just "/"

  // Split on first whitespace: name vs args
  const spaceIdx = rest.search(/\s/);
  if (spaceIdx === -1) {
    return { name: rest.toLowerCase(), args: "", raw: input };
  }

  const name = rest.slice(0, spaceIdx).toLowerCase();
  const args = rest.slice(spaceIdx + 1).trim();
  return { name, args, raw: input };
}

/**
 * Check if input looks like a command (starts with /)
 */
export function isCommandInput(input: string): boolean {
  return input.trim().startsWith("/");
}
