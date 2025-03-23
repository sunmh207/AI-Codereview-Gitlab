import re
import os
import yaml
from typing import Dict, List, Optional

from biz.utils.log import logger
from biz.llm.factory import Factory


class CodeReviewer:
    def __init__(self):
        self.client = Factory().getClient()
        self.agents = self._load_agents()

    def _load_agents(self) -> Dict[str, Dict]:
        """加载所有启用的Agent配置"""
        agents = {}
        agents_dir = "conf/agents"
        
        # 确保agents目录存在
        if not os.path.exists(agents_dir):
            logger.warning(f"Agents directory {agents_dir} does not exist")
            return agents
            
        # 从环境变量获取启用的Agent列表
        enabled_agents = os.getenv('ENABLED_AGENTS', '').split(',')
        enabled_agents = [agent.strip() for agent in enabled_agents if agent.strip()]
        
        if not enabled_agents:
            logger.warning("No agents enabled in .env configuration")
            # 如果没有配置启用的Agent，加载默认的code_review配置
            return self._load_default_config()
            
        # 遍历启用的Agent
        for agent_name in enabled_agents:
            agent_dir = os.path.join(agents_dir, agent_name)
            if not os.path.isdir(agent_dir):
                logger.warning(f"Agent directory {agent_dir} does not exist")
                continue
                
            # 加载agent的提示词配置
            prompt_file = os.path.join(agent_dir, "prompt_templates.yml")
            if not os.path.exists(prompt_file):
                logger.warning(f"Prompt templates file not found for agent {agent_name}")
                continue
                
            try:
                with open(prompt_file, "r", encoding='utf-8') as file:
                    prompt_templates = yaml.safe_load(file)
                    system_prompt = prompt_templates.get('system_prompt')
                    user_prompt = prompt_templates.get('user_prompt')
                    
                    if not system_prompt or not user_prompt:
                        logger.warning(f"Invalid prompt templates for agent {agent_name}")
                        continue
                        
                    agents[agent_name] = {
                        "system_message": {
                            "role": "system",
                            "content": system_prompt
                        },
                        "user_message": {
                            "role": "user",
                            "content": user_prompt
                        }
                    }
                    logger.info(f"Successfully loaded agent {agent_name}")
            except Exception as e:
                logger.error(f"Error loading agent {agent_name}: {str(e)}")
                continue
                
        # 如果没有成功加载任何Agent，加载默认配置
        if not agents:
            logger.warning("No agents loaded successfully, falling back to default configuration")
            return self._load_default_config()
                
        return agents

    def _load_default_config(self) -> Dict[str, Dict]:
        """加载默认的code_review配置"""
        try:
            with open("conf/prompt_templates.yml", "r", encoding='utf-8') as file:
                prompt_templates = yaml.safe_load(file)
                system_prompt = prompt_templates.get('system_prompt')
                user_prompt = prompt_templates.get('user_prompt')
                
                if system_prompt and user_prompt:
                    return {
                        "code_review": {
                            "system_message": {
                                "role": "system",
                                "content": system_prompt
                            },
                            "user_message": {
                                "role": "user",
                                "content": user_prompt
                            }
                        }
                    }
                else:
                    logger.error("Invalid default prompt templates configuration")
        except Exception as e:
            logger.error(f"Error loading default configuration: {str(e)}")
        return {}

    def review_code(self, diffs_text: str, commits_text: str = "", system_prompt: str = None, user_prompt: str = None) -> str:
        """Review代码，并返回所有启用的Agent的结果"""
        if system_prompt and user_prompt:
            # 如果提供了自定义的提示词，直接使用
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt.format(
                        diffs_text=diffs_text,
                        commits_text=commits_text
                    )
                }
            ]
            return self.call_llm(messages)
            
        # 如果没有提供自定义提示词，使用默认的agents
        if not self.agents:
            logger.error("No agents available for code review")
            return "No agents available for code review"
            
        all_results = []
        for agent_name, prompts in self.agents.items():
            try:
                messages = [
                    prompts["system_message"],
                    {
                        "role": "user",
                        "content": prompts["user_message"]["content"].format(
                            diffs_text=diffs_text,
                            commits_text=commits_text
                        )
                    }
                ]
                result = self.call_llm(messages)
                all_results.append(f"### {agent_name} 的评审结果\n\n{result}")
            except Exception as e:
                logger.error(f"Error in agent {agent_name}: {str(e)}")
                all_results.append(f"### {agent_name} 评审失败\n\n{str(e)}")
                
        return "\n\n".join(all_results)

    def call_llm(self, messages: list) -> str:
        logger.info(f"向AI发送代码Review请求, message:{messages})")
        review_result = self.client.completions(
            messages=messages
        )
        logger.info(f"收到AI返回结果:{review_result}")
        return review_result

    @staticmethod
    def parse_review_score(review_text: str) -> int:
        """解析AI返回的Review结果，返回评分"""
        if not review_text:
            return 0  # 如果review_text为空，返回 0
        match = re.search(r"总分[:：]\s*(\d+)分?", review_text)

        if match:
            return int(match.group(1))  # 提取数值部分并转换为整数
        return 0  # 如果未匹配到，返回 0
