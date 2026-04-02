import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()
MAX_DIFF_CHARS = 20000

def analyze_with_llm(
    pr_diff: dict,
    violations: dict,
    findings: list
) -> dict:
    """
    Send PR diff, static analysis, and security findings to GPT-4o.
    Returns a structured review.
    """
    try:
        repo_name = pr_diff["repo_name"]
        pr_number = pr_diff["pr_number"]
        pr_title = pr_diff["pr_title"]
        pr_author = pr_diff["pr_author"]

        diff_parts = []
        for file in pr_diff["files"]:
            filename = file["filename"]
            status = file["status"]
            additions = file["additions"]
            deletions = file["deletions"]
            patch = file["patch"]
            diff_parts.append(
                f"File: {filename} ({status}, +{additions} -{deletions})\n{patch}\n"
            )

        diff_summary = '\n'.join(diff_parts)

        # Truncate if too long
        if len(diff_summary) > MAX_DIFF_CHARS:
            diff_summary = diff_summary[:MAX_DIFF_CHARS] + "\n... [truncated]"

        if not violations:
            violations_summary = "No style violations found"
        else:
            parts = []
            for filename,violation_list in violations.items():
                parts.append(f"{filename}:\n" + "\n".join(violation_list))
            violations_summary = "\n\n".join(parts)

        if not findings:
            security_summary = "No security issues found"
        else:
            parts = []
            for finding in findings:
                severity = finding["severity"]
                filename = finding["filename"]
                line = finding["line"]
                issue = finding["issue"]
                parts.append(f"[{severity}] {filename}:{line} — {issue}")
            security_summary = "\n\n".join(parts)

        prompt = f"""You are a senior software engineer conducting a code review.

            PR: {pr_title} by {pr_author} on {repo_name}

            ## Code Changes
            {diff_summary}

            ## Static Analysis Results
            {violations_summary}

            ## Security Scan Results
            {security_summary}

            Produce a structured review with these sections:
            ## Summary
            ## Critical Issues (if any)
            ## Style & Quality Issues (if any)
            ## Security Findings (if any)
            ## Suggestions
            ## Verdict: [APPROVE / REQUEST_CHANGES]

            Be specific. Cite line numbers. Be concise."""

        response = client.chat.completions.create(
        model="gpt-4o" , messages=[{"role": "user", "content": prompt}], temperature=0.5
        )
        brief_text = response.choices[0].message.content.strip()

        return {
            "error": False,
            "repo_name": repo_name, "pr_number": pr_number, "review": brief_text, "verdict": "REQUEST_CHANGES" if findings or violations else "APPROVE"
        }
    except Exception as e:
        return {"error": True, "message": f"LLM analysis failed: {str(e)}"}

if __name__ == "__main__":
    from tools.fetch_pr_diff import fetch_pr_diff
    from tools.run_static_analysis import run_static_analysis
    from tools.check_security import check_security
    
    pr_diff = fetch_pr_diff("Hemanth-Thulasiraman/FinSight", 1)
    violations = run_static_analysis(pr_diff["files"])
    security = check_security(pr_diff["files"])
    
    review = analyze_with_llm(
        pr_diff,
        violations["violations"],
        security["findings"]
    )
    print(f"Verdict: {review['verdict']}")
    print(review['review'])