CREATE DATABASE IF NOT EXISTS `auto_download`
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_general_ci;

USE `auto_download`;

DROP TABLE IF EXISTS `ad_browser_page`;
DROP TABLE IF EXISTS `ad_browser_page_config`;
DROP TABLE IF EXISTS `ad_browser_window`;
DROP TABLE IF EXISTS `ad_browser_session`;

CREATE TABLE `ad_browser_window` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'primary key',
  `window_id` VARCHAR(64) NOT NULL COMMENT 'business window id',
  `status` CHAR(1) NOT NULL DEFAULT '1' COMMENT '1 valid 0 invalid',
  `last_page_title` VARCHAR(255) DEFAULT NULL COMMENT 'last active page title',
  `last_page_url` VARCHAR(500) DEFAULT NULL COMMENT 'last active page URL',
  `created_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'created time',
  `updated_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'updated time',
  `invalid_time` DATETIME DEFAULT NULL COMMENT 'invalid time',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_window_id` (`window_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='browser window table';

CREATE TABLE `ad_browser_page` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'primary key',
  `window_id` BIGINT NOT NULL COMMENT 'window primary key',
  `title` VARCHAR(255) DEFAULT NULL COMMENT 'page title',
  `url` VARCHAR(1000) DEFAULT NULL COMMENT 'page URL',
  `status` CHAR(1) NOT NULL DEFAULT '1' COMMENT '0 opened inactive 1 active 2 invalid',
  `sort_no` INT NOT NULL DEFAULT 1 COMMENT 'page order in window',
  `created_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'created time',
  `updated_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'updated time',
  `invalid_time` DATETIME DEFAULT NULL COMMENT 'invalid time',
  PRIMARY KEY (`id`),
  KEY `idx_window_status` (`window_id`, `status`),
  KEY `idx_window_sort` (`window_id`, `sort_no`),
  CONSTRAINT `fk_ad_browser_page_window_id` FOREIGN KEY (`window_id`) REFERENCES `ad_browser_window` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='browser page table';

CREATE TABLE `ad_browser_page_config` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT 'primary key',
  `config_code` VARCHAR(64) NOT NULL COMMENT 'page config code',
  `config_name` VARCHAR(255) DEFAULT NULL COMMENT 'page config name',
  `page_name` VARCHAR(255) DEFAULT NULL COMMENT 'page name',
  `url` VARCHAR(1000) NOT NULL COMMENT 'page URL',
  `status` CHAR(1) NOT NULL DEFAULT '1' COMMENT '1 valid 0 invalid',
  `sort_no` INT NOT NULL DEFAULT 1 COMMENT 'open order',
  `created_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT 'created time',
  `updated_time` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'updated time',
  `invalid_time` DATETIME DEFAULT NULL COMMENT 'invalid time',
  PRIMARY KEY (`id`),
  KEY `idx_config_status_sort` (`config_code`, `status`, `sort_no`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='browser page open config table';
