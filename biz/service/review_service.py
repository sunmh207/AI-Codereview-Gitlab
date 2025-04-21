import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from sqlalchemy.engine.url import make_url
import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity

Base = declarative_base()


class MRReviewLog(Base):
    __tablename__ = 'mr_review_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(255))
    author = Column(String(255))
    source_branch = Column(String(255))
    target_branch = Column(String(255))
    updated_at = Column(BigInteger)
    commit_messages = Column(Text)
    score = Column(Integer)
    url = Column(String(512))
    review_result = Column(Text)


class PushReviewLog(Base):
    __tablename__ = 'push_review_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(255))
    author = Column(String(255))
    branch = Column(String(255))
    updated_at = Column(BigInteger)
    commit_messages = Column(Text)
    score = Column(Integer)
    review_result = Column(Text)


class ReviewService:
    load_dotenv("conf/.env")
    db_url = os.environ.get('DB_URL', 'sqlite:///data/data.db')
    # db_url = os.environ.get('DB_URL', 'mysql+pymysql://root:root@127.0.0.1:3306/ai_code_review')

    engine = create_engine(db_url, echo=False)
    Session = sessionmaker(bind=engine)

    @staticmethod
    def init_db():
        """初始化数据库，如果是 MySQL 则自动建库"""
        url = make_url(ReviewService.db_url)
        backend = url.get_backend_name()

        if backend == "mysql":
            db_name = url.database
            if not db_name:
                print("Database name is missing in the DB_URL for MySQL.")
                raise ValueError("Database name required in DB_URL.")
            tmp_url = f"{url.drivername}://{url.username}:{url.password}@{url.host}:{url.port}"
            tmp_engine = create_engine(tmp_url)
            try:
                with tmp_engine.connect() as conn:
                    result = conn.execute(text(f"SHOW DATABASES LIKE '{db_name}'")).fetchone()
                    if not result:
                        conn.execute(text(f"CREATE DATABASE {db_name} DEFAULT CHARACTER SET utf8mb4"))
                        print(f"Database {db_name} has been created.")
                    else:
                        print(f"Database {db_name} already exists.")
            except OperationalError as e:
                print(f"Failed to connect to MySQL server or create database: {e}")
                raise
            finally:
                tmp_engine.dispose()

        # Create table structures (for all databases)
        Base.metadata.create_all(ReviewService.engine)

    @staticmethod
    def insert_mr_review_log(entity: MergeRequestReviewEntity):
        """插入 MR 审核日志"""
        session = ReviewService.Session()
        try:
            record = MRReviewLog()
            record.project_name = entity.project_name
            record.author = entity.author
            record.source_branch = entity.source_branch
            record.target_branch = entity.target_branch
            record.updated_at = entity.updated_at
            record.commit_messages = entity.commit_messages
            record.score = entity.score
            record.url = entity.url
            record.review_result = entity.review_result
            record.url_slug = entity.url_slug
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error inserting MR review log: {e}")
        finally:
            session.close()

    @staticmethod
    def get_mr_review_logs(authors=None, project_names=None, updated_at_gte=None, updated_at_lte=None):
        """获取 MR 审核日志"""
        session = ReviewService.Session()
        try:
            query = session.query(MRReviewLog)
            if authors:
                query = query.filter(MRReviewLog.author.in_(authors))
            if project_names:
                query = query.filter(MRReviewLog.project_name.in_(project_names))
            if updated_at_gte:
                query = query.filter(MRReviewLog.updated_at >= updated_at_gte)
            if updated_at_lte:
                query = query.filter(MRReviewLog.updated_at <= updated_at_lte)
            query = query.order_by(MRReviewLog.updated_at.desc())
            df = pd.read_sql(query.statement, ReviewService.engine)
            return df
        except Exception as e:
            print(f"Error querying MR review logs: {e}")
            return pd.DataFrame()
        finally:
            session.close()

    @staticmethod
    def insert_push_review_log(entity: PushReviewEntity):
        """插入 Push 审核日志"""
        session = ReviewService.Session()
        try:
            record = PushReviewLog()
            record.project_name = entity.project_name
            record.author = entity.author
            record.branch = entity.branch
            record.updated_at = entity.updated_at
            record.commit_messages = entity.commit_messages
            record.score = entity.score
            record.review_result = entity.review_result
            session.add(record)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error inserting push review log: {e}")
        finally:
            session.close()

    @staticmethod
    def get_push_review_logs(authors=None, project_names=None, updated_at_gte=None, updated_at_lte=None):
        """获取 Push 审核日志"""
        session = ReviewService.Session()
        try:
            query = session.query(PushReviewLog)
            if authors:
                query = query.filter(PushReviewLog.author.in_(authors))
            if project_names:
                query = query.filter(PushReviewLog.project_name.in_(project_names))
            if updated_at_gte:
                query = query.filter(PushReviewLog.updated_at >= updated_at_gte)
            if updated_at_lte:
                query = query.filter(PushReviewLog.updated_at <= updated_at_lte)
            query = query.order_by(PushReviewLog.updated_at.desc())
            df = pd.read_sql(query.statement, ReviewService.engine)
            return df
        except Exception as e:
            print(f"Error querying push review logs: {e}")
            return pd.DataFrame()
        finally:
            session.close()

# Initialize database
ReviewService.init_db()
