import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")

def send_review_for_approval(
    repo_name: str,
    pr_number: int,
    pr_title: str,
    review_content: str,
    verdict: str,
    run_id: str
) -> dict:
    """
    Send review preview to Slack with Approve/Reject buttons.
    Returns the Slack message timestamp for later updates.
    """
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        raise ValueError("SLACK_BOT_TOKEN or SLACK_CHANNEL_ID not set")

    client = WebClient(token=SLACK_BOT_TOKEN)

    # Truncate review for Slack preview — max 2000 chars
    preview = review_content[:2000] + "..." if len(review_content) > 2000 else review_content

    # Verdict emoji
    verdict_emoji = "✅" if verdict == "APPROVE" else "⚠️"

    try:
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"CodeSense Review Ready {verdict_emoji}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*PR:* <https://github.com/{repo_name}/pull/{pr_number}|{pr_title}>\n*Repo:* {repo_name}\n*Verdict:* {verdict}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Review Preview:*\n```{preview}```"
                    }
                },
                {
                    "type": "actions",
                    "block_id": f"review_actions_{run_id}",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "✅ Approve & Post"},
                            "style": "primary",
                            "action_id": "approve_review",
                            "value": run_id
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "❌ Reject"},
                            "style": "danger",
                            "action_id": "reject_review",
                            "value": run_id
                        }
                    ]
                }
            ],
            text=f"CodeSense review ready for {repo_name} PR #{pr_number}"
        )

        return {
            "error": False,
            "message_ts": response["ts"],
            "channel": SLACK_CHANNEL_ID
        }

    except SlackApiError as e:
        return {"error": True, "message": f"Slack error: {e.response['error']}"}

def update_message_after_decision(
    message_ts: str,
    decision: str,
    decided_by: str
) -> dict:
    """
    Update the Slack message after human approves or rejects.
    Replaces buttons with a status message.
    """
    client = WebClient(token=SLACK_BOT_TOKEN)
    status = "✅ Approved and posted to GitHub" if decision == "APPROVE" else "❌ Rejected — not posted"

    try:
        client.chat_update(
            channel=SLACK_CHANNEL_ID,
            ts=message_ts,
            text=f"{status} by {decided_by}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{status} by *{decided_by}*"
                    }
                }
            ]
        )
        return {"error": False, "status": status}

    except SlackApiError as e:
        return {"error": True, "message": f"Slack update error: {e.response['error']}"}
