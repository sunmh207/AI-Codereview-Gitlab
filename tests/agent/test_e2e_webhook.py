from unittest.mock import patch

import pytest

from biz.queue.worker import _review_with_strategy


GL_PAYLOAD = {
    "object_kind": "merge_request",
    "project": {"name": "g/p", "path_with_namespace": "g/p", "git_http_url": "http://x/g/p.git"},
    "object_attributes": {
        "iid": 1,
        "target_project_id": 1,
        "action": "open",
        "source_branch": "feat",
        "target_branch": "main",
        "last_commit": {"id": "deadbeef"},
        "url": "http://x/g/p/-/merge_requests/1",
    },
    "user": {"username": "u"},
}


class TestWebhookStrategy:
    def test_diff_only_default(self, monkeypatch):
        monkeypatch.setenv("REVIEW_STRATEGY", "diff_only")
        with patch("biz.queue.worker.CodeReviewer") as MockCR:
            MockCR.return_value.review_and_strip_code.return_value = "DIFF_ONLY"
            out = _review_with_strategy(
                changes=[],
                commits_text="c",
                webhook_data=GL_PAYLOAD,
                gitlab_url="http://x",
            )
            assert out == "DIFF_ONLY"
            MockCR.return_value.review_and_strip_code.assert_called_once()

    def test_agentic_branch_routes_to_reviewer(self, monkeypatch):
        monkeypatch.setenv("REVIEW_STRATEGY", "agentic")
        with patch("biz.queue.worker.CodeReviewer") as MockCR:
            MockCR.return_value.review_and_strip_code.return_value = "DIFF_ONLY_FALLBACK"
            with patch("biz.agent.agentic_reviewer.AgenticReviewer") as MockAR:
                MockAR.return_value.review.return_value = "AGENTIC_OK"
                out = _review_with_strategy(
                    changes=["+ x"],
                    commits_text="c",
                    webhook_data=GL_PAYLOAD,
                    gitlab_url="http://x",
                )
                assert out == "AGENTIC_OK"
                MockAR.assert_called_once()


GL_PUSH_PAYLOAD = {
    "object_kind": "push",
    "ref": "refs/heads/main",
    "before": "0000000000000000000000000000000000000000",
    "after": "abcdef1234567890",
    "user_username": "u",
    "project": {
        "name": "g/p",
        "path_with_namespace": "g/p",
        "git_http_url": "http://x/g/p.git",
    },
    "commits": [],
}


class TestGitLabPushAgentic:
    def test_push_payload_routes_to_agentic_reviewer(self, monkeypatch):
        """GitLab push events must resolve to (url, key, ref) so agentic mode kicks in.

        Regression: previously the GitLab branch in _resolve_repo_for_event
        returned (None, None, None) for push events because it read MR-only
        fields (object_attributes.source_branch / last_commit.id).
        """
        monkeypatch.setenv("REVIEW_STRATEGY", "agentic")
        with patch("biz.queue.worker.CodeReviewer") as MockCR:
            MockCR.return_value.review_and_strip_code.return_value = "DIFF_ONLY_FALLBACK"
            with patch("biz.agent.agentic_reviewer.AgenticReviewer") as MockAR:
                MockAR.return_value.review.return_value = "AGENTIC_OK"
                out = _review_with_strategy(
                    changes=["+ x"],
                    commits_text="c",
                    webhook_data=GL_PUSH_PAYLOAD,
                    gitlab_url="http://x",
                )
                assert out == "AGENTIC_OK", "expected agentic routing, not diff_only fallback"
                MockAR.assert_called_once_with(
                    repo_url="http://x/g/p.git",
                    repo_key="g/p",
                    ref="abcdef1234567890",
                    cache_root="data/repo_cache",
                )
