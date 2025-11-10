import pymysql
from typing import Optional
import pandas as pd
from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.db.base_db_service import BaseDBService
from biz.utils.log import logger


class MySQLService(BaseDBService):
    """MySQL数据库服务实现"""
    
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
    
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            db=self.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def init_db(self):
        """初始化数据库及表结构"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    # 创建 mr_review_log 表
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mr_review_log (
                            id BIGINT AUTO_INCREMENT PRIMARY KEY,
                            project_name VARCHAR(255),
                            author VARCHAR(255),
                            source_branch VARCHAR(255),
                            target_branch VARCHAR(255),
                            updated_at BIGINT,
                            commit_messages TEXT,
                            score INT,
                            url VARCHAR(500),
                            review_result LONGTEXT,
                            additions INT DEFAULT 0,
                            deletions INT DEFAULT 0,
                            last_commit_id VARCHAR(255) DEFAULT '',
                            INDEX idx_updated_at (updated_at),
                            INDEX idx_project_name (project_name),
                            INDEX idx_author (author)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    ''')
                    
                    # 创建 push_review_log 表
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS push_review_log (
                            id BIGINT AUTO_INCREMENT PRIMARY KEY,
                            project_name VARCHAR(255),
                            author VARCHAR(255),
                            branch VARCHAR(255),
                            updated_at BIGINT,
                            commit_messages TEXT,
                            score INT,
                            review_result LONGTEXT,
                            additions INT DEFAULT 0,
                            deletions INT DEFAULT 0,
                            INDEX idx_updated_at (updated_at),
                            INDEX idx_project_name (project_name),
                            INDEX idx_author (author)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    ''')
                    
                    conn.commit()
                    logger.info("MySQL数据库初始化成功")
            finally:
                conn.close()
        except pymysql.Error as e:
            logger.error(f"MySQL数据库初始化失败: {e}")
    
    def insert_mr_review_log(self, entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO mr_review_log (project_name, author, source_branch, target_branch, 
                        updated_at, commit_messages, score, url, review_result, additions, deletions, 
                        last_commit_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (entity.project_name, entity.author, entity.source_branch,
                     entity.target_branch, entity.updated_at, entity.commit_messages, entity.score,
                     entity.url, entity.review_result, entity.additions, entity.deletions,
                     entity.last_commit_id))
                    conn.commit()
                    logger.info(f"插入MR审核日志成功: {entity.project_name}#{entity.source_branch}->{entity.target_branch}")
            finally:
                conn.close()
        except pymysql.Error as e:
            logger.error(f"插入MR审核日志失败: {e}")
    
    def get_mr_review_logs(self, authors: Optional[list] = None, project_names: Optional[list] = None,
                          updated_at_gte: Optional[int] = None, updated_at_lte: Optional[int] = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
            conn = self._get_connection()
            try:
                query = """
                    SELECT project_name, author, source_branch, target_branch, updated_at, 
                           commit_messages, score, url, review_result, additions, deletions
                    FROM mr_review_log
                    WHERE 1=1
                """
                params = []

                if authors:
                    placeholders = ','.join(['%s'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['%s'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= %s"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= %s"
                    params.append(updated_at_lte)

                query += " ORDER BY updated_at DESC"
                
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                logger.info(f"查询MR审核日志成功: 条数={len(df)}, 条件=[authors={authors}, projects={project_names}, time_range={updated_at_gte}-{updated_at_lte}]")
                return df
            finally:
                conn.close()
        except pymysql.Error as e:
            logger.error(f"获取MR审核日志失败: {e}")
            return pd.DataFrame()
    
    def check_mr_last_commit_id_exists(self, project_name: str, source_branch: str,
                                      target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        SELECT COUNT(*) as count FROM mr_review_log 
                        WHERE project_name = %s AND source_branch = %s AND target_branch = %s AND last_commit_id = %s
                    ''', (project_name, source_branch, target_branch, last_commit_id))
                    result = cursor.fetchone()
                    exists = result['count'] > 0 if result else False
                    logger.info(f"检查last_commit_id: {project_name}#{source_branch}->{target_branch}#{last_commit_id}, 结果={exists}")
                    return exists
            finally:
                conn.close()
        except pymysql.Error as e:
            logger.error(f"检查last_commit_id失败: {e}")
            return False
    
    def insert_push_review_log(self, entity: PushReviewEntity):
        """插入推送审核日志"""
        try:
            conn = self._get_connection()
            try:
                with conn.cursor() as cursor:
                    cursor.execute('''
                        INSERT INTO push_review_log (project_name, author, branch, updated_at, 
                        commit_messages, score, review_result, additions, deletions)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (entity.project_name, entity.author, entity.branch,
                     entity.updated_at, entity.commit_messages, entity.score,
                     entity.review_result, entity.additions, entity.deletions))
                    conn.commit()
                    logger.info(f"插入Push审核日志成功: {entity.project_name}#{entity.branch}")
            finally:
                conn.close()
        except pymysql.Error as e:
            logger.error(f"插入Push审核日志失败: {e}")
    
    def get_push_review_logs(self, authors: Optional[list] = None, project_names: Optional[list] = None,
                            updated_at_gte: Optional[int] = None, updated_at_lte: Optional[int] = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
            conn = self._get_connection()
            try:
                query = """
                    SELECT project_name, author, branch, updated_at, commit_messages, 
                           score, review_result, additions, deletions
                    FROM push_review_log
                    WHERE 1=1
                """
                params = []

                if authors:
                    placeholders = ','.join(['%s'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['%s'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= %s"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= %s"
                    params.append(updated_at_lte)

                query += " ORDER BY updated_at DESC"
                
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                logger.info(f"查询Push审核日志成功: 条数={len(df)}, 条件=[authors={authors}, projects={project_names}, time_range={updated_at_gte}-{updated_at_lte}]")
                return df
            finally:
                conn.close()
        except pymysql.Error as e:
            logger.error(f"获取Push审核日志失败: {e}")
            return pd.DataFrame()
