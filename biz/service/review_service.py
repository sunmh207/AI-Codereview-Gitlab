import sqlite3

import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity


class ReviewService:
    DB_FILE = "data/data.db"

    @staticmethod
    def init_db():
        """初始化数据库及表结构"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS mr_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            source_branch TEXT,
                            target_branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            url TEXT,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0,
                            last_commit_id TEXT DEFAULT ''
                        )
                    ''')
                cursor.execute('''
                        CREATE TABLE IF NOT EXISTS push_review_log (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_name TEXT,
                            author TEXT,
                            branch TEXT,
                            updated_at INTEGER,
                            commit_messages TEXT,
                            score INTEGER,
                            review_result TEXT,
                            additions INTEGER DEFAULT 0,
                            deletions INTEGER DEFAULT 0
                        )
                    ''')
                # 确保旧版本的mr_review_log、push_review_log表添加additions、deletions列
                tables = ["mr_review_log", "push_review_log"]
                columns = ["additions", "deletions"]
                for table in tables:
                    cursor.execute(f"PRAGMA table_info({table})")
                    current_columns = [col[1] for col in cursor.fetchall()]
                    for column in columns:
                        if column not in current_columns:
                            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER DEFAULT 0")

                # 为旧版本的mr_review_log表添加last_commit_id字段
                mr_columns = [
                    {
                        "name": "last_commit_id",
                        "type": "TEXT",
                        "default": "''"
                    }
                ]
                cursor.execute(f"PRAGMA table_info('mr_review_log')")
                current_columns = [col[1] for col in cursor.fetchall()]
                for column in mr_columns:
                    if column.get("name") not in current_columns:
                        cursor.execute(f"ALTER TABLE mr_review_log ADD COLUMN {column.get('name')} {column.get('type')} "
                                       f"DEFAULT {column.get('default')}")

                conn.commit()
                # 添加时间字段索引（默认查询就需要时间范围）
                conn.execute('CREATE INDEX IF NOT EXISTS idx_push_review_log_updated_at ON '
                             'push_review_log (updated_at);')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_mr_review_log_updated_at ON mr_review_log (updated_at);')
        except sqlite3.DatabaseError as e:
            print(f"Database initialization failed: {e}")

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity) -> int:
        """插入合并请求审核日志，返回插入记录的id"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''INSERT INTO mr_review_log (project_name, author, source_branch, 
                target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions, last_commit_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                               (entity.project_name, entity.author,
                                entity.source_branch, entity.target_branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.url, entity.review_result, entity.additions, entity.deletions, entity.last_commit_id))
                record_id = cursor.lastrowid
                conn.commit()
                print(f"Successfully inserted mr_review_log record with id: {record_id}")
                return record_id
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")
            return 0

    @staticmethod
    def get_mr_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                           updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                query = """
                            SELECT project_name, author, source_branch, target_branch, updated_at, commit_messages, score, url, review_result, additions, deletions
                            FROM mr_review_log
                            WHERE 1=1
                            """
                params = []

                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)
                query += " ORDER BY updated_at DESC"
                df = pd.read_sql_query(sql=query, con=conn, params=params)
            return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving review logs: {e}")
            return pd.DataFrame()

    @staticmethod
    def check_mr_last_commit_id_exists(project_name: str, source_branch: str, target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM mr_review_log 
                    WHERE project_name = ? AND source_branch = ? AND target_branch = ? AND last_commit_id = ?
                ''', (project_name, source_branch, target_branch, last_commit_id))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.DatabaseError as e:
            print(f"Error checking last_commit_id: {e}")
            return False

    @staticmethod
    def update_mr_review_log_by_id(record_id: int, score: float, review_result: str) -> bool:
        """通过id更新合并请求审核日志的review_result和score"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE mr_review_log 
                    SET score = ?, review_result = ?
                    WHERE id = ?
                ''', (score, review_result, record_id))
                conn.commit()
                updated_rows = cursor.rowcount
                if updated_rows > 0:
                    print(f"Successfully updated mr_review_log record with id: {record_id}")
                    return True
                else:
                    print(f"No mr_review_log record found with id: {record_id}")
                    return False
        except sqlite3.DatabaseError as e:
            print(f"Error updating mr_review_log by id: {e}")
            return False

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        """插入推送审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                                INSERT INTO push_review_log (project_name,author, branch, updated_at, commit_messages, score,review_result, additions, deletions)
                                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''',
                               (entity.project_name, entity.author, entity.branch,
                                entity.updated_at, entity.commit_messages, entity.score,
                                entity.review_result, entity.additions, entity.deletions))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print(f"Error inserting review log: {e}")

    @staticmethod
    def get_push_review_logs(authors: list = None, project_names: list = None, updated_at_gte: int = None,
                             updated_at_lte: int = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        try:
            with sqlite3.connect(ReviewService.DB_FILE) as conn:
                # 基础查询
                query = """
                    SELECT project_name, author, branch, updated_at, commit_messages, score, review_result, additions, deletions
                    FROM push_review_log
                    WHERE 1=1
                """
                params = []

                # 动态添加 authors 条件
                if authors:
                    placeholders = ','.join(['?'] * len(authors))
                    query += f" AND author IN ({placeholders})"
                    params.extend(authors)

                if project_names:
                    placeholders = ','.join(['?'] * len(project_names))
                    query += f" AND project_name IN ({placeholders})"
                    params.extend(project_names)

                # 动态添加 updated_at_gte 条件
                if updated_at_gte is not None:
                    query += " AND updated_at >= ?"
                    params.append(updated_at_gte)

                # 动态添加 updated_at_lte 条件
                if updated_at_lte is not None:
                    query += " AND updated_at <= ?"
                    params.append(updated_at_lte)

                # 按 updated_at 降序排序
                query += " ORDER BY updated_at DESC"

                # 执行查询
                df = pd.read_sql_query(sql=query, con=conn, params=params)
                return df
        except sqlite3.DatabaseError as e:
            print(f"Error retrieving push review logs: {e}")
            return pd.DataFrame()


# Initialize database
ReviewService.init_db()
