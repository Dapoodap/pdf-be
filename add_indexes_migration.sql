-- =============================================================================
-- Migration: Add missing indexes for performance optimization
-- Date: 2026-06-23
-- Description: Adds indexes on user_id FK columns di tabel transactions,
--              subscriptions, dan file_histories untuk mempercepat query.
-- =============================================================================
-- NOTE: Jalankan script ini jika database sudah ada (tabel sudah terbuat).
--       SQLAlchemy hanya membuat index otomatis saat CREATE TABLE (tabel baru).

-- Index untuk tabel transactions
CREATE INDEX IF NOT EXISTS ix_transactions_user_id ON transactions (user_id);

-- Index untuk tabel subscriptions
CREATE INDEX IF NOT EXISTS ix_subscriptions_user_id ON subscriptions (user_id);

-- Index tambahan untuk mempercepat query "subscription aktif" di auth/me
CREATE INDEX IF NOT EXISTS ix_subscriptions_end_date ON subscriptions (end_date);

-- Index untuk tabel file_histories
CREATE INDEX IF NOT EXISTS ix_file_histories_user_id ON file_histories (user_id);

-- Index tambahan untuk mempercepat filter berdasarkan tanggal (query history 24 jam)
CREATE INDEX IF NOT EXISTS ix_file_histories_created_at ON file_histories (created_at);

-- =============================================================================
-- Verifikasi index setelah dijalankan:
-- SELECT indexname, tablename FROM pg_indexes WHERE schemaname = 'public' ORDER BY tablename;
-- =============================================================================
