import os
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def post_review_comment(
    repo_name: str,
    pr_number: int,
    review_content: str,
    verdict: str
) -> dict:
    """
    Post a formal review on a GitHub PR.
    verdict must be APPROVE or REQUEST_CHANGES.
    """
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN environment variable not set")

    try:
        g = Github(auth=Auth.Token(GITHUB_TOKEN))
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        if verdict == "APPROVE":
            event = "APPROVE"
        elif verdict == "REQUEST_CHANGES":
            event = "REQUEST_CHANGES"
        else:
            event = "COMMENT"
    
        review = pr.create_review(body=review_content, event=event)

        return {
            "error": False,
            "comment_url": review.html_url,
            "verdict": verdict,
            "pr_number": pr_number,
            "repo_name": repo_name
        }

    except Exception as e:
        return {"error": True, "message": f"Failed to post review: {str(e)}"}
