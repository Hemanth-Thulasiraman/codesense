#import statements
import os
from github import Github
from dotenv import load_dotenv
from github import Auth

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def fetch_pr_diff(repo_name: str, pr_number: int) -> dict:
    """
    Fetch the unified diff of all changed files in a PR.
    Returns a dict with file diffs or an error dict.
    """
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        total = pr.additions + pr.deletions
        if total > 10000 :
            return {"error": True, "message": "PR too large", "flag": "TOO_LARGE"}

        files = pr.get_files()
        diffs = []

        for file in files:
            if file.patch == None:
                 continue
            diffs.append({
                 "filename": file.filename,
                 "status": file.status,  
                 "additions": file.additions,
                 "deletions": file.deletions,
                 "patch": file.patch
             })

        if not diffs:
            return {"error": True, "message": "No reviewable files found", "flag": "SKIP_REVIEW"}
        

        return {
            "error": False,
            "repo_name": repo_name,
            "pr_number": pr_number,
            "pr_title": pr.title,
            "pr_author": pr.user.login,
            "files": diffs,
            "total_files": len(diffs)
        }

    except Exception as e:
        return {"error": True, "message": f"Failed to fetch PR diff: {str(e)}"}
