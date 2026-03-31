**1\. Problem Statement** 

Software engineers at companies of all sizes spend 3-4 hours per week on manual code review \- time taken away from building. A senior engineer reviewing a 500-line PR spends 1-2 hours , at a cost of 300$ per PR. A team merging 10 PRs per week spends $3,000 per week just on review time. The process is inconsistent \- when 2 developers review the same code each might come up with different issues which can be inconsistent with each other. Critical issues like security vulnerabilities are frequently missed because reviewers are human and fatigued. Current automated tools like linters catch style issues but cannot reason why this is an issue. CodeSense changes this by integrating a structured review comment posted directly on the PR with severity ratings, specific line references, and suggested fixes — in under 60 seconds instead of 2 hours.

**2\. Why an agent and not a pipeline** 

Reason 1 — Dynamic control flow:

"When CodeSense analyzes a PR diff and discovers a function being modified that is called in 12 other files, it must decide to fetch those dependent files and check for breaking changes. A pipeline cannot do this because it will just analyse that one change and post review . In code review this matters because a breaking change in a widely-used function can cause production failures that would have been caught if the reviewer had checked all dependent call sites.”

Reason 2 — Intelligent error handling:

"When the fetch\_pr\_diff tool returns a binary file or a minified JS file with 50,000 characters on one line, the agent flags it as unanalyzable, skips LLM analysis, posts a note on the PR saying the file couldn't be reviewed. A pipeline cannot do this because it will review it anyways and return garbage or might just break. This matters because we need to know where the system is not working pointing to the exact issue."

Reason 3 — Variable task depth:

"A 10-line PR fixing a typo requires 1 tool call. A 500-line PR refactoring a core authentication module requires 10+ because more files, more dependencies, more security checks. A pipeline cannot handle this because it doesnt have the ability to analyse dependencies . This matters because over-reviewing simple PRs wastes cost, under-reviewing complex ones misses bugs."

**3\. Tool Registry — CodeSense needs these five tools:**

Tool name: fetch\_pr\_diff  
What it does: Fetches the unified diff of all changed files   
              from a GitHub PR using the GitHub API  
API/service used: GitHub REST API (PyGithub library)  
Output format: Raw unified diff text  lines starting with   
               \+ are additions, \- are deletions  
What the agent does with the output: Passes the diff to   
               run\_static\_analysis and analyze\_with\_llm  
What happens if it fails or returns garbage: If diff is   
               empty (only images or docs changed), log   
               SKIP\_REVIEW and exit. If API returns 404,   
               return error to user. If diff exceeds 10,000   
               lines, flag as TOO\_LARGE and review only   
               the first 500 lines.

Tool name: run\_static\_analysis  
What it does: Runs flake8 and pylint on all changed Python   
              files to detect style violations and complexity  
API/service used: flake8 and pylint (installed as Python packages)  
Output format: Plain text list of violations, one per line:  
               file.py:23:4: E501 line too long (120 \> 79 chars)  
What the agent does with the output: Passes violations list   
               to analyze\_with\_llm as additional context   
               alongside the raw diff  
What happens if it fails or returns garbage: If flake8   
               crashes on a file due to syntax error, log   
               STATIC\_ANALYSIS\_FAILED for that file, skip   
               it, and continue with remaining files.

Tool name: analyze\_with\_llm  
What it does: Sends the PR diff and static analysis results   
              to GPT-4o to generate a structured human-readable   
              review with severity ratings and suggested fixes  
API/service used: OpenAI API (GPT-4o)  
Output format: Structured markdown with sections:  
               \- Summary, Critical Issues, Warnings,   
               Suggestions, Verdict (Approve/Request Changes)  
What the agent does with the output: Passes the review   
               to post\_review\_comment  
What happens if it fails or returns garbage: Retry once.   
               If retry fails, post a minimal comment saying   
               automated review failed and log LLM\_FAILURE   
               in the run trace.

Tool name: post\_review\_comment  
What it does: Posts the generated review as a PR comment   
              on GitHub using the GitHub API  
API/service used: GitHub REST API (PyGithub library)  
Output format: GitHub PR review object (JSON confirmation)  
What the agent does with the output: This is the terminal   
               tool — logs the comment URL and marks run   
               as COMPLETED  
What happens if it fails: Retry once. If retry fails,   
               save the review to a file and log   
               POST\_FAILED so the review is not lost.

Tool name: check\_security  
What it does: Scans changed files for hardcoded secrets,   
              API keys, and known vulnerability patterns  
API/service used: bandit (Python security linter) \+   
                  detect-secrets library  
Output format: JSON list of findings with severity:  
               \[{"file": "app.py", "line": 12,   
               "issue": "Hardcoded password",   
               "severity": "HIGH"}\]  
What the agent does with the output: If HIGH severity   
               findings exist, flags the PR as SECURITY\_RISK   
               and includes findings prominently in the review  
What happens if it fails or returns garbage: Log   
               SECURITY\_SCAN\_FAILED, proceed with review   
               but add disclaimer that security scan   
               could not be completed.

**4\. Human-in-the-loop checkpoints** 

Checkpoint name: security escalation   
When it occurs: when check\_security returns HIGH   
What the human reviews: The human reviews the comment and code change  
Why the agent can't handle this alone: The agent knows what to do technically \- post the finding. The problem is it can't judge the business context. A hardcoded API key in a test file is different from one in a production config. Only a human knows which is which.  
What the agent does while waiting: the agent stores the state   
What happens if human approves: it post the review comment on github pr  
What happens if human rejects: The PR still exists — the human might choose to write their own comment or handle it offline.

Checkpoint name: final review approval  
When it occurs: after analyze\_with\_llm generates review. This checkpoint only fires when the LLM verdict is Request Changes or when critical issues are found. If the verdict is Approve with no critical issues, CodeSense posts automatically  
What the human reviews: the review comment   
Why the agent can't handle this alone: The LLM cannot assess whether a review comment is appropriate for the team's context, coding standards, or PR sensitivity. A human must verify the tone, accuracy, and relevance before it's posted publicly.  
What the agent does while waiting: it saves the state and waits for human to respond  
What happens if human approves: the review comment is posted on github  pr  
What happens if human rejects: the review is not posted

**5\. Success Metrics**

| Metric | Target | Why it matters |
| :---- | :---- | :---- |
| Task completion rate | \>95% of PRs reviewed successfully | Measures reliability |
| Latency per review | \<60 seconds | Measures usability |
| Cost per review | \<$0.10 | Measures viability |
| False positive rate | \<10% of flagged issues are incorrect | Measures accuracy  |
| Developer action rate | \>80%  | Measures the changes made based on comments |
| Critical Issue Miss rate  | \<5% | Measures the percentage of real issues that wasn't flagged |

