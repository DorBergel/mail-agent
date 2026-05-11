

CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    applied_date DATE NOT NULL DEFAULT CURRENT_DATE,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_email VARCHAR(255),
    notes TEXT,
    UNIQUE(company, role)
);


CREATE TABLE IF NOT EXISTS processed_emails (
    id SERIAL PRIMARY KEY,
    email_id VARCHAR(255) NOT NULL UNIQUE,
    processed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    result VARCHAR(20) DEFAULT 'skipped'
);

-- Migration for existing deployments:
-- ALTER TABLE processed_emails ADD COLUMN IF NOT EXISTS result VARCHAR(20) DEFAULT 'skipped';