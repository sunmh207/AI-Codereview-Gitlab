import re
import shutil
import stat
import subprocess
import tempfile

from biz.utils.log import logger


def _build_authed_url(git_http_url: str, token: str) -> str:
    """将 token 注入 http(s) 克隆地址，用于私有仓库免交互克隆。"""
    if not token:
        return git_http_url
    # https://gitlab.example.com/g/p.git -> https://oauth2:<token>@gitlab.example.com/g/p.git
    return re.sub(r"^(https?://)", rf"\1oauth2:{token}@", git_http_url, count=1)


def _run_git(args: list, cwd: str = None):
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        # 避免把带 token 的 URL 打进日志
        raise RuntimeError(f"git {' '.join(a for a in args if '@' not in a)} 失败: {result.stderr.strip()}")
    return result.stdout


def _on_rm_error(func, path, exc_info):
    """Windows 上删除 .git 只读对象时的兜底。"""
    try:
        import os
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def clone_branches_for_review(git_http_url: str, token: str, source_branch: str, target_branch: str):
    """
    将仓库以 blobless 方式克隆到临时目录，准备好 source/target 两个分支，
    返回 (repo_dir, diff_range)。调用方负责用 cleanup_repo(repo_dir) 清理。

    diff_range 形如 'origin/main...origin/feature'，即 MR 在 source 分支上相对
    target 的增量改动，供 skill 的 `git diff <range>` 使用。
    """
    repo_dir = tempfile.mkdtemp(prefix="cr_skill_")
    authed = _build_authed_url(git_http_url, token)
    try:
        # blobless 部分克隆：保留完整历史(用于 merge-base)但按需拉取文件内容，省时省盘
        _run_git(["clone", "--filter=blob:none", "--no-single-branch", authed, repo_dir])
        _run_git(["fetch", "origin", source_branch, target_branch], cwd=repo_dir)
        # 检出 source 分支，使 skill 能读取工作区文件
        _run_git(["checkout", source_branch], cwd=repo_dir)
        diff_range = f"origin/{target_branch}...origin/{source_branch}"
        logger.info(f"已克隆仓库用于 skill 审查: {repo_dir}, range={diff_range}")
        return repo_dir, diff_range
    except Exception:
        cleanup_repo(repo_dir)
        raise


def cleanup_repo(repo_dir: str):
    if repo_dir:
        shutil.rmtree(repo_dir, ignore_errors=False, onerror=_on_rm_error)
