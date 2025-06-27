import re


class GitDiffParser:
    def __init__(self, diff_string):
        self.diff_string = diff_string
        self.old_code = None
        self.new_code = None

    def parse_diff(self):
        old_code = []
        new_code = []

        diff_lines = self.diff_string.splitlines()
        parsing_old_code = False
        parsing_new_code = False

        for line in diff_lines:
            # Identify the diff sections
            if line.startswith('@@'):
                parsing_old_code = False
                parsing_new_code = False
            elif line.startswith('-'):
                old_code.append(line[1:])  # Remove the leading '-' which indicates removal
                parsing_old_code = True
            elif line.startswith('+'):
                new_code.append(line[1:])  # Remove the leading '+' which indicates addition
                parsing_new_code = True
            else:
                if parsing_old_code:
                    old_code.append(line)
                if parsing_new_code:
                    new_code.append(line)

        self.old_code = '\n'.join(old_code)
        self.new_code = '\n'.join(new_code)

    def get_old_code(self):
        if self.old_code is None:
            self.parse_diff()
        return self.old_code

    def get_new_code(self):
        if self.new_code is None:
            self.parse_diff()
        return self.new_code


def parse_single_file_diff(diff_text, file_path, old_file_path=None):
    """
        解析单个文件的 unified diff 格式文本，提取变更信息。
        返回包含该文件变更详情和上下文的字典。
        """
    file_changes = {
        "path": file_path,
        "old_path": old_file_path,
        "changes": [],
        "context": {"old": [], "new": []},
        "lines_changed": 0
    }

    old_line_num_current = 0
    new_line_num_current = 0
    hunk_context_lines = []

    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith('--- ') or line.startswith('+++ '):
            i += 1
            continue
        elif line.startswith('@@ '):
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                old_line_num_start = int(match.group(1))
                new_line_num_start = int(match.group(3))
                old_line_num_current = old_line_num_start
                new_line_num_current = new_line_num_start
                if hunk_context_lines:  # 将上一个 hunk 的上下文添加到 file_changes
                    file_changes["context"]["old"].extend(hunk_context_lines)
                    file_changes["context"]["new"].extend(hunk_context_lines)
                    hunk_context_lines = []  # 为新的 hunk 重置
            else:
                old_line_num_current = 0
                new_line_num_current = 0
        elif line.startswith('+'):
            file_changes["changes"].append({
                "type": "add",
                "old_line": None,
                "new_line": new_line_num_current,
                "content": line[1:]
            })
            new_line_num_current += 1
        elif line.startswith('-'):
            file_changes["changes"].append({
                "type": "delete",
                "old_line": old_line_num_current,
                "new_line": None,
                "content": line[1:]
            })
            old_line_num_current += 1
        elif line.startswith(' '):  # Context line
            hunk_context_lines.append(f"{old_line_num_current} -> {new_line_num_current}: {line[1:]}")
            old_line_num_current += 1
            new_line_num_current += 1
        i += 1

    if hunk_context_lines:  # 添加最后一个 hunk 的上下文
        file_changes["context"]["old"].extend(hunk_context_lines)
        file_changes["context"]["new"].extend(hunk_context_lines)

    limit = 20  # 限制上下文行数
    file_changes["context"]["old"] = "\n".join(file_changes["context"]["old"][-limit:])
    file_changes["context"]["new"] = "\n".join(file_changes["context"]["new"][-limit:])
    file_changes["lines_changed"] = len([c for c in file_changes["changes"] if c['type'] in ['add', 'delete']])

    return file_changes
