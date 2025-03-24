CREATE TABLE rss_feeds (
    id SERIAL PRIMARY KEY,
    title TEXT,
    vendor TEXT,
    product TEXT,
    exploits TEXT,
    url TEXT UNIQUE,
    published TIMESTAMP,
    summary TEXT
);

CREATE INDEX idx_published ON rss_feeds (published);
