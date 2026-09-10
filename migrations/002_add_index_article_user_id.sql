-- Migration: Add index on user_id in article table
-- Date: 2026-07-05
-- Description: Add index on user_id column for faster queries

CREATE INDEX ix_article_user_id ON article (user_id);
