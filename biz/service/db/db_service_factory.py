import os
from biz.service.db.base_db_service import BaseDBService
from biz.service.db.sqlite_service import SQLiteService
from biz.service.db.mysql_service import MySQLService
from biz.utils.log import logger


class DBServiceFactory:
    """数据库服务工厂类，根据配置创建相应的数据库服务实例"""
    
    _instance = None
    
    @staticmethod
    def create_db_service() -> BaseDBService:
        """
        根据环境变量配置创建数据库服务实例
        支持的数据库类型：sqlite（默认）、mysql
        
        环境变量配置：
        - DB_TYPE: 数据库类型，可选值：sqlite, mysql
        - DB_FILE: SQLite数据库文件路径（仅当DB_TYPE=sqlite时使用）
        - DB_HOST: MySQL数据库主机地址（仅当DB_TYPE=mysql时使用）
        - DB_PORT: MySQL数据库端口（仅当DB_TYPE=mysql时使用）
        - DB_USER: MySQL数据库用户名（仅当DB_TYPE=mysql时使用）
        - DB_PASSWORD: MySQL数据库密码（仅当DB_TYPE=mysql时使用）
        - DB_NAME: MySQL数据库名称（仅当DB_TYPE=mysql时使用）
        
        :return: 数据库服务实例
        """
        db_type = os.environ.get('DB_TYPE', 'sqlite').lower()
        
        if db_type == 'mysql':
            # MySQL配置
            host = os.environ.get('DB_HOST', 'localhost')
            port = int(os.environ.get('DB_PORT', '3306'))
            user = os.environ.get('DB_USER', 'root')
            password = os.environ.get('DB_PASSWORD', '')
            database = os.environ.get('DB_NAME', 'ai_codereview')
            
            if not password:
                logger.warning("MySQL密码未配置，使用空密码可能存在安全风险")
            
            logger.info(f"使用MySQL数据库: {host}:{port}/{database}")
            return MySQLService(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database
            )
        else:
            # SQLite配置（默认）
            db_file = os.environ.get('DB_FILE', 'data/data.db')
            logger.info(f"使用SQLite数据库: {db_file}")
            return SQLiteService(db_file=db_file)
    
    @classmethod
    def get_instance(cls) -> BaseDBService:
        """
        获取数据库服务单例实例
        :return: 数据库服务实例
        """
        if cls._instance is None:
            cls._instance = cls.create_db_service()
            cls._instance.init_db()
        return cls._instance
    
    @classmethod
    def reset_instance(cls):
        """重置单例实例（主要用于测试）"""
        cls._instance = None
