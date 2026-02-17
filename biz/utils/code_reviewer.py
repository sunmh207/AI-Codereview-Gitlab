import abc
import os
import re
from typing import Dict, Any, List

import yaml
from jinja2 import Template

from biz.llm.factory import Factory
from biz.utils.log import logger
from biz.utils.token_util import count_tokens, truncate_text_by_tokens


class BaseReviewer(abc.ABC):
    """代码审查基类"""

    def __init__(self, prompt_key: str):
        self.client = Factory().getClient()
        self.prompts = self._load_prompts(prompt_key, os.getenv("REVIEW_STYLE", "professional"))

    def _load_prompts(self, prompt_key: str, style="professional") -> Dict[str, Any]:
        """加载提示词配置"""
        prompt_templates_file = "conf/prompt_templates.yml"
        try:
            # 在打开 YAML 文件时显式指定编码为 UTF-8，避免使用系统默认的 GBK 编码。
            with open(prompt_templates_file, "r", encoding="utf-8") as file:
                prompts = yaml.safe_load(file).get(prompt_key, {})

                # 使用Jinja2渲染模板
                def render_template(template_str: str) -> str:
                    return Template(template_str).render(style=style)

                system_prompt = render_template(prompts["system_prompt"])
                user_prompt = render_template(prompts["user_prompt"])

                return {
                    "system_message": {"role": "system", "content": system_prompt},
                    "user_message": {"role": "user", "content": user_prompt},
                }
        except (FileNotFoundError, KeyError, yaml.YAMLError) as e:
            logger.error(f"加载提示词配置失败: {e}")
            raise Exception(f"提示词配置加载失败: {e}")

    def call_llm(self, messages: List[Dict[str, Any]]) -> str:
        """调用 LLM 进行代码审核"""
        logger.info(f"向 AI 发送代码 Review 请求, messages: {messages}")
        review_result = self.client.completions(messages=messages)
        logger.info(f"收到 AI 返回结果: {review_result}")
        return review_result

    @abc.abstractmethod
    def review_code(self, *args, **kwargs) -> str:
        """抽象方法，子类必须实现"""
        pass


class CodeReviewer(BaseReviewer):
    """代码 Diff 级别的审查"""

    def __init__(self):
        super().__init__("code_review_prompt")

    def review_and_strip_code(self, changes_text: str, commits_text: str = "") -> str:
        """
        Review判断changes_text超出取前REVIEW_MAX_TOKENS个token，超出则截断changes_text，
        调用review_code方法，返回review_result，如果review_result是markdown格式，则去掉头尾的```
        :param changes_text:
        :param commits_text:
        :return:
        """
        # 如果超长，取前REVIEW_MAX_TOKENS个token
        review_max_tokens = int(os.getenv("REVIEW_MAX_TOKENS", 10000))
        # 如果changes为空,打印日志
        if not changes_text:
            logger.info("代码为空, diffs_text = %", str(changes_text))
            return "代码为空"

        # 计算tokens数量，如果超过REVIEW_MAX_TOKENS，截断changes_text
        tokens_count = count_tokens(changes_text)
        if tokens_count > review_max_tokens:
            changes_text = truncate_text_by_tokens(changes_text, review_max_tokens)

        review_result = self.review_code(changes_text, commits_text).strip()
        if review_result.startswith("```markdown") and review_result.endswith("```"):
            return review_result[11:-3].strip()
        return review_result

    def review_code(self, diffs_text: str, commits_text: str = "") -> str:
        """Review 代码并返回结果"""
        messages = [
            self.prompts["system_message"],
            {
                "role": "user",
                "content": self.prompts["user_message"]["content"].format(
                    diffs_text=diffs_text, commits_text=commits_text
                ),
            },
        ]
        return self.call_llm(messages)

    def review_changes_in_batches(self, changes: List[Dict[str, Any]], commits_text: str = "") -> str:
        """
        按文件批次审查代码变更，然后汇总所有审查结果
        :param changes: 代码变更列表，每个元素是一个包含文件信息的字典
        :param commits_text: 提交信息
        :return: 汇总后的审查结果
        """
        if not changes:
            logger.info("代码变更为空")
            return "代码为空"

        # 检查是否启用批量审查
        batch_review_enabled = os.getenv("BATCH_REVIEW_ENABLED", "1") == "1"
        
        # 如果未启用批量审查，使用原有的一次性审查方式
        if not batch_review_enabled:
            logger.info("批量审查功能未启用，使用传统一次性审查方式")
            return self.review_and_strip_code(str(changes), commits_text)

        review_max_tokens = int(os.getenv("REVIEW_MAX_TOKENS", 10000))
        # 获取每批次审查的文件数量配置
        files_per_batch = int(os.getenv("BATCH_REVIEW_FILES_PER_BATCH", 1))
        logger.info(f"批量审查已启用，每批次审查 {files_per_batch} 个文件")
        
        partial_reviews = []
        total_files = len(changes)
        
        # 按配置的批次大小分批进行审查
        for batch_start in range(0, total_files, files_per_batch):
            batch_end = min(batch_start + files_per_batch, total_files)
            batch_changes = changes[batch_start:batch_end]
            batch_num = (batch_start // files_per_batch) + 1
            total_batches = (total_files + files_per_batch - 1) // files_per_batch
            
            logger.info(f"正在审查第 {batch_num}/{total_batches} 批次 (文件 {batch_start + 1}-{batch_end}/{total_files})")
            
            # 收集当前批次的文件路径
            batch_file_paths = [
                change.get('new_path') or change.get('old_path', 'unknown') 
                for change in batch_changes
            ]
            
            # 将批次内的文件转换为文本
            batch_text = str(batch_changes)
            
            # 计算tokens数量，如果超过限制则截断
            tokens_count = count_tokens(batch_text)
            if tokens_count > review_max_tokens:
                logger.warning(f"批次 {batch_num} 的变更超过 {review_max_tokens} tokens，将截断")
                batch_text = truncate_text_by_tokens(batch_text, review_max_tokens)
            
            # 审查当前批次
            try:
                review_result = self.review_code(batch_text, commits_text).strip()
                if review_result.startswith("```markdown") and review_result.endswith("```"):
                    review_result = review_result[11:-3].strip()
                
                # 添加批次标识
                batch_header = f"### 批次 {batch_num} (文件: {', '.join(batch_file_paths)})\n"
                partial_reviews.append(f"{batch_header}{review_result}")
                logger.info(f"批次 {batch_num} 审查完成")
            except Exception as e:
                logger.error(f"审查批次 {batch_num} 时出错: {e}")
                partial_reviews.append(f"### 批次 {batch_num}\n审查失败: {str(e)}")
        
        # 如果只有一个批次，直接返回结果（去掉批次标识）
        if len(partial_reviews) == 1:
            # 去掉批次标题行
            result = partial_reviews[0]
            lines = result.split('\n', 1)
            return lines[1] if len(lines) > 1 else result
        
        # 汇总多个批次的审查结果
        logger.info(f"开始汇总 {len(partial_reviews)} 个批次的审查结果")
        summary_result = self._summarize_reviews(partial_reviews)
        return summary_result

    def _summarize_reviews(self, partial_reviews: List[str]) -> str:
        """
        使用 summary_merge_review_prompt 汇总多个审查结果
        :param partial_reviews: 各批次的审查结果列表
        :return: 汇总后的总审查报告
        """
        # 加载汇总提示词
        summary_prompts = self._load_prompts("summary_merge_review_prompt", os.getenv("REVIEW_STYLE", "professional"))
        
        # 拼接所有分批审查结果
        partial_reviews_text = "\n\n---\n\n".join(partial_reviews)
        
        # 构建汇总请求消息
        messages = [
            summary_prompts["system_message"],
            {
                "role": "user",
                "content": summary_prompts["user_message"]["content"].format(
                    partial_reviews_text=partial_reviews_text
                ),
            },
        ]
        
        # 调用LLM进行汇总
        summary_result = self.call_llm(messages).strip()
        if summary_result.startswith("```markdown") and summary_result.endswith("```"):
            summary_result = summary_result[11:-3].strip()
        
        logger.info("审查结果汇总完成")
        return summary_result

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析 AI 返回的 Review 结果，返回评分"""
        if not review_text:
            return 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)
        return int(match.group(1)) if match else 0

