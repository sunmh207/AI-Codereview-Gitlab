from typing import Optional
import pandas as pd

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.db.db_service_factory import DBServiceFactory


class ReviewService:
    """审核服务类，提供统一的数据库操作接口"""
    
    def __init__(self):
        """初始化审核服务，获取数据库服务实例"""
        self._db_service = DBServiceFactory.get_instance()
    
    def init_db(self):
        """初始化数据库及表结构（兼容旧版本调用）"""
        self._db_service.init_db()

    def insert_mr_review_log(self, entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        self._db_service.insert_mr_review_log(entity)

    def get_mr_review_logs(self, authors: Optional[list] = None, project_names: Optional[list] = None, 
                           updated_at_gte: Optional[int] = None, updated_at_lte: Optional[int] = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        return self._db_service.get_mr_review_logs(authors, project_names, updated_at_gte, updated_at_lte)

    def check_mr_last_commit_id_exists(self, project_name: str, source_branch: str, target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        return self._db_service.check_mr_last_commit_id_exists(project_name, source_branch, target_branch, last_commit_id)

    def insert_push_review_log(self, entity: PushReviewEntity):
        """插入推送审核日志"""
        self._db_service.insert_push_review_log(entity)

    def get_push_review_logs(self, authors: Optional[list] = None, project_names: Optional[list] = None,
                             updated_at_gte: Optional[int] = None, updated_at_lte: Optional[int] = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        return self._db_service.get_push_review_logs(authors, project_names, updated_at_gte, updated_at_lte)


# 初始化数据库（向后兼容）
DBServiceFactory.get_instance().init_db()
