from agent.state import AgentState
from tools.fetch_pr_diff import fetch_pr_diff
from tools.run_static_analysis import run_static_analysis
from tools.check_security import check_security
from tools.analyze_with_llm import analyze_with_llm
from tools.post_review_comment import post_review_comment
from tools.slack_notifier import send_review_for_approval
from db.database import get_connection, release_connection
import uuid

def fetch_diff(state: AgentState) -> dict:
    """Fetch PR diff from GitHub."""
    result = fetch_pr_diff(state["repo_name"], state["pr_number"])
    if result.get("error"):
        return {"status": "FAILED", "error_message": result["message"]}
    return {
        "pr_diff": result,
        "tools_called": state["tools_called"] + ["fetch_pr_diff"],
        "tool_call_count": state["tool_call_count"] + 1,
        "messages": state["messages"] + [f"Fetched diff: {result['total_files']} files"]
    }

def static_analysis(state: AgentState) -> dict:
    """Run flake8 static analysis."""
    result = run_static_analysis(state["pr_diff"]["files"])
    if result.get("error"):
        return {"status": "FAILED", "error_message": result["message"]}
    return {
        "violations": result["violations"],
        "tools_called": state["tools_called"] + ["run_static_analysis"],
        "tool_call_count": state["tool_call_count"] + 1,
        "messages": state["messages"] + [f"Ran static analysis: {result['total_violations']} violations"]
    }

def security_check(state: AgentState) -> dict:
    result = check_security(state["pr_diff"]["files"])
    if result.get("error"):
        return {"status": "FAILED", "error_message": result["message"]}
    return {
        "findings": result.get("findings", []),
        "requires_hitl": result.get("requires_hitl", False),
        "tools_called": state["tools_called"] + ["check_security"],
        "tool_call_count": state["tool_call_count"] + 1,
        "messages": state["messages"] + [f"Ran security check: {result.get('total_findings', 0)} findings"]
    }

def llm_review(state: AgentState) -> dict:
    """Generate review with GPT-4o."""
    result = analyze_with_llm(state["pr_diff"], state["violations"], state["findings"])
    if result.get("error"):
        return {"status": "FAILED", "error_message": result["message"]}
    return {
        "review": result["review"],
        "verdict": result["verdict"],
        "tools_called": state["tools_called"] + ["analyze_with_llm"],
        "tool_call_count": state["tool_call_count"] + 1,
        "messages": state["messages"] + [f"Generated review: {result['review']}"]}
   

def notify_slack(state: AgentState) -> dict:
    """Send review to Slack for human approval."""
    run_id = str(uuid.uuid4())
    
    print(f"DEBUG notify_slack: run_id={run_id}, thread_id={state.get('thread_id')}")
    
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_reviews SET review_id = %s, review_content = %s WHERE thread_id = %s",
            (run_id, state["review"], state["thread_id"])
        )
        conn.commit()
        cursor.execute(
            "SELECT review_id, thread_id FROM pending_reviews WHERE thread_id = %s",
            (state["thread_id"],)
        )
        print(f"DEBUG notify_slack: after update = {cursor.fetchone()}")
    finally:
        release_connection(conn)
    
    result = send_review_for_approval(
        repo_name=state["repo_name"],
        pr_number=state["pr_number"],
        pr_title=state["pr_diff"]["pr_title"],
        review_content=state["review"],
        verdict=state["verdict"],
        run_id=run_id
    )
    if result.get("error"):
        return {"status": "FAILED", "error_message": result["message"]}
    return {
        "slack_message_ts": result["message_ts"],
        "tool_call_count": state["tool_call_count"] + 1,
        "messages": state["messages"] + ["Review sent to Slack for approval"]
    }

def post_review(state: AgentState) -> dict:
    """Post approved review to GitHub PR."""

    result = post_review_comment(state["repo_name"], state["pr_number"], state["review"], state["verdict"])
    if result.get("error"):
        return {"status": "FAILED", "error_message": result["message"]}
    return {
        "tool_call_count": state["tool_call_count"] + 1,
        "messages": state["messages"] + ["Review posted to GitHub PR"]
    }
   
def save_result(state: AgentState) -> dict:
    """Save completed review to PostgreSQL."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO review_results
               (repo_name, pr_number, verdict, severity_level,
                files_reviewed, github_comment_url, approved_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (
                state["repo_name"],
                state["pr_number"],
                state["verdict"],
                "HIGH" if state.get("requires_hitl") else "LOW",
                [f["filename"] for f in state["pr_diff"]["files"]],
                "pending",
                "slack_user"
            )
        )
        conn.commit()
        return {
            "status": "COMPLETED",
            "messages": state["messages"] + ["Review saved to database"]
        }
    except Exception as e:
        conn.rollback()
        return {"status": "FAILED", "error_message": str(e)}
    finally:
        release_connection(conn)

def emergency_stop(state: AgentState) -> dict:
    """Handle failures and max tool call limit."""
    return {
        "status": "FAILED",
        "error_message": f"Agent stopped: tool_call_count={state['tool_call_count']}",
        "messages": state["messages"] + ["Emergency stop triggered"]
    }