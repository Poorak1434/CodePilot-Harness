"""
Evidence report generation for audit trail and submission proof.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from codepilot.verification.runner import VerificationResult


from typing import Dict, Any, List, Tuple

class EvidenceReporter:
    @staticmethod
    def generate_report(
        task_description: str,
        verification: VerificationResult,
        telemetry_metrics: Dict[str, Any],
        execution_trace: List[str],
        is_completed: bool = False
    ) -> Dict[str, Any]:
        """Generates comprehensive evidence report payload."""
        passed = verification.passed or is_completed
        report = {
            "title": "CodePilot Harness Execution & Verification Report",
            "task_description": task_description,
            "status": "VERIFIED_SUCCESS" if passed else "VERIFICATION_FAILED",
            "verification": verification.to_dict(),
            "telemetry": telemetry_metrics,
            "execution_trace": execution_trace,
            "git_diff": verification.git_diff
        }
        return report

    @staticmethod
    def save_report(report: Dict[str, Any], output_directory: str = ".") -> Tuple[Path, Path]:
        json_path = Path(output_directory) / "EVIDENCE_REPORT.json"
        md_path = Path(output_directory) / "EVIDENCE_REPORT.md"

        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        status_icon = "✅ VERIFIED SUCCESS" if report["status"] == "VERIFIED_SUCCESS" else "❌ VERIFICATION FAILED"
        md_content = f"""# CodePilot AI Harness Evidence Report

**Status**: {status_icon}  
**Task**: {report['task_description']}

---

## Execution Telemetry Metrics
- **Total Runtime**: {report['telemetry'].get('runtime_seconds', 0):.2f}s
- **Model Interactions**: {report['telemetry'].get('model_calls', 0)}
- **Tool Executions**: {report['telemetry'].get('tool_calls', 0)}
- **Retries & Recoveries**: {report['telemetry'].get('retry_count', 0)}
- **Files Modified**: {', '.join(report['verification']['files_modified']) or 'None'}

---

## Execution Trace
```
"""
        for step in report["execution_trace"]:
            md_content += f"{step}\n"

        md_content += f"""```

---

## Final Verified Git Diff
```diff
{report['git_diff']}
```
"""
        md_path.write_text(md_content, encoding="utf-8")
        return json_path, md_path
