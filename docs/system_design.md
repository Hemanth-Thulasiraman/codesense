Architecture Description

1. Entry Point Layer

The Entry Point Layer is responsible for receiving incoming GitHub webhook events when a pull request is opened or updated. This layer is implemented with FastAPI, which exposes lightweight HTTP endpoints to accept webhook POST requests securely and efficiently. Once a webhook is received, this layer validates the request, extracts the relevant event payload, and passes the structured information to the Webhook Processing Layer. In this way, it acts as the system’s external interface, connecting GitHub to the rest of the CodeSense pipeline.

2. Webhook Processing Layer

The Webhook Processing Layer parses and normalizes the incoming GitHub event data so it can be used by downstream components. Using PyGithub, this layer interacts with the GitHub REST API to fetch additional repository context such as changed files, commit metadata, pull request details, and code diffs when the webhook payload alone is insufficient. It prepares the information required for analysis and routes it into the Agent Layer for reasoning and decision-making. This layer therefore serves as the bridge between raw GitHub events and the intelligent review workflow.

3. Agent Layer

The Agent Layer is the core reasoning engine of CodeSense. Built with LangGraph and orchestrated using a ReAct loop, the agent dynamically decides which actions to take in response to a code event, such as invoking static analysis tools, retrieving repository context, interpreting results, and generating a review recommendation. The underlying model, GPT-4o, allows the agent to reason across both code changes and tool outputs, producing more context-aware feedback than a fixed pipeline. This layer connects upward to the processed webhook data and downward to analysis tools, storage, and human approval workflows.

4. HITL Layer (Slack)

The Human-in-the-Loop layer introduces a review checkpoint before final actions are taken on sensitive or high-impact recommendations. After the agent produces a candidate review, CodeSense sends a structured preview to reviewers through the Slack API, allowing a human to approve or reject the recommendation. During this waiting period, pending review state is stored in PostgreSQL so the system can persist decisions reliably across asynchronous interactions. This layer connects the autonomous agent workflow with human oversight, ensuring that important review actions remain controlled and auditable.

5. Output Layer

The Output Layer is responsible for turning approved agent decisions into concrete results that are visible in the development workflow. After approval, CodeSense can post comments, recommendations, or review summaries back to GitHub, making the system’s analysis directly accessible inside pull requests and repository discussions. This layer consumes decisions from the Agent and HITL layers, then uses GitHub integration services to publish the final output. As a result, it closes the loop by feeding actionable review intelligence back into the software development process.

6. Observability Layer

The Observability Layer provides monitoring, tracing, and debugging support across the full CodeSense workflow. Using LangSmith, the system records agent execution paths, tool calls, intermediate reasoning steps, and final outputs so developers can inspect how decisions were made and identify failures or inefficiencies. This layer connects across every other part of the system, from webhook ingestion to final output delivery, offering end-to-end visibility into runtime behavior. It is critical for evaluation, iteration, and maintaining trust in an agentic code review platform.
