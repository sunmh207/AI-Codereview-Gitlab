from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity


class BaseDBService(ABC):
    """数据库服务基类，定义统一的数据库操作接口"""
    
    @abstractmethod
    def init_db(self):
        """初始化数据库及表结构"""
        pass
    
    @abstractmethod
    def insert_mr_review_log(self, entity: MergeRequestReviewEntity):
        """插入合并请求审核日志"""
        pass
    
    @abstractmethod
    def get_mr_review_logs(self, authors: Optional[list] = None, project_names: Optional[list] = None, 
                          updated_at_gte: Optional[int] = None, updated_at_lte: Optional[int] = None) -> pd.DataFrame:
        """获取符合条件的合并请求审核日志"""
        pass
    
    @abstractmethod
    def check_mr_last_commit_id_exists(self, project_name: str, source_branch: str, 
                                      target_branch: str, last_commit_id: str) -> bool:
        """检查指定项目的Merge Request是否已经存在相同的last_commit_id"""
        pass
    
    @abstractmethod
    def insert_push_review_log(self, entity: PushReviewEntity):
        """插入推送审核日志"""
        pass
    
    @abstractmethod
    def get_push_review_logs(self, authors: Optional[list] = None, project_names: Optional[list] = None,
                            updated_at_gte: Optional[int] = None, updated_at_lte: Optional[int] = None) -> pd.DataFrame:
        """获取符合条件的推送审核日志"""
        pass
