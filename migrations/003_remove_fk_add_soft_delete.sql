-- Migration: Remove FK on article.user_id, add is_deleted to user
-- Date: 2026-07-05
-- Description: Remove FK constraint from article.user_id (validation moved to app layer), add is_deleted field to user for soft delete

ALTER TABLE article DROP FOREIGN KEY fk_article_user;
ALTER TABLE user ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;
