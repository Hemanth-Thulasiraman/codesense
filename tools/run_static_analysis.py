import os
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

def run_static_analysis(files: list) -> dict:
    """
    Run flake8 on Python files from the PR diff.
    Takes the files list from fetch_pr_diff output.
    Returns violations grouped by filename.
    """
    violations = {}
    python_files = [f for f in files if f["filename"].endswith(".py")]

    if not python_files:
        return {
            "error": False,
            "message": "No Python files to analyze",
            "violations": {},
            "total_violations": 0
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
            ["flake8", "--max-line-length=100", tmp_path],
            capture_output=True,
            text=True
        )

        output = result.stdout.replace(tmp_path, filename)
        violations[filename] = [
            line for line in output.split('\n') if line.strip()
        ]

        os.remove(tmp_path)

    total = sum(len(v) for v in violations.values())
    return {
        "error": False,
        "violations": violations,
        "total_violations": total,
        "files_analyzed": len(python_files)
    }
