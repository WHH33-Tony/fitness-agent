CREATE DATABASE IF NOT EXISTS users CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS sports CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE users;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  phone VARCHAR(20) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_profiles (
  user_id BIGINT PRIMARY KEY,
  nickname VARCHAR(64),
  height DECIMAL(5,2),
  weight DECIMAL(5,2),
  gender ENUM('male', 'female', 'unknown') NOT NULL DEFAULT 'unknown',
  age INT,
  voice_type VARCHAR(64) NOT NULL DEFAULT 'longxiaochun',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_questionnaire (
  user_id BIGINT PRIMARY KEY,
  physique VARCHAR(64),
  fitness_goal VARCHAR(128),
  exercise_level VARCHAR(64),
  injury_history JSON,
  avoid_movements JSON,
  extra_info JSON,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_questionnaire_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS training_plans (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  plan_data JSON NOT NULL,
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_plan_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS daily_exercise (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  exercise_date DATE NOT NULL,
  calories_burned DECIMAL(8,2) NOT NULL DEFAULT 0,
  exercise_records JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uk_daily_user_date (user_id, exercise_date),
  CONSTRAINT fk_daily_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 姿态分析会话记录
CREATE TABLE IF NOT EXISTS pose_sessions (
  session_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  movement_name VARCHAR(128) NOT NULL,
  score INT NOT NULL,
  metrics JSON,
  errors JSON,
  suggestions JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_pose_session_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_pose_sessions_user_created (user_id, created_at)
);

-- MCP 工具注册表（工具治理）
CREATE TABLE IF NOT EXISTS mcp_tools (
  tool_name VARCHAR(64) PRIMARY KEY,
  description TEXT NOT NULL,
  input_schema JSON NOT NULL,
  endpoint VARCHAR(255) NOT NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  call_count BIGINT NOT NULL DEFAULT 0,
  avg_latency_ms INT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Agent 会话表（记录意图与工具编排）
CREATE TABLE IF NOT EXISTS agent_sessions (
  session_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  intent VARCHAR(64),
  tool_calls JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_agent_session_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  KEY idx_agent_sessions_user_created (user_id, created_at)
);

-- 问答记录表（用于历史查询）
CREATE TABLE IF NOT EXISTS qa_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT NOT NULL,
  sources JSON,
  intent VARCHAR(64),
  agent_session_id BIGINT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_qa_records_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_qa_records_agent_session FOREIGN KEY (agent_session_id) REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
  KEY idx_qa_records_user_created (user_id, created_at)
);

-- MCP 工具调用日志（可观测性）
CREATE TABLE IF NOT EXISTS tool_calls (
  call_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT,
  tool_name VARCHAR(64) NOT NULL,
  params JSON,
  result JSON,
  status ENUM('success', 'fail', 'timeout') NOT NULL,
  latency_ms INT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_tool_calls_session FOREIGN KEY (session_id) REFERENCES agent_sessions(session_id) ON DELETE SET NULL,
  KEY idx_tool_calls_tool_created (tool_name, created_at)
);

-- 用户反馈（用户-管理员多轮对话）
CREATE TABLE IF NOT EXISTS feedbacks (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  status ENUM('pending', 'replied', 'closed') NOT NULL DEFAULT 'pending',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY idx_feedbacks_user_updated (user_id, updated_at),
  CONSTRAINT fk_feedbacks_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS feedback_messages (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  feedback_id BIGINT NOT NULL,
  sender_type ENUM('user', 'admin') NOT NULL,
  sender_id BIGINT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_feedback_messages_feedback_created (feedback_id, created_at),
  CONSTRAINT fk_feedback_messages_feedback FOREIGN KEY (feedback_id) REFERENCES feedbacks(id) ON DELETE CASCADE,
  CONSTRAINT fk_feedback_messages_sender FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
);

INSERT INTO users (phone, password_hash, role)
VALUES
  ('admin', 'plain:123456', 'admin'),
  ('18800000002', 'plain:123456', 'user')
ON DUPLICATE KEY UPDATE phone = VALUES(phone);

INSERT INTO user_profiles (user_id, nickname, height, weight, gender, age)
SELECT id, CASE role WHEN 'admin' THEN '系统管理员' ELSE '普通用户' END,
       175.00, 70.00, 'unknown', 22
FROM users
ON DUPLICATE KEY UPDATE nickname = VALUES(nickname);

USE sports;

CREATE TABLE IF NOT EXISTS categories (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL UNIQUE,
  description VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS movements (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  category_id BIGINT NOT NULL,
  name VARCHAR(128) NOT NULL,
  description TEXT,
  difficulty ENUM('beginner', 'intermediate', 'advanced') NOT NULL DEFAULT 'beginner',
  video_url VARCHAR(255),
  keypoints_template JSON,
  target_muscles VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_movement_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS nutrition_foods (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(128) NOT NULL UNIQUE,
  calories_per_100g DECIMAL(8,2) NOT NULL,
  protein DECIMAL(8,2) NOT NULL DEFAULT 0,
  fat DECIMAL(8,2) NOT NULL DEFAULT 0,
  carbs DECIMAL(8,2) NOT NULL DEFAULT 0
);

INSERT INTO categories (name, description)
VALUES
  ('胸部', '胸大肌、上胸和下胸训练'),
  ('背部', '背阔肌、斜方肌和竖脊肌训练'),
  ('腿部', '股四头肌、臀腿和小腿训练'),
  ('肩部', '三角肌前中后束训练'),
  ('核心', '腹部、腰腹稳定和核心控制')
ON DUPLICATE KEY UPDATE description = VALUES(description);

INSERT INTO movements (category_id, name, description, difficulty, keypoints_template, target_muscles)
SELECT c.id, '标准俯卧撑', '保持身体一条直线，屈肘下降至胸部接近地面后推起。', 'beginner',
       JSON_OBJECT('elbow_min_angle', 70, 'body_line_score', 0.85), '胸大肌,肱三头肌,核心'
FROM categories c WHERE c.name = '胸部'
UNION ALL
SELECT c.id, '徒手深蹲', '双脚与肩同宽，下蹲时膝盖与脚尖方向一致，髋部向后坐。', 'beginner',
       JSON_OBJECT('knee_min_angle', 85, 'hip_min_angle', 80), '股四头肌,臀大肌'
FROM categories c WHERE c.name = '腿部'
UNION ALL
SELECT c.id, '平板支撑', '前臂支撑，肩髋踝保持直线，避免塌腰。', 'beginner',
       JSON_OBJECT('body_line_score', 0.9, 'hip_drop_max', 12), '核心,腹横肌'
FROM categories c WHERE c.name = '核心'
UNION ALL
SELECT c.id, '哑铃推举', '核心收紧，肩部发力向上推举，避免耸肩。', 'intermediate',
       JSON_OBJECT('shoulder_angle_target', 170, 'elbow_angle_target', 160), '三角肌,肱三头肌'
FROM categories c WHERE c.name = '肩部'
UNION ALL
SELECT c.id, '俯身划船', '背部保持平直，肘部贴近身体向后拉。', 'intermediate',
       JSON_OBJECT('back_line_score', 0.85, 'elbow_pull_angle', 90), '背阔肌,斜方肌'
FROM categories c WHERE c.name = '背部';

INSERT INTO nutrition_foods (name, calories_per_100g, protein, fat, carbs)
VALUES
  ('鸡胸肉', 165, 31, 3.6, 0),
  ('燕麦', 389, 16.9, 6.9, 66.3),
  ('鸡蛋', 143, 12.6, 9.5, 0.7),
  ('米饭', 116, 2.6, 0.3, 25.9)
ON DUPLICATE KEY UPDATE calories_per_100g = VALUES(calories_per_100g);
