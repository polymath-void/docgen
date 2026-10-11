# Dynamic DocGen ⚡

> **Zero-Backend Living Architecture & Continuous AST Documentation Platform**
> Fast, offline-first codebase documentation engine with sub-second incremental caching, call-graph visualization, and in-browser WebAssembly execution.

---

## 🚀 Key Features

- **Zero-Dependency AST Extraction**: Parses Python and JS/TS codebases extracting modules, classes, methods, docstrings, type annotations, arguments, return types, call graphs, and McCabe cyclomatic complexity.
- **Incremental Merkle Hashing**: BLAKE2b content-addressed caching skips unchanged files; rebuilds complex projects in **15ms**.
- **Relational Knowledge Graph**: Generates bidirectional containment, inheritance, and call graph edges with callers/callees resolution.
- **Zero-Backend Static Portability**: Ships with a modern Vite + React 18 SPA developer cockpit:
  - **Overview**: System metrics, LOC, and architectural complexity hotspots.
  - **Symbol Inspector**: Complete parameter tables, type signatures, and source viewers.
  - **Architecture Graph**: Interactive SVG dependency visualizer.
  - **Living Sandbox**: In-browser Python WebAssembly execution via Pyodide.
  - **Instant Search**: Hotkey `/` modal with live fuzzy filtering.
- **Cross-Project Universal CLI**: Analyze and serve any local project in `~/Projects` with a single command.

---

## 🛠️ CLI Usage

DocGen is installed globally in `$PREFIX/bin/docgen` and can be invoked from any project directory.

### 1. Build Documentation Manifest
Analyze the current directory or target a specific project:

```bash
# Analyze current directory
docgen build

# Analyze a specific project
docgen build --dir ~/Projects/AnyProject

# Analyze and bundle static UI directly into target/docs_ui/
docgen build --dir ~/Projects/AnyProject --bundle-ui
```

### 2. Serve Living Documentation UI
Start the local server (default port `8088`):

```bash
# Serve documentation for current directory
docgen serve --port 8088

# Serve documentation for a specific project
docgen serve --dir ~/Projects/AnyProject --port 8088
```
Open `http://localhost:8088` in any browser or use `termux-open-url http://localhost:8088`.

### 3. Continuous Watch Mode
Automatically re-indexes on every file save with sub-second latency:

```bash
docgen watch --dir ~/Projects/AnyProject
```

---

## 📂 Architecture

```
DocGen/
├── bin/
│   └── docgen               # Termux / Linux executable wrapper
├── docgen/
│   ├── extractor.py         # AST symbol & complexity extractor
│   ├── merkle.py            # BLAKE2b caching layer
│   ├── compiler.py          # Knowledge graph & search index builder
│   └── ui/                  # Vite + React 18 SPA
│       ├── src/             # Frontend source code
│       ├── public/          # Public assets & docs_manifest.json
│       └── dist/            # Pre-bundled standalone distribution
├── docgen_cli.py            # Universal CLI entrypoint
├── setup.py                 # Python package manifest
└── test_docgen.py           # Verification test suite
```

---

## 🧪 Testing

Run the offline verification suite:
```bash
python3 test_docgen.py
```
Run the Universal QA syntax analyzer:
```bash
python ~/.gemini/config/skills/qa-analyzer/scripts/analyzer.py .
```
