-- Migration: Add userId field to article table
-- Date: 2026-05-04
-- Description: Add user_id field to article table for user association

ALTER TABLE article ADD COLUMN user_id INT NULL;
ALTER TABLE article ADD CONSTRAINT fk_article_user FOREIGN KEY (user_id) REFERENCES user(id);
