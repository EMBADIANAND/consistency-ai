USE consistency_ai;

CREATE TABLE life_rules (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    title VARCHAR(120) NOT NULL,
    description TEXT NULL,
    emoji VARCHAR(16) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_life_rules_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_life_rules_user_active (user_id, is_active)
);

CREATE TABLE daily_tasks (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    life_rule_id INT UNSIGNED NULL,
    title VARCHAR(180) NOT NULL,
    emoji VARCHAR(16) NULL,
    scheduled_for DATE NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_daily_tasks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_daily_tasks_rule FOREIGN KEY (life_rule_id) REFERENCES life_rules(id) ON DELETE SET NULL,
    INDEX idx_daily_tasks_user_date (user_id, scheduled_for),
    INDEX idx_daily_tasks_rule (life_rule_id)
);

CREATE TABLE daily_check_ins (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NOT NULL,
    checkin_date DATE NOT NULL,
    mood VARCHAR(32) NULL,
    reflection TEXT NULL,
    completed_tasks INT UNSIGNED NOT NULL DEFAULT 0,
    total_tasks INT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_checkins_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT uq_checkins_user_date UNIQUE (user_id, checkin_date)
);
