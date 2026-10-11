"""
DocGen Graph Compiler & Search Index Generator
=============================================================================
Compiles raw AST symbols into a relational knowledge graph (Nodes + Edges)
and generates an inverted full-text search index for the client-side SPA.
=============================================================================
"""

import os
import time
from typing import Dict, List, Any, Set
from docgen.extractor import extract_file_symbols
from docgen.merkle import MerkleASTCache
from docgen.enricher import DocGenEnricher

IGNORED_DIRS = {
    ".git", "node_modules", "dist", "build", "__pycache__",
    ".pytest_cache", ".agents", ".opencode", ".venv", "venv",
    "site-packages", ".idea", ".vscode"
}

VALID_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}

PYTHON_BUILTINS = {
    "print", "len", "range", "str", "int", "float", "bool", "list", "dict", "set",
    "tuple", "open", "isinstance", "issubclass", "hasattr", "getattr", "setattr",
    "delattr", "enumerate", "zip", "map", "filter", "any", "all", "sum", "min", "max",
    "sorted", "reversed", "round", "abs", "repr", "iter", "next", "super", "type",
    "id", "hash", "dir", "vars", "callable", "format", "input", "eval", "exec", "compile",
    "join", "split", "splitlines", "strip", "lstrip", "rstrip", "replace", "append",
    "extend", "insert", "pop", "remove", "clear", "index", "count", "sort", "reverse",
    "get", "keys", "values", "items", "update", "setdefault", "startswith", "endswith",
    "lower", "upper", "capitalize", "read", "write", "close", "readline", "readlines",
    "seek", "tell", "flush", "add", "copy", "difference", "intersection", "union",
    "groups", "group", "start", "end", "span", "finditer", "findall", "match", "search", "sub",
    "hexdigest", "digest", "encode", "decode", "sleep",
    "assertEqual", "assertNotEqual", "assertTrue", "assertFalse", "assertIn", "assertNotIn",
    "assertIs", "assertIsNot", "assertIsNone", "assertIsNotNone", "assertIsInstance",
    "assertRaises", "assertGreater", "assertGreaterEqual", "assertLess", "assertLessEqual",
    "send_response", "send_header", "end_headers", "serve_forever",
    "add_argument", "add_subparsers", "add_parser", "parse_args"
}

JS_BUILTINS = {
    "console", "Math", "JSON", "Promise", "Array", "Object", "String", "Number", "Boolean",
    "crypto", "window", "document", "navigator", "location", "history", "fetch",
    "setTimeout", "setInterval", "clearTimeout", "clearInterval", "parseInt", "parseFloat",
    "encodeURIComponent", "decodeURIComponent", "alert", "confirm", "prompt",
    "addEventListener", "removeEventListener", "WebSocket", "RTCPeerConnection",
    "RTCDataChannel", "RTCIceCandidate", "RTCSessionDescription", "Blob", "FileReader",
    "URL", "URLSearchParams", "TextEncoder", "TextDecoder", "Uint8Array", "ArrayBuffer",
    "Map", "Set", "WeakMap", "WeakSet", "Error", "TypeError", "RangeError", "require",
    "push", "pop", "shift", "unshift", "slice", "splice", "concat", "includes",
    "indexOf", "lastIndexOf", "forEach", "map", "filter", "reduce", "find", "findIndex",
    "some", "every", "join", "split", "trim", "replace", "replaceAll", "substring",
    "toLowerCase", "toUpperCase", "startsWith", "endsWith", "getElementById",
    "querySelector", "querySelectorAll", "createElement", "appendChild", "removeChild",
    "classList", "focus", "select", "send", "close", "open"
}


class DocGenCompiler:
    def __init__(self, root_dir: str, cache_file: str = ".docgen_cache.json"):
        self.root_dir = os.path.abspath(root_dir)
        self.cache = MerkleASTCache(cache_file=os.path.join(self.root_dir, cache_file))

    def discover_files(self) -> List[str]:
        """Finds all parsable source files in the target directory."""
        found = []
        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]
            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in VALID_EXTENSIONS:
                    found.append(os.path.join(root, file))
        return found

    def compile(self) -> Dict[str, Any]:
        """Executes full incremental compilation of the codebase documentation."""
        start_time = time.time()
        files = self.discover_files()
        existing_rel_files = set()

        all_file_data = []
        stats = {
            "total_files": len(files),
            "total_loc": 0,
            "total_classes": 0,
            "total_functions": 0,
            "avg_complexity": 0.0,
            "complexities": []
        }

        # 1. Parse or load from Merkle cache
        for fpath in files:
            rel_path = os.path.relpath(fpath, self.root_dir).replace("\\", "/")
            existing_rel_files.add(rel_path)
            mtime = os.path.getmtime(fpath)

            if self.cache.is_cached(rel_path, mtime):
                data = self.cache.get_cached_symbols(rel_path)
            else:
                data = extract_file_symbols(fpath, self.root_dir)
                self.cache.update(rel_path, mtime, data)

            if data:
                all_file_data.append(data)
                stats["total_loc"] += data.get("loc", 0)
                stats["total_classes"] += len(data.get("classes", []))
                stats["total_functions"] += len(data.get("functions", []))
                for c in data.get("classes", []):
                    stats["total_functions"] += len(c.get("methods", []))
                    for m in c.get("methods", []):
                        stats["complexities"].append(m.get("complexity", 1))
                for fn in data.get("functions", []):
                    stats["complexities"].append(fn.get("complexity", 1))

        # Save updated cache
        self.cache.prune_stale(existing_rel_files)
        self.cache.save()

        if stats["complexities"]:
            stats["avg_complexity"] = round(sum(stats["complexities"]) / len(stats["complexities"]), 2)
        del stats["complexities"]

        # 2. Build Unified Symbol Dictionary
        symbols: Dict[str, Any] = {}
        # Quick lookup for symbol resolution: name -> [full_names]
        name_to_ids: Dict[str, List[str]] = {}

        for f in all_file_data:
            # File node
            f_id = f"module:{f['file']}"
            symbols[f_id] = {
                "id": f_id,
                "name": f["file"],
                "type": "module",
                "file": f["file"],
                "docstring": f.get("docstring", ""),
                "loc": f.get("loc", 0),
                "imports": f.get("imports", [])
            }

            for c in f.get("classes", []):
                cid = c["full_name"]
                symbols[cid] = c
                name_to_ids.setdefault(c["name"], []).append(cid)
                for m in c.get("methods", []):
                    mid = m["full_name"]
                    symbols[mid] = m
                    name_to_ids.setdefault(m["name"], []).append(mid)

            for fn in f.get("functions", []):
                fn_id = fn["full_name"]
                symbols[fn_id] = fn
                name_to_ids.setdefault(fn["name"], []).append(fn_id)

        # 3. Resolve Call Graph & Build Graph with Reference Diagnostics
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []

        diagnostics = {
            "unresolved": [],
            "ambiguous": [],
            "external_builtins": {},
            "orphans": []
        }

        total_calls_count = 0
        resolved_internal_count = 0

        # Map of file_path -> set of imported root names/aliases
        file_imports = {}
        for f in all_file_data:
            imported_names = set()
            for imp in f.get("imports", []):
                if isinstance(imp, dict):
                    alias = imp.get("alias") or imp.get("module", "")
                    imported_names.add(alias.split(".")[0])
                    if imp.get("module"):
                        imported_names.add(imp.get("module").split(".")[0])
                        imported_names.add(imp.get("module"))
            file_imports[f["file"]] = imported_names

        for sid, sym in symbols.items():
            nodes.append({
                "id": sid,
                "name": sym["name"],
                "type": sym["type"],
                "file": sym["file"],
                "line": sym.get("line", 1)
            })

            # Containment edges
            if sym["type"] in ["class", "function"]:
                edges.append({
                    "source": f"module:{sym['file']}",
                    "target": sid,
                    "relation": "contains"
                })
            elif sym["type"] == "method" and sym.get("parent_class"):
                edges.append({
                    "source": f"{sym['file']}:{sym['parent_class']}",
                    "target": sid,
                    "relation": "contains"
                })

            # Inheritance edges
            if sym["type"] == "class":
                for base in sym.get("bases", []):
                    if base in name_to_ids:
                        for target_id in name_to_ids[base]:
                            edges.append({
                                "source": sid,
                                "target": target_id,
                                "relation": "inherits"
                            })

            # Call edges & Diagnostic checking
            calls = sym.get("calls", [])
            sym["callers"] = []
            sym["unresolved_calls"] = []
            sym["ambiguous_calls"] = []
            file_imp = file_imports.get(sym["file"], set())

            for called_name in calls:
                total_calls_count += 1
                root_name = called_name.split(".")[0]
                tail_name = called_name.split(".")[-1]

                # 1. Exact match in repository symbols
                if called_name in name_to_ids:
                    targets = name_to_ids[called_name]
                    if len(targets) == 1:
                        resolved_internal_count += 1
                        edges.append({
                            "source": sid,
                            "target": targets[0],
                            "relation": "calls"
                        })
                    else:
                        # Ambiguous / bulk references (matched across multiple classes/files)
                        resolved_internal_count += 1
                        sym["ambiguous_calls"].append({
                            "name": called_name,
                            "candidates": targets
                        })
                        diagnostics["ambiguous"].append({
                            "source": sid,
                            "source_name": sym["name"],
                            "file": sym["file"],
                            "line": sym.get("line", 1),
                            "called_name": called_name,
                            "candidates": targets
                        })
                        for target_id in targets:
                            edges.append({
                                "source": sid,
                                "target": target_id,
                                "relation": "calls_ambiguous"
                            })
                # 2. Method invocation on self, this, or cls
                elif called_name.startswith(("self.", "this.", "cls.")) and tail_name in name_to_ids:
                    targets = name_to_ids[tail_name]
                    resolved_internal_count += 1
                    edges.append({
                        "source": sid,
                        "target": targets[0],
                        "relation": "calls"
                    })
                # 3. Call to an imported module or package
                elif root_name in file_imp or called_name in file_imp:
                    diagnostics["external_builtins"][called_name] = diagnostics["external_builtins"].get(called_name, 0) + 1
                # 4. Standard runtime built-in (Python or JS)
                elif (
                    called_name in PYTHON_BUILTINS or
                    called_name in JS_BUILTINS or
                    tail_name in PYTHON_BUILTINS or
                    tail_name in JS_BUILTINS or
                    root_name in PYTHON_BUILTINS or
                    root_name in JS_BUILTINS
                ):
                    diagnostics["external_builtins"][called_name] = diagnostics["external_builtins"].get(called_name, 0) + 1
                # 5. Method call on object instance matching project symbols
                elif "." in called_name and tail_name in name_to_ids:
                    targets = name_to_ids[tail_name]
                    if len(targets) == 1:
                        resolved_internal_count += 1
                        edges.append({
                            "source": sid,
                            "target": targets[0],
                            "relation": "calls"
                        })
                    else:
                        resolved_internal_count += 1
                        sym["ambiguous_calls"].append({
                            "name": called_name,
                            "candidates": targets
                        })
                        diagnostics["ambiguous"].append({
                            "source": sid,
                            "source_name": sym["name"],
                            "file": sym["file"],
                            "line": sym.get("line", 1),
                            "called_name": called_name,
                            "candidates": targets
                        })
                        for target_id in targets:
                            edges.append({
                                "source": sid,
                                "target": target_id,
                                "relation": "calls_ambiguous"
                            })
                # 6. Truly Unresolved / Broken Reference!
                else:
                    sym["unresolved_calls"].append(called_name)
                    diagnostics["unresolved"].append({
                        "source": sid,
                        "source_name": sym["name"],
                        "file": sym["file"],
                        "line": sym.get("line", 1),
                        "called_name": called_name
                    })


        # Reverse caller population
        for edge in edges:
            if edge["relation"] in ["calls", "calls_ambiguous"]:
                target = edge["target"]
                source = edge["source"]
                if target in symbols:
                    if "callers" not in symbols[target]:
                        symbols[target]["callers"] = []
                    if source not in symbols[target]["callers"]:
                        symbols[target]["callers"].append(source)

        # Detect Orphan symbols (dead code / unreferenced internal symbols)
        ENTRY_NAMES = {"main", "__init__", "handler", "do_GET", "do_POST", "setUpClass", "tearDownClass", "run", "boot"}
        for sid, sym in symbols.items():
            if sym["type"] in ["function", "method", "class"]:
                if len(sym.get("callers", [])) == 0 and sym["name"] not in ENTRY_NAMES and not sym["name"].startswith("test_"):
                    diagnostics["orphans"].append({
                        "id": sid,
                        "name": sym["name"],
                        "type": sym["type"],
                        "file": sym["file"],
                        "line": sym.get("line", 1)
                    })

        # Compute Reference Integrity Metrics
        total_eval = max(1, total_calls_count)
        integrity_score = round(((total_eval - len(diagnostics["unresolved"])) / total_eval) * 100, 1)

        stats["integrity_score"] = f"{integrity_score}%"
        stats["unresolved_refs"] = len(diagnostics["unresolved"])
        stats["ambiguous_refs"] = len(diagnostics["ambiguous"])
        stats["orphan_symbols"] = len(diagnostics["orphans"])

        # 4. Generate Inverted Search Index
        search_index = []
        for sid, sym in symbols.items():
            search_index.append({
                "id": sid,
                "name": sym["name"],
                "type": sym["type"],
                "file": sym["file"],
                "line": sym.get("line", 1),
                "doc": sym.get("docstring", "")[:120],
                "sig": sym.get("signature", "")
            })

        project_name = os.path.basename(self.root_dir)
        elapsed = round(time.time() - start_time, 3)

        manifest = {
            "project": {
                "name": project_name,
                "root": self.root_dir,
                "compiled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "build_duration_sec": elapsed,
                "stats": stats
            },
            "diagnostics": {
                "summary": {
                    "total_calls": total_calls_count,
                    "resolved_internal": resolved_internal_count,
                    "unresolved": len(diagnostics["unresolved"]),
                    "ambiguous": len(diagnostics["ambiguous"]),
                    "external_builtins": sum(diagnostics["external_builtins"].values()),
                    "orphan_symbols": len(diagnostics["orphans"]),
                    "integrity_score": f"{integrity_score}%"
                },
                "unresolved": diagnostics["unresolved"],
                "ambiguous": diagnostics["ambiguous"],
                "external_builtins": diagnostics["external_builtins"],
                "orphans": diagnostics["orphans"]
            },
            "symbols": symbols,
            "graph": {
                "nodes": nodes,
                "edges": edges
            },
            "search_index": search_index
        }

        # 5. Enrich Symbols with Topological Guides (Layer 2)
        enricher = DocGenEnricher(manifest)
        manifest = enricher.enrich_all()

        return manifest


