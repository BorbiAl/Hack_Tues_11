CREATE TABLE IF NOT EXISTS core_user (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME DEFAULT NULL
);

-- Create the `core_profile` table
CREATE TABLE IF NOT EXISTS core_profile (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    bio TEXT,
    profile_picture VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES core_user(id) ON DELETE CASCADE
);

-- Create the `core_subject` table
CREATE TABLE IF NOT EXISTS core_subject (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Prepopulate the `core_subject` table
INSERT INTO core_subject (name) VALUES
    ('Psychology'),
    ('Literature'),
    ('Geography'),
    ('Biology'),
    ('History');

-- Create the `core_test` table
CREATE TABLE IF NOT EXISTS core_test (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    subject_id BIGINT NOT NULL,
    grade INT NOT NULL,
    question_data JSON NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_core_test_subject
        FOREIGN KEY (subject_id) REFERENCES core_subject (id)
        ON DELETE CASCADE
);