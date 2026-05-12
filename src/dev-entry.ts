// Route: TTY → Ink UI, non-TTY → readline fallback
if (process.stdin.isTTY && typeof process.stdin.setRawMode === "function") {
  // Ink TUI (PowerShell / Windows Terminal / real TTY)
  import("./ink-main");
} else {
  // Readline fallback (pipes, Git Bash, non-TTY)
  import("./main").then(m => m.main()).catch((err: any) => { console.error("Fatal:", err); process.exit(1); });
}
