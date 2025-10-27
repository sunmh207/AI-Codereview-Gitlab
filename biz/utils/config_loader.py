import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import yaml

from biz.utils.log import logger


class ConfigLoader:
    """
    配置加载器，支持按应用名独立目录配置
    配置文件优先级：conf/{app_name}/.env > conf/.env
    """
    
    # 默认配置目录
    DEFAULT_CONF_DIR = "conf"
    
    # 环境变量文件名
    ENV_FILE_NAME = ".env"
    
    # Prompt模板文件名
    PROMPT_TEMPLATE_FILE_NAME = "prompt_templates.yml"
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置加载器"""
        if not ConfigLoader._initialized:
            self.app_name = None
            ConfigLoader._initialized = True
    
    def set_app_name(self, app_name: str):
        """设置应用名称"""
        self.app_name = app_name
        logger.info(f"ConfigLoader设置应用名称: {app_name}")
    
    def get_env_file_path(self, app_name: Optional[str] = None, project_path: Optional[str] = None) -> str:
        """
        获取环境变量配置文件路径
        优先级：项目级别配置 > 命名空间级别配置 > 默认配置
        :param app_name: 应用名称（URL slug，已废弃，保留用于兼容）
        :param project_path: 项目路径（如：asset/asset-batch-center）
        :return: 配置文件路径
        """
        if project_path and '/' in project_path:
            # 提取命名空间和项目名
            parts = project_path.split('/', 1)
            namespace = parts[0]
            project_name = parts[1] if len(parts) > 1 else ''
            
            # 1. 优先查找项目级别配置: conf/{namespace}/{project_name}/.env
            if project_name:
                project_env_path = Path(self.DEFAULT_CONF_DIR) / namespace / project_name / self.ENV_FILE_NAME
                if project_env_path.exists():
                    logger.info(msg=f"使用项目级别配置: {project_env_path}")
                    return str(project_env_path)
                else:
                    logger.debug(f"项目级别配置不存在 ({project_env_path})")
            
            # 2. 查找命名空间级别配置: conf/{namespace}/.env
            namespace_env_path = Path(self.DEFAULT_CONF_DIR) / namespace / self.ENV_FILE_NAME
            if namespace_env_path.exists():
                logger.info(msg=f"使用命名空间级别配置: {namespace_env_path}")
                return str(namespace_env_path)
            else:
                logger.debug(f"命名空间级别配置不存在 ({namespace_env_path})")
        
        # 3. 使用默认配置: conf/.env
        default_env_path = Path(self.DEFAULT_CONF_DIR) / self.ENV_FILE_NAME
        logger.info(msg=f"使用默认配置: {default_env_path}")
        return str(default_env_path)
    
    def load_env(self, app_name: Optional[str] = None, project_path: Optional[str] = None, override: bool = False):
        """
        加载环境变量配置
        :param app_name: 应用名称（URL slug）
        :param project_path: 项目路径（如：asset/asset-batch-center）
        :param override: 是否覆盖已存在的环境变量
        """
        env_path = self.get_env_file_path(app_name, project_path)
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=override)
            logger.info(msg=f"成功加载环境变量配置: {env_path}")
        else:
            logger.warning(f"环境变量配置文件不存在: {env_path}")
    
    def get_prompt_template_file_path(self, app_name: Optional[str] = None, project_path: Optional[str] = None) -> str:
        """
        获取Prompt模板配置文件路径
        优先级：项目级别配置 > 命名空间级别配置 > 默认配置
        :param app_name: 应用名称（URL slug，已废弃，保留用于兼容）
        :param project_path: 项目路径（如：asset/asset-batch-center）
        :return: 配置文件路径
        """
        if project_path and '/' in project_path:
            # 提取命名空间和项目名
            parts = project_path.split('/', 1)
            namespace = parts[0]
            project_name = parts[1] if len(parts) > 1 else ''
            
            # 1. 优先查找项目级别配置: conf/{namespace}/{project_name}/prompt_templates.yml
            if project_name:
                project_template_path = Path(self.DEFAULT_CONF_DIR) / namespace / project_name / self.PROMPT_TEMPLATE_FILE_NAME
                if project_template_path.exists():
                    logger.info(msg=f"使用项目级别Prompt模板: {project_template_path}")
                    return str(project_template_path)
                else:
                    logger.debug(f"项目级别Prompt模板不存在 ({project_template_path})")
            
            # 2. 查找命名空间级别配置: conf/{namespace}/prompt_templates.yml
            namespace_template_path = Path(self.DEFAULT_CONF_DIR) / namespace / self.PROMPT_TEMPLATE_FILE_NAME
            if namespace_template_path.exists():
                logger.info(msg=f"使用命名空间级别Prompt模板: {namespace_template_path}")
                return str(namespace_template_path)
            else:
                logger.debug(f"命名空间级别Prompt模板不存在 ({namespace_template_path})")
        
        # 3. 使用默认配置: conf/prompt_templates.yml
        default_template_path = Path(self.DEFAULT_CONF_DIR) / self.PROMPT_TEMPLATE_FILE_NAME
        logger.info(msg=f"使用默认Prompt模板: {default_template_path}")
        return str(default_template_path)
    
    def load_prompt_template(self, prompt_key: str, app_name: Optional[str] = None, project_path: Optional[str] = None) -> dict:
        """
        加载Prompt模板配置
        :param prompt_key: 提示词配置键
        :param app_name: 应用名称（URL slug）
        :param project_path: 项目路径（如：asset/asset-batch-center）
        :return: 提示词配置字典
        """
        template_path = self.get_prompt_template_file_path(app_name, project_path)
        
        try:
            with open(template_path, "r", encoding="utf-8") as file:
                templates = yaml.safe_load(file)
                prompts = templates.get(prompt_key, {})
                
                if not prompts:
                    logger.warning(f"在配置文件 {template_path} 中未找到 prompt_key: {prompt_key}")
                else:
                    logger.info(f"成功加载Prompt模板 {prompt_key} from {template_path}")
                
                return prompts
        except (FileNotFoundError, KeyError, yaml.YAMLError) as e:
            logger.error(f"加载Prompt模板配置失败: {e}")
            raise Exception(f"Prompt模板配置加载失败: {e}")
    
    @staticmethod
    def create_app_config_dir(app_name: str) -> Path:
        """
        创建应用专属配置目录
        :param app_name: 应用名称（URL slug）
        :return: 配置目录路径
        """
        app_conf_dir = Path(ConfigLoader.DEFAULT_CONF_DIR) / app_name
        app_conf_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"创建应用专属配置目录: {app_conf_dir}")
        return app_conf_dir


# 全局配置加载器实例
config_loader = ConfigLoader()
