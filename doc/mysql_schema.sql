-- MySQL 数据库建表脚本
-- 使用说明：
-- 1. 创建数据库：CREATE DATABASE ai_codereview CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- 2. 切换到数据库：USE ai_codereview;
-- 3. 执行本脚本创建表结构

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS ai_codereview CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ai_codereview;

-- Merge Request 审核日志表
CREATE TABLE IF NOT EXISTS mr_review_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_name VARCHAR(255) COMMENT '项目名称',
    author VARCHAR(255) COMMENT '作者',
    source_branch VARCHAR(255) COMMENT '源分支',
    target_branch VARCHAR(255) COMMENT '目标分支',
    updated_at BIGINT COMMENT '更新时间戳',
    commit_messages TEXT COMMENT '提交信息',
    score INT COMMENT 'Review评分',
    url VARCHAR(500) COMMENT 'MR链接',
    review_result LONGTEXT COMMENT 'Review结果',
    additions INT DEFAULT 0 COMMENT '新增代码行数',
    deletions INT DEFAULT 0 COMMENT '删除代码行数',
    last_commit_id VARCHAR(255) DEFAULT '' COMMENT '最后一次commit ID',
    INDEX idx_updated_at (updated_at),
    INDEX idx_project_name (project_name),
    INDEX idx_author (author)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Merge Request审核日志表';

-- Push 审核日志表
CREATE TABLE IF NOT EXISTS push_review_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    project_name VARCHAR(255) COMMENT '项目名称',
    author VARCHAR(255) COMMENT '作者',
    branch VARCHAR(255) COMMENT '分支',
    updated_at BIGINT COMMENT '更新时间戳',
    commit_messages TEXT COMMENT '提交信息',
    score INT COMMENT 'Review评分',
    review_result LONGTEXT COMMENT 'Review结果',
    additions INT DEFAULT 0 COMMENT '新增代码行数',
    deletions INT DEFAULT 0 COMMENT '删除代码行数',
    INDEX idx_updated_at (updated_at),
    INDEX idx_project_name (project_name),
    INDEX idx_author (author)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Push审核日志表';

-- 查看表结构
SHOW TABLES;
DESC mr_review_log;
DESC push_review_log;
