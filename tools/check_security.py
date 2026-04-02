import os
import subprocess
import tempfile
import json
from dotenv import load_dotenv

load_dotenv()

def check_security(files: list) -> dict:
    """
    Run bandit security scanner on Python files from the PR diff.
    Returns findings with severity levels.
    """
    all_findings = []
    python_files = [f for f in files if f["filename"].endswith(".py")]

    if not python_files:
        return {
            "error": False,
            "message": "No Python files to scan",
            "findings": [],
            "has_high_severity": False,
            "requires_hitl": False
        }

    for file in python_files:
        filename = file["filename"]
        patch = file["patch"]

        added_lines = [
                line[1:]  # remove the leading +
                for line in patch.split('\n')
                if line.startswith('+') and not line.startswith('+++')
        ]
        code_string = '\n'.join(added_lines)

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(code_string)
            tmp_path = tmp.name

        result = subprocess.run(
            ["bandit", "-f", "json", "-q", tmp_path],
            capture_output=True,
            text=True
        )   

        if result.stdout.strip():
            try:
                data = json.loads(result.stdout)
                for issue in data.get("results", []):
                    all_findings.append({
                        "filename": filename,
                        "line": issue["line_number"],
                        "issue": issue["issue_text"],
                        "severity": issue["issue_severity"],
                        "confidence": issue["issue_confidence"]
                    })
            except json.JSONDecodeError:
                pass

        os.remove(tmp_path)

    has_high = any(f["severity"] == "HIGH" for f in all_findings)

    return {
        "error": False,
        "findings": all_findings,
        "total_findings": len(all_findings),
        "has_high_severity": has_high,
        "requires_hitl": has_high
    }