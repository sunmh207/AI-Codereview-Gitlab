import re
from pathlib import Path
from typing import List, Tuple, Optional


class AIIgnore:
    def __init__(self, ai_ignore_path: Optional[str] = None, ai_ignore_content: Optional[str] = None,
                 patterns: Optional[List[str]] = None):
        """
        初始化AIIgnore对象
        参数:
        ai_ignore_path: .aiignore文件路径
        patterns: 直接提供规则列表
        """
        self.patterns: List[Tuple[bool, str, bool]] = []  # (是否否定, 模式, 是目录)
        self.root = Path.cwd()

        if ai_ignore_path:
            self.root = Path(ai_ignore_path).parent
            with open(ai_ignore_path, 'r', encoding='utf-8') as f:
                patterns = f.read().splitlines()

        if ai_ignore_content:
            patterns = ai_ignore_content.splitlines()

        if patterns:
            for pattern in patterns:
                self.add_pattern(pattern)

    def add_pattern(self, pattern: str):
        """添加单个规则"""
        # 跳过注释和空行
        stripped = pattern.strip()
        if not stripped or stripped.startswith('#'):
            return

        # 处理否定规则
        is_negative = stripped.startswith('!')
        if is_negative:
            stripped = stripped[1:]

        # 处理目录规则
        is_dir = stripped.endswith('/')
        if is_dir:
            stripped = stripped.rstrip('/')

        # 根目录匹配
        is_root = stripped.startswith('/')
        if is_root:
            stripped = stripped[1:]

        # 添加处理后的规则
        if stripped:  # 避免空规则
            self.patterns.append((is_negative, stripped, is_dir))

    def is_ignored(self, path: str) -> bool:
        """
        检查路径是否被忽略
        参数:
        path: 要检查的路径(可以是文件或目录)
        返回:
        bool: True表示被忽略，False表示不忽略
        """
        # 规范化路径为相对路径
        path_obj = Path(path)
        if path_obj.is_absolute():
            try:
                rel_path = path_obj.relative_to(self.root)
            except ValueError:
                # 路径不在根目录下
                return False
        else:
            rel_path = Path(path)

        # 将路径转换为POSIX格式
        path_str = rel_path.as_posix()

        # 处理目录路径的特殊情况
        if path_str == '.':
            path_str = ''

        # 存储匹配结果
        matched = False

        # 按顺序应用规则
        for is_negative, pattern, is_dir in self.patterns:
            # 检查是否匹配
            if self._match(pattern, path_str, is_dir):
                matched = not is_negative

        return matched

    def _match(self, pattern: str, path: str, is_dir: bool) -> bool:
        """内部方法：检查路径是否匹配单个模式"""
        # 空路径只匹配空模式
        if not pattern:
            return not path

        # 处理目录匹配
        if is_dir and not path.endswith('/'):
            path += '/'

        # 将模式转换为正则表达式
        regex = self._pattern_to_regex(pattern)
        if regex is None:
            return False

        # 执行匹配
        return re.fullmatch(regex, path) is not None

    def _pattern_to_regex(self, pattern: str) -> Optional[str]:
        """将.gitignore模式转换为正则表达式"""
        # 特殊处理：空模式
        if not pattern:
            return None

        # 转义正则特殊字符
        regex = ''
        i = 0
        n = len(pattern)

        while i < n:
            c = pattern[i]

            if c == '*':
                # 处理 ** 递归匹配
                if i + 1 < n and pattern[i + 1] == '*':
                    # 处理 /**
                    if i + 2 < n and pattern[i + 2] == '/':
                        regex += r'(?:[^/]+/)*'
                        i += 3
                    else:
                        regex += r'.*'
                        i += 2
                else:
                    regex += r'[^/]*'
                    i += 1
            elif c == '?':
                regex += r'[^/]'
                i += 1
            elif c == '[':
                # 处理字符集
                j = i + 1
                if j < n and pattern[j] == '!':
                    j += 1
                if j < n and pattern[j] == ']':
                    j += 1
                while j < n:
                    if pattern[j] == ']':
                        break
                    j += 1

                if j < n and pattern[j] == ']':
                    char_class = pattern[i:j + 1]
                    # 转换字符集为有效正则
                    char_class = char_class.replace('\\', '\\\\')
                    if char_class.startswith('[!'):
                        char_class = '[^' + char_class[2:]
                    regex += char_class
                    i = j + 1
                else:
                    regex += r'\['
                    i += 1
            elif c in r'.^$+()|{}':
                regex += '\\' + c
                i += 1
            else:
                regex += c
                i += 1

        # 处理完整路径匹配
        if not regex.startswith(r'[^/]*'):
            # 非绝对路径可以匹配任意层级
            regex = r'(?:^|/)' + regex

        # 处理结尾
        if not regex.endswith('/'):
            regex += r'(?:/.*)?$'
        else:
            regex += r'.*$'

        return regex


def ai_ignore_filter(changes: list, ai_ignore_content: str) -> list:
    """
    用change列表里的对象的`new_path`字段判断是否应该过滤
    """
    if ai_ignore_content:
        ai_ignore_filtered = []
        ai_ignore = AIIgnore(ai_ignore_content=ai_ignore_content)
        for line in changes:
            try:
                if not ai_ignore.is_ignored(line['new_path']):
                    ai_ignore_filtered.append(line)
            except Exception as e:
                print(f"Error while filtering ai_ignore: {str(e)}")
        return ai_ignore_filtered
    return changes
