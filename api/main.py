import os
import json
import hmac
import hashlib
import uuid
from urllib.parse import unquote_plus
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.types import Command
from agent.graph import graph
from db.database import get_connection, release_connection
from tools.post_review_comment import post_review_comment
from dotenv import load_dotenv

load_dotenv()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

app = FastAPI(title="CodeSense API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_github_signature(payload: bytes, signature: str) -> bool:
    if not GITHUB_WEBHOOK_SECRET:
        return True
    expected = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CodeSense API"}

@app.post("/webhook")
async def handle_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if not verify_github_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    data = json.loads(payload)

    if data.get("action") not in ["opened", "reopened"]:
        return {"status": "ignored", "reason": "not a PR open event"}

    repo_name = data["repository"]["full_name"]
    pr_number = data["pull_request"]["number"]
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "repo_name": repo_name,
        "pr_number": pr_number,
        "thread_id": thread_id,
        "status": "PENDING",
        "messages": [],
        "tool_call_count": 0,
        "error_message": None,
        "tools_called": [],
        "pr_diff": None,
        "violations": None,
        "findings": None,
        "review": None,
        "verdict": None,
        "slack_message_ts": None,
        "requires_hitl": None,
        "next_action": None
    }

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pending_reviews (thread_id, repo_name, pr_number, approval_status) VALUES (%s, %s, %s, 'PENDING')",
        (thread_id, repo_name, pr_number)
    )
    conn.commit()
    release_connection(conn)

    result = graph.invoke(initial_state, config)
    print(f"DEBUG webhook: status={result.get('status')}, messages={result.get('messages')}")

    if result.get("status") == "FAILED":
        return {"status": "failed", "error": result.get("error_message")}
    return {"status": "processing", "repo": repo_name, "pr": pr_number}

@app.post("/slack/actions")
async def handle_slack_action(request: Request):
    body = await request.body()
    body_str = body.decode()
    payload_str = unquote_plus(body_str.replace("payload=", ""))
    payload = json.loads(payload_str)

    action = payload["actions"][0]
    action_id = action["action_id"]
    run_id = action["value"]
    user = payload["user"]["username"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT thread_id, repo_name, pr_number FROM pending_reviews WHERE review_id = %s",
        (run_id,)
    )
    row = cursor.fetchone()
    release_connection(conn)

    if not row:
        return {"error": "Run not found", "run_id": run_id}

    thread_id, repo_name, pr_number = row

    if action_id == "approve_review":
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT review_content FROM pending_reviews WHERE review_id = %s",
            (run_id,)
        )
        review_row = cursor.fetchone()
        release_connection(conn)

        if review_row and review_row[0]:
            post_review_comment(
                repo_name=repo_name,
                pr_number=pr_number,
                review_content=review_row[0],
                verdict="REQUEST_CHANGES"
            )
        result = post_review_comment(
            repo_name=repo_name,
            pr_number=pr_number,
            review_content=review_row[0],
            verdict="COMMENT"
        )
        print(f"DEBUG post_review result: {result}")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_reviews SET approval_status = 'APPROVED' WHERE thread_id = %s",
            (thread_id,)
        )
        conn.commit()
        release_connection(conn)
        return {"text": f"Review approved by {user} — posted to GitHub"}

    else:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE pending_reviews SET approval_status = 'REJECTED' WHERE thread_id = %s",
            (thread_id,)
        )
        conn.commit()
        release_connection(conn)
        return {"text": f"Review rejected by {user}"}