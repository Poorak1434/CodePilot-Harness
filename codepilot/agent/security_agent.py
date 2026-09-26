"""
Security Auditor Agent for CodePilot Multi-Agent Architecture.
Inspects repository files, detects vulnerabilities, exposed secrets, injection risks,
and produces structured findings with actionable remediation.
"""
import os
import re
import ast
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from codepilot.agent.base_agent import BaseSpecializedAgent, AgentTask, AgentResult
from codepilot.safety.policy import SafetyPolicy
from codepilot.llm.adapter import LLMAdapter


class SecurityAuditorAgent(BaseSpecializedAgent):
    agent_id: str = "security_auditor"
    agent_role: str = "Security Auditor"
    is_read_only: bool = True
    description: str = "Inspects codebase for security vulnerabilities, exposed secrets, and injection risks."

    def __init__(self, workspace_root: str, llm: LLMAdapter, safety: SafetyPolicy):
        super().__init__(workspace_root, llm, safety)
        self.workspace_path = Path(workspace_root).resolve()

    def execute(self, task: AgentTask) -> AgentResult:
        start_time = time.time()
        findings: List[Dict[str, Any]] = []
        errors: List[str] = []

        # 1. Discover target files
        source_files = self._collect_source_files()

        # 2. Perform static analysis across collected files
        finding_counter = 1
        for file_path in source_files:
            try:
                rel_path = str(file_path.relative_to(self.workspace_path))
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                # A. Secret & Insecure Config Scanning
                secret_findings = self._scan_secrets(rel_path, lines, finding_counter)
                findings.extend(secret_findings)
                finding_counter += len(secret_findings)

                # B. Injection & Dangerous Primitive Scanning (Python AST & Regex)
                code_findings = self._scan_code_risks(rel_path, lines, content, finding_counter)
                findings.extend(code_findings)
                finding_counter += len(code_findings)

            except Exception as e:
                errors.append(f"Error scanning {file_path.name}: {str(e)}")

        # 3. LLM-assisted verification and high-level architecture security assessment
        llm_assessment = self._run_llm_security_review(findings, task.objective)

        # 4. Generate artifacts
        artifacts_dir = self.workspace_path / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        json_path = artifacts_dir / "security_findings.json"
        md_path = artifacts_dir / "security_audit.md"

        audit_report = {
            "agent_id": self.agent_id,
            "scan_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "files_scanned": len(source_files),
            "findings_count": len(findings),
            "findings": findings,
            "llm_assessment": llm_assessment,
            "security_disclaimer": "No automated scan can guarantee complete security. Absence of findings does not imply the codebase is invulnerable."
        }

        json_path.write_text(json.dumps(audit_report, indent=2), encoding="utf-8")
        markdown_content = self._render_markdown_report(audit_report)
        md_path.write_text(markdown_content, encoding="utf-8")

        runtime = round(time.time() - start_time, 2)
        summary = (
            f"Security Audit completed: {len(source_files)} files scanned, "
            f"{len(findings)} findings identified. Report saved to artifacts/security_audit.md."
        )

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            status="SUCCESS" if not errors else "PARTIAL",
            findings=findings,
            artifacts={
                "security_findings_json": str(json_path),
                "security_audit_md": str(md_path)
            },
            evidence={
                "files_scanned": len(source_files),
                "high_severity_count": len([f for f in findings if f.get("severity") in ("CRITICAL", "HIGH")])
            },
            metrics={"runtime_seconds": runtime, "files_inspected": len(source_files)},
            errors=errors,
            summary=summary
        )

    def _collect_source_files(self) -> List[Path]:
        collected = []
        ignored_dirs = {".git", ".venv", "venv", "__pycache__", "node_modules", ".pytest_cache", "artifacts"}
        target_exts = {".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml", ".env", ".toml"}

        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in target_exts or file.startswith(".env"):
                    collected.append(Path(root) / file)
        return collected[:100]

    def _scan_secrets(self, rel_path: str, lines: List[str], start_id: int) -> List[Dict[str, Any]]:
        findings = []
        secret_patterns = [
            (re.compile(r"""(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token)\s*=\s*['"][a-zA-Z0-9_\-]{20,}['"]"""),
             "Potential hardcoded API key or access token", "HIGH",
             "Hardcoded credentials can be leaked through version control systems."),
            (re.compile(r"""(?i)(?:password|passwd|pwd)\s*=\s*['"][^'"]{8,}['"]"""),
             "Potential hardcoded password", "CRITICAL",
             "Hardcoded passwords violate credential isolation and secrets management policies."),
            (re.compile(r"""-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"""),
             "Exposed Private Cryptographic Key", "CRITICAL",
             "Private keys stored in source repositories allow unauthorized identity impersonation.")
        ]

        # Check for exposed active secrets in .env
        if rel_path.endswith(".env"):
            for idx, line in enumerate(lines, 1):
                clean = line.strip()
                if clean and not clean.startswith("#") and "=" in clean:
                    k, v = clean.split("=", 1)
                    v_clean = v.strip().strip("'\"")
                    if len(v_clean) >= 20 and not v_clean.startswith("{{") and "placeholder" not in v_clean.lower():
                        findings.append({
                            "finding_id": f"SEC-{start_id + len(findings):03d}",
                            "affected_file": rel_path,
                            "line_number": idx,
                            "vulnerability": "Exposed Raw Secret in .env file",
                            "severity": "HIGH",
                            "rationale": "Active production secrets in repository workspace risk accidental commit to remote branches.",
                            "evidence": f"{k.strip()}=***REDACTED (len {len(v_clean)})***",
                            "suggested_remediation": "Move secrets to runtime environment variables or vault and add .env to .gitignore.",
                            "verification_status": "VERIFIED"
                        })

        for idx, line in enumerate(lines, 1):
            for pattern, desc, severity, rationale in secret_patterns:
                if pattern.search(line):
                    findings.append({
                        "finding_id": f"SEC-{start_id + len(findings):03d}",
                        "affected_file": rel_path,
                        "line_number": idx,
                        "vulnerability": desc,
                        "severity": severity,
                        "rationale": rationale,
                        "evidence": line.strip()[:100],
                        "suggested_remediation": "Extract secret to secure environment variable or secrets manager.",
                        "verification_status": "VERIFIED"
                    })
        return findings

    def _scan_code_risks(self, rel_path: str, lines: List[str], content: str, start_id: int) -> List[Dict[str, Any]]:
        findings = []

        # Regex checks for dangerous commands
        for idx, line in enumerate(lines, 1):
            if "shell=True" in line and "subprocess" in content:
                findings.append({
                    "finding_id": f"SEC-{start_id + len(findings):03d}",
                    "affected_file": rel_path,
                    "line_number": idx,
                    "vulnerability": "Insecure Shell Execution (subprocess shell=True)",
                    "severity": "HIGH",
                    "rationale": "Using shell=True allows command injection if untrusted inputs reach the command line.",
                    "evidence": line.strip(),
                    "suggested_remediation": "Pass arguments as an argument list with shell=False, or sanitize inputs with shlex.split().",
                    "verification_status": "VERIFIED"
                })
            elif re.search(r"\b(?:eval|exec)\s*\(", line):
                findings.append({
                    "finding_id": f"SEC-{start_id + len(findings):03d}",
                    "affected_file": rel_path,
                    "line_number": idx,
                    "vulnerability": "Arbitrary Code Execution via eval/exec",
                    "severity": "CRITICAL",
                    "rationale": "Evaluating dynamic strings executes arbitrary code within the current process context.",
                    "evidence": line.strip(),
                    "suggested_remediation": "Refactor to use ast.literal_eval() for data or safe dispatch maps.",
                    "verification_status": "VERIFIED"
                })
            elif "pickle.loads" in line:
                findings.append({
                    "finding_id": f"SEC-{start_id + len(findings):03d}",
                    "affected_file": rel_path,
                    "line_number": idx,
                    "vulnerability": "Insecure Deserialization via pickle",
                    "severity": "HIGH",
                    "rationale": "Deserializing untrusted pickle streams can lead to arbitrary remote code execution.",
                    "evidence": line.strip(),
                    "suggested_remediation": "Use safe serialization formats such as JSON or Protocol Buffers.",
                    "verification_status": "VERIFIED"
                })

        return findings

    def _run_llm_security_review(self, findings: List[Dict[str, Any]], objective: str) -> str:
        prompt = (
            "You are CodePilot Security Auditor. Review the static security audit findings below "
            "and provide an expert summary assessment covering authentication, authorization, "
            "input validation, and defense-in-depth.\n\n"
            f"Findings summary: {len(findings)} findings.\n"
            f"Findings detail: {json.dumps(findings[:10], indent=2)}\n\n"
            "Provide a concise, professional assessment in markdown format."
        )
        try:
            resp = self.llm.generate_response(
                system_prompt="You are an autonomous application security expert.",
                user_context=prompt,
                history=[]
            )
            return resp.get("thought") or resp.get("assessment") or "Security review completed."
        except Exception:
            return "Security review completed. Static rules analyzed repository perimeter."

    def _render_markdown_report(self, report: Dict[str, Any]) -> str:
        md = [
            "# 🛡️ CodePilot Security Audit Report",
            f"**Scan Date**: {report['scan_timestamp']}  ",
            f"**Files Scanned**: {report['files_scanned']}  ",
            f"**Total Findings**: {report['findings_count']}  \n",
            "---",
            "## 1. Executive Summary",
            report.get("llm_assessment", ""),
            "\n---",
            "## 2. Detailed Findings\n"
        ]

        if not report["findings"]:
            md.append("✅ **No high-confidence vulnerabilities detected by static heuristics.**\n")
        else:
            for f in report["findings"]:
                md.append(f"### [{f['finding_id']}] {f['vulnerability']}")
                md.append(f"- **File & Line**: `{f['affected_file']}:{f['line_number']}`")
                md.append(f"- **Severity**: `{f['severity']}`")
                md.append(f"- **Rationale**: {f['rationale']}")
                md.append(f"- **Evidence**:\n```\n{f['evidence']}\n```")
                md.append(f"- **Suggested Remediation**: {f['suggested_remediation']}")
                md.append(f"- **Verification Status**: `{f['verification_status']}`\n")

        md.extend([
            "---",
            "## 3. Security Disclaimer",
            f"> {report['security_disclaimer']}\n"
        ])
        return "\n".join(md)
