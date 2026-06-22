-- 1. Remove old columns from users table
ALTER TABLE users DROP COLUMN IF EXISTS is_premium;
ALTER TABLE users DROP COLUMN IF EXISTS premium_start_date;
ALTER TABLE users DROP COLUMN IF EXISTS premium_end_date;

-- 2. Add membership_status to users table
ALTER TABLE users ADD COLUMN membership_status VARCHAR DEFAULT 'basic';

-- 3. Update pricings table
ALTER TABLE pricings ADD COLUMN plan_type VARCHAR;
ALTER TABLE pricings ADD COLUMN duration_days INTEGER;

-- 4. Create subscriptions table
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pricing_id INTEGER REFERENCES pricings(id) ON DELETE SET NULL,
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE
);

-- 5. Update transactions table for Midtrans
ALTER TABLE transactions ADD COLUMN order_id VARCHAR UNIQUE;
ALTER TABLE transactions ADD COLUMN midtrans_transaction_id VARCHAR;
ALTER TABLE transactions ADD COLUMN payment_type VARCHAR;
ALTER TABLE transactions ADD COLUMN snap_token VARCHAR;
ALTER TABLE transactions ADD COLUMN snap_redirect_url VARCHAR;

CREATE INDEX ix_transactions_order_id ON transactions (order_id);

CREATE INDEX ix_subscriptions_id ON subscriptions (id);
