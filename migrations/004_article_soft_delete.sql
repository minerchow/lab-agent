-- Migration: Add is_deleted to article for soft delete
-- Date: 2026-07-05
-- Description: Add is_deleted field to article table to support soft delete.
--              When a user is soft-deleted, their articles are also soft-deleted.

ALTER TABLE article ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0;
