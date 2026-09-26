"""
Code Quality and Duplication Agent for CodePilot Multi-Agent Architecture.
Detects redundant implementations, duplicated code blocks, dead functions,
and excessive abstraction layers without introducing unnecessary complexity.
"""
import os
import re
import ast
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Tuple, Set, Optional
from collections import defaultdict
from codepilot.agent.base_agent import BaseSpecializedAgent, AgentTask, AgentResult
from codepilot.safety.policy import SafetyPolicy
from codepilot.llm.adapter import LLMAdapter


class CodeQualityAgent(BaseSpecializedAgent):
    agent_id: str = "code_quality"
    agent_role: str = "Code Quality & Duplication Agent"
    is_read_only: bool = True
    description: str = "Analyzes repository for duplicated blocks, dead code, and maintainability improvements."

    def __init__(self, workspace_root: str, llm: LLMAdapter, safety: SafetyPolicy):
        super().__init__(workspace_root, llm, safety)
        self.workspace_path = Path(workspace_root).resolve()

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        findings: List[Dict[str, Any]] = []
        errors: List[str] = []

        source_files = self._collect_python_files()

        # 1. Duplication Detection across files (sliding window of normalized lines)
        duplication_findings = self._detect_duplicates(source_files)
        findings.extend(duplication_findings)

        # 2. Dead Code / Unused Function Detection (AST analysis)
        dead_code_findings = self._detect_unused_definitions(source_files)
        findings.extend(dead_code_findings)

        # 3. Excessive Abstraction & Pass-through wrapper analysis
        abstraction_findings = self._detect_shallow_wrappers(source_files)
        findings.extend(abstraction_findings)

        # 4. LLM Refactoring synthesis
        llm_recommendations = self._run_llm_quality_review(findings)

        # 5. Generate artifacts
        artifacts_dir = self.workspace_path / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        json_path = artifacts_dir / "duplication_findings.json"
        md_path = artifacts_dir / "code_quality_report.md"

        report_data = {
            "agent_id": self.agent_id,
            "scan_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "files_analyzed": len(source_files),
            "findings_count": len(findings),
            "findings": findings,
            "refactoring_guidance": llm_recommendations,
            "principle": "Minimize unnecessary complexity. Simplify and consolidate rather than adding redundant abstraction layers."
        }

        json_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
        markdown_text = self._render_markdown_report(report_data)
        md_path.write_text(markdown_text, encoding="utf-8")

        runtime = round(time.time() - start_time, 2)
        summary = (
            f"Code Quality scan completed: {len(source_files)} files analyzed, "
            f"{len(findings)} quality/duplication opportunities detected. Report saved to artifacts/code_quality_report.md."
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="SUCCESS" if not errors else "PARTIAL",
            findings=findings,
            artifacts={
                "duplication_findings_json": str(json_path),
                "code_quality_report_md": str(md_path)
            },
            evidence={
                "files_analyzed": len(source_files),
                "duplications_found": len(duplication_findings),
                "dead_code_candidates": len(dead_code_findings)
            },
            metrics={"runtime_seconds": runtime, "files_inspected": len(source_files)},
            errors=errors,
            summary=summary
        )

    def _collect_python_files(self) -> List[Path]:
        collected = []
        ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", "artifacts"}
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                if file.endswith(".py"):
                    collected.append(Path(root) / file)
        return collected[:100]

    def _detect_duplicates(self, files: List[Path], window_size: int = 5) -> List[Dict[str, Any]]:
        findings = []
        chunk_hashes: Dict[str, List[Tuple[str, int]]] = defaultdict(list)

        for file_path in files:
            rel_path = str(file_path.relative_to(self.workspace_path))
            try:
                lines = [l.strip() for l in file_path.read_text(encoding="utf-8", errors="ignore").splitlines()]
                # Filter out blank lines and comments
                filtered = [(idx + 1, l) for idx, l in enumerate(lines) if l and not l.startswith("#")]

                for i in range(len(filtered) - window_size + 1):
                    window = [l for _, l in filtered[i:i + window_size]]
                    normalized = "".join(window)
                    if len(normalized) > 50:  # Avoid trivial repetitions
                        h = hashlib.md5(normalized.encode("utf-8")).hexdigest()
                        chunk_hashes[h].append((rel_path, filtered[i][0]))
            except Exception:
                continue

        # Group matches
        seen_pairs = set()
        finding_id = 1
        for h, occurrences in chunk_hashes.items():
            if len(occurrences) > 1:
                # Distinct locations
                unique_files = list({loc[0] for loc in occurrences})
                if len(unique_files) > 1:
                    pair_key = tuple(sorted(unique_files[:2]))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        findings.append({
                            "finding_id": f"QUAL-{finding_id:03d}",
                            "type": "DUPLICATE_CODE_BLOCK",
                            "affected_files": [f"{loc[0]}:L{loc[1]}" for loc in occurrences[:4]],
                            "description": f"Identical logic block ({window_size} statements) repeated across {len(occurrences)} locations.",
                            "suggested_refactoring": "Extract repeated logic into a shared helper function in an existing utility module.",
                            "expected_maintainability_benefit": f"Consolidates {len(occurrences)} duplicate implementations into a single source of truth.",
                            "regression_risk": "LOW — safe to extract if unit tests verify behavior.",
                            "verification_evidence": "Run test suite to verify no behavior alteration after refactoring."
                        })
                        finding_id += 1
                        if len(findings) >= 5:
                            break
        return findings

    def _detect_unused_definitions(self, files: List[Path]) -> List[Dict[str, Any]]:
        findings = []
        all_content = ""
        defined_functions: Dict[str, Tuple[str, int]] = {}

        for file_path in files:
            rel_path = str(file_path.relative_to(self.workspace_path))
            try:
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                all_content += "\n" + code
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Skip private / magic methods or test functions
                        if not node.name.startswith("_") and not node.name.startswith("test_"):
                            defined_functions[node.name] = (rel_path, node.lineno)
            except Exception:
                continue

        finding_id = len(findings) + 1
        for func_name, (rel_path, lineno) in defined_functions.items():
            # Check occurrences across entire workspace
            count = len(re.findall(rf"\b{re.escape(func_name)}\b", all_content))
            # If function name only appears once (its own definition), it is a potential dead code candidate
            if count <= 1:
                findings.append({
                    "finding_id": f"QUAL-DEAD-{finding_id:03d}",
                    "type": "POTENTIAL_UNUSED_FUNCTION",
                    "affected_files": [f"{rel_path}:L{lineno}"],
                    "description": f"Function '{func_name}' is defined but never referenced elsewhere in workspace.",
                    "suggested_refactoring": f"Verify if '{func_name}' is part of public API. If internal and unused, remove to reduce dead code.",
                    "expected_maintainability_benefit": "Reduces codebase surface area and maintenance overhead.",
                    "regression_risk": "MEDIUM — ensure function is not invoked dynamically.",
                    "verification_evidence": "Grep search for function name across project and run test suite."
                })
                finding_id += 1
                if len(findings) >= 8:
                    break
        return findings

    def _detect_shallow_wrappers(self, files: List[Path]) -> List[Dict[str, Any]]:
        findings = []
        finding_id = 1
        for file_path in files:
            rel_path = str(file_path.relative_to(self.workspace_path))
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"))
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        # Check if class has only 1 method that immediately delegates
                        methods = [n for n in node.body if isinstance(n, ast.FunctionDef)]
                        if len(methods) == 1 and len(methods[0].body) == 1:
                            stmt = methods[0].body[0]
                            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call):
                                findings.append({
                                    "finding_id": f"QUAL-WRAP-{finding_id:03d}",
                                    "type": "UNNECESSARY_ABSTRACTION",
                                    "affected_files": [f"{rel_path}:L{node.lineno}"],
                                    "description": f"Class '{node.name}' is a single-method pass-through wrapper.",
                                    "suggested_refactoring": "Inline or replace single-use pass-through wrapper with direct function call.",
                                    "expected_maintainability_benefit": "Eliminates redundant indirection and simplifies mental model.",
                                    "regression_risk": "LOW — straightforward inlining.",
                                    "verification_evidence": "Pass unit tests after replacing wrapper with direct invocation."
                                })
                                finding_id += 1
            except Exception:
                continue
        return findings

    def _run_llm_quality_review(self, findings: List[Dict[str, Any]]) -> str:
        prompt = (
            "You are CodePilot Code Quality & Duplication Agent. Review these findings:\n"
            f"{json.dumps(findings[:8], indent=2)}\n\n"
            "Provide high-level recommendations for refactoring and simplification. "
            "CRITICAL: Do NOT recommend adding more abstraction layers. Focus on reducing unnecessary complexity and dead code."
        )
        try:
            resp = self.llm.generate_response(
                system_prompt="You are a senior software architect specializing in clean code and simplification.",
                user_context=prompt,
                history=[]
            )
            return resp.get("thought") or resp.get("recommendation") or "Review completed."
        except Exception:
            return "Refactoring opportunities identified. Consolidate duplicated logic without adding unnecessary abstraction layers."

    def _render_markdown_report(self, report: Dict[str, Any]) -> str:
        md = [
            "# 🧹 CodePilot Code Quality & Duplication Report",
            f"**Scan Date**: {report['scan_timestamp']}  ",
            f"**Files Analyzed**: {report['files_analyzed']}  ",
            f"**Total Opportunities**: {report['findings_count']}  \n",
            "---",
            "## 1. Architectural Principle",
            f"> {report['principle']}\n",
            "## 2. Refactoring Recommendations",
            report.get("refactoring_guidance", ""),
            "\n---",
            "## 3. Detailed Findings\n"
        ]

        if not report["findings"]:
            md.append("✅ **No significant duplication or dead code detected in analyzed modules.**\n")
        else:
            for f in report["findings"]:
                md.append(f"### [{f['finding_id']}] {f['type']}")
                md.append(f"- **Affected Files**: {', '.join(f.get('affected_files', []))}")
                md.append(f"- **Description**: {f.get('description', '')}")
                md.append(f"- **Suggested Refactoring**: {f.get('suggested_refactoring', '')}")
                md.append(f"- **Maintainability Benefit**: {f.get('expected_maintainability_benefit', '')}")
                md.append(f"- **Regression Risk**: `{f.get('regression_risk', 'LOW')}`")
                md.append(f"- **Verification Evidence**: {f.get('verification_evidence', '')}\n")

        return "\n".join(md)
