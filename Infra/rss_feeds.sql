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

CREATE TABLE vendors (
    id SERIAL PRIMARY KEY,
    vendor TEXT,
    emails TEXT,
    date_subscribed TIMESTAMP
)

CREATE UNIQUE INDEX idx_vendor_email ON vendors (vendor, emails);

-- This should be optimized (TODO)
