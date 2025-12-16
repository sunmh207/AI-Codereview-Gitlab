import os
import unittest
from pathlib import Path
import tempfile
import shutil

from biz.utils.config_loader import ConfigLoader, config_loader


class TestConfigLoader(unittest.TestCase):
    """测试配置加载器"""
    
    def setUp(self):
        """设置测试环境"""
        # 创建临时测试目录
        self.test_dir = tempfile.mkdtemp()
        self.original_conf_dir = ConfigLoader.DEFAULT_CONF_DIR
        ConfigLoader.DEFAULT_CONF_DIR = self.test_dir  # type: ignore
        
        # 创建默认配置文件
        self.default_env_content = "TEST_VAR=default_value\nLLM_PROVIDER=openai"
        self.default_prompt_content = """code_review_prompt:
  system_prompt: "Default system prompt"
  user_prompt: "Default user prompt"
"""
        
        Path(self.test_dir).mkdir(exist_ok=True)
        with open(os.path.join(self.test_dir, ".env"), "w") as f:
            f.write(self.default_env_content)
        with open(os.path.join(self.test_dir, "prompt_templates.yml"), "w") as f:
            f.write(self.default_prompt_content)
    
    def tearDown(self):
        """清理测试环境"""
        ConfigLoader.DEFAULT_CONF_DIR = self.original_conf_dir  # type: ignore
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        loader1 = ConfigLoader()
        loader2 = ConfigLoader()
        self.assertIs(loader1, loader2)
    
    def test_get_default_env_file_path(self):
        """测试获取默认环境变量文件路径"""
        loader = ConfigLoader()
        env_path = loader.get_env_file_path()
        expected_path = os.path.join(self.test_dir, ".env")
        self.assertEqual(env_path, expected_path)
    
    def test_get_app_specific_env_file_path(self):
        """测试获取应用专属环境变量文件路径"""
        # 创建应用专属配置
        app_name = "test_app"
        app_dir = os.path.join(self.test_dir, app_name)
        os.makedirs(app_dir)
        app_env_content = "TEST_VAR=app_specific_value"
        with open(os.path.join(app_dir, ".env"), "w") as f:
            f.write(app_env_content)
        
        loader = ConfigLoader()
        loader.set_app_name(app_name)
        env_path = loader.get_env_file_path()
        expected_path = os.path.join(self.test_dir, app_name, ".env")
        self.assertEqual(env_path, expected_path)
    
    def test_get_env_file_path_fallback_to_default(self):
        """测试当应用专属配置不存在时，降级到默认配置"""
        app_name = "non_existent_app"
        loader = ConfigLoader()
        loader.set_app_name(app_name)
        env_path = loader.get_env_file_path()
        expected_path = os.path.join(self.test_dir, ".env")
        self.assertEqual(env_path, expected_path)
    
    def test_get_default_prompt_template_file_path(self):
        """测试获取默认Prompt模板文件路径"""
        loader = ConfigLoader()
        template_path = loader.get_prompt_template_file_path()
        expected_path = os.path.join(self.test_dir, "prompt_templates.yml")
        self.assertEqual(template_path, expected_path)
    
    def test_get_app_specific_prompt_template_file_path(self):
        """测试获取应用专属Prompt模板文件路径"""
        # 创建应用专属配置
        app_name = "test_app"
        app_dir = os.path.join(self.test_dir, app_name)
        os.makedirs(app_dir)
        app_template_content = """code_review_prompt:
  system_prompt: "App specific system prompt"
  user_prompt: "App specific user prompt"
"""
        with open(os.path.join(app_dir, "prompt_templates.yml"), "w") as f:
            f.write(app_template_content)
        
        loader = ConfigLoader()
        loader.set_app_name(app_name)
        template_path = loader.get_prompt_template_file_path()
        expected_path = os.path.join(self.test_dir, app_name, "prompt_templates.yml")
        self.assertEqual(template_path, expected_path)
    
    def test_load_prompt_template_default(self):
        """测试加载默认Prompt模板"""
        loader = ConfigLoader()
        prompts = loader.load_prompt_template("code_review_prompt")
        self.assertIn("system_prompt", prompts)
        self.assertIn("user_prompt", prompts)
        self.assertEqual(prompts["system_prompt"], "Default system prompt")
        self.assertEqual(prompts["user_prompt"], "Default user prompt")
    
    def test_load_prompt_template_app_specific(self):
        """测试加载应用专属Prompt模板"""
        # 创建应用专属配置
        app_name = "test_app"
        app_dir = os.path.join(self.test_dir, app_name)
        os.makedirs(app_dir)
        app_template_content = """code_review_prompt:
  system_prompt: "App specific system prompt"
  user_prompt: "App specific user prompt"
"""
        with open(os.path.join(app_dir, "prompt_templates.yml"), "w", encoding="utf-8") as f:
            f.write(app_template_content)
        
        loader = ConfigLoader()
        prompts = loader.load_prompt_template("code_review_prompt", app_name)
        self.assertEqual(prompts["system_prompt"], "App specific system prompt")
        self.assertEqual(prompts["user_prompt"], "App specific user prompt")
    
    def test_create_app_config_dir(self):
        """测试创建应用专属配置目录"""
        app_name = "new_app"
        app_dir = ConfigLoader.create_app_config_dir(app_name)
        self.assertTrue(app_dir.exists())
        self.assertTrue(app_dir.is_dir())
        expected_path = Path(self.test_dir) / app_name
        self.assertEqual(app_dir, expected_path)


if __name__ == "__main__":
    unittest.main()
