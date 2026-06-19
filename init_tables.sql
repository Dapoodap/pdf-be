CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR UNIQUE,
    email VARCHAR UNIQUE,
    hashed_password VARCHAR,
    is_premium BOOLEAN DEFAULT FALSE
);

CREATE INDEX ix_users_id ON users(id);
CREATE INDEX ix_users_username ON users(username);
CREATE INDEX ix_users_email ON users(email);


CREATE TABLE services (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE,
    description VARCHAR
);

CREATE INDEX ix_services_id ON services(id);
CREATE INDEX ix_services_name ON services(name);


CREATE TABLE pricings (
    id SERIAL PRIMARY KEY,
    service_id INTEGER REFERENCES services(id) ON DELETE CASCADE,
    price DOUBLE PRECISION DEFAULT 0.0
);

CREATE INDEX ix_pricings_id ON pricings(id);


CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    amount DOUBLE PRECISION,
    status VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_transactions_id ON transactions(id);


CREATE TABLE file_histories (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    service_id INTEGER REFERENCES services(id) ON DELETE SET NULL,
    file_path VARCHAR,
    file_name VARCHAR,
    file_type VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_file_histories_id ON file_histories(id);
