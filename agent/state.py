from typing import TypedDict, Optional, List

class AgentState(TypedDict):
  repo_name: str
  pr_number: int
  pr_diff: Optional[dict]
  violations: Optional[dict]
  findings: Optional[list]
  review: Optional[str]
  verdict: Optional[str]
  slack_message_ts: Optional[str]
  status: str
  messages: List[str]
  tool_call_count: int
  error_message: Optional[str]
  tools_called: List[str]
  next_action: Optional[str]
  requires_hitl: Optional[bool]
