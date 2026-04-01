-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table 1: pending_reviews
CREATE TABLE IF NOT EXISTS pending_reviews (
    review_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    thread_id VARCHAR NOT NULL,
    repo_name VARCHAR NOT NULL,
    pr_number INT NOT NULL,
    pr_diff TEXT,
    review_content TEXT,
    slack_message_ts VARCHAR,
    approval_status VARCHAR NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Table 2: review_results
CREATE TABLE IF NOT EXISTS review_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID NOT NULL REFERENCES pending_reviews(review_id) ON DELETE RESTRICT,
    repo_name VARCHAR NOT NULL,
    pr_number INT NOT NULL,
    verdict VARCHAR NOT NULL,
    severity_level VARCHAR NOT NULL,
    files_reviewed TEXT[] NOT NULL, 
    github_comment_url VARCHAR NOT NULL, 
    approved_by VARCHAR NOT NULL, 
    created_at TIMESTAMP NOT NULL DEFAULT NOW()

);

-- Table 3: run_log
CREATE TABLE IF NOT EXISTS run_log (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status VARCHAR NOT NULL,    
    number_of_tool_calls INT,
    time_elapsed FLOAT ,
    cost FLOAT ,
    error_message VARCHAR ,
    repo_name VARCHAR NOT NULL,
    pr_number INT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
