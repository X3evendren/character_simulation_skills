
import pathlib, re
files = [
    "src/character/memory/short-term.ts",
    "src/character/memory/long-term.ts",
    "src/character/memory/core-graph.ts",
]
for fp in files:
    c = pathlib.Path(fp).read_text("utf-8")
    c = c.replace("import type Database from bun:sqlite", "import Database from better-sqlite3")
    c = c.replace("const { Database } = await import(bun:sqlite);", "")
    c = c.replace("import Database from bun:sqlite", "import Database from better-sqlite3")
    # Replace .run( -> .exec( for CREATE TABLE, .
    # Actually best approach: handle each pattern manually
    c = c.replace("this._db.run(", "this._db.exec(")
    c = c.replace("this._db!.run(", "this._db!.exec(")
    c = c.replace("this._db!.query(", "this._db!.prepare(")
    # Remove auto-commit comments
    c = re.sub(r"\s*// bun:sqlite[^
]*
?", "", c)
    pathlib.Path(fp).write_text(c, "utf-8")
    print(f"  {fp}")
print("done")
