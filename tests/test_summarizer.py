"""Unit tests for daily summary rendering."""

import asyncio
from datetime import datetime, timezone

from src.ai.summarizer import DailySummarizer
from src.models import ContentItem, SourceType


def _run_async(coro):
    return asyncio.run(coro)


def _make_item(idx: int) -> ContentItem:
    item = ContentItem(
        id=f"rss:item-{idx}",
        source_type=SourceType.RSS,
        title=f"Important Item {idx}",
        url=f"https://example.com/items/{idx}",
        content="content",
        author="tester",
        published_at=datetime(2026, 4, 25, 8, 0, tzinfo=timezone.utc),
    )
    item.ai_score = 8.0
    item.ai_summary = f"Summary for item {idx}."
    item.ai_tags = ["AI", "News"]
    return item


def test_generate_webhook_overview_lists_items_without_full_details():
    summarizer = DailySummarizer()
    items = [_make_item(1), _make_item(2)]

    result = summarizer.generate_webhook_overview(
        items,
        date="2026-04-25",
        total_fetched=10,
        language="en",
    )

    assert "Selected 2 important items from 10 fetched items" in result
    assert "1. [Important Item 1](https://example.com/items/1)" in result
    assert "2. [Important Item 2](https://example.com/items/2)" in result
    assert "Summary for item 1." not in result


def test_generate_webhook_item_renders_single_item_detail():
    summarizer = DailySummarizer()

    result = summarizer.generate_webhook_item(
        _make_item(1),
        language="en",
        index=1,
        total=2,
    )

    assert result.startswith("Item 1/2")
    assert "## [Important Item 1](https://example.com/items/1)" in result
    assert "Summary for item 1." in result
    assert "**Tags**: `#AI`, `#News`" in result


def test_generate_webhook_item_includes_discussion_link_when_distinct():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata["discussion_url"] = "https://news.ycombinator.com/item?id=1"

    result = summarizer.generate_webhook_item(
        item,
        language="en",
        index=1,
        total=1,
    )

    assert "tester · Apr 25, 08:00 · [Discussion](https://news.ycombinator.com/item?id=1)" in result


def test_generate_webhook_item_omits_discussion_link_when_same_as_item_url():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata["discussion_url"] = item.url

    result = summarizer.generate_webhook_item(
        item,
        language="en",
        index=1,
        total=1,
    )

    assert "[Discussion](https://example.com/items/1)" not in result


def test_generate_webhook_item_uses_localized_discussion_label():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata["discussion_url"] = "https://www.reddit.com/r/python/comments/abc123/test/"

    result = summarizer.generate_webhook_item(
        item,
        language="zh",
        index=1,
        total=1,
    )

    assert "[社区讨论](https://www.reddit.com/r/python/comments/abc123/test/)" in result


def test_generate_summary_zh_uses_localized_selection_header_and_numeric_date():
    summarizer = DailySummarizer()
    item = _make_item(1)

    result = _run_async(
        summarizer.generate_summary(
            [item],
            date="2026-04-25",
            total_fetched=10,
            language="zh",
        )
    )

    assert "> 从 10 条内容中筛选出 1 条重要资讯。" in result
    assert "rss · tester · 4月25日 08:00" in result
    assert "From 10 items" not in result
    assert "Apr 25, 08:00" not in result


def test_generate_summary_zh_renders_complete_topic_card():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata.update(
        {
            "topic_title_zh": "孩子交上 AI 作业后，为什么还要讲一遍思路",
            "topic_entry_zh": "作业协作、家长介入",
            "topic_hook_zh": "作业答案全对，孩子却说不清第一步。",
            "key_fact_zh": "来源显示，部分课堂正在使用生成式 AI 辅助作业。",
            "parent_real_scene_zh": "孩子为了完成当天作业，请 AI 直接给出答案。",
            "parent_ai_intervention_zh": "AI 先替孩子完成了解题和表述。",
            "process_problem_zh": "孩子跳过了理解和验证。",
            "causal_chain_zh": "完成作业→让 AI 给答案→无法解释→补回验证",
            "visible_evidence_zh": "让孩子不用看答案讲出第一步。",
            "parent_judgment_zh": "家长只核对孩子能否解释方法。",
            "course_connection_zh": "不建议本条明显露出课程",
            "content_goal_zh": "认知",
            "parent_evidence_maturity_zh": "可开发",
            "suitability_note_zh": "可讲使用边界，不能推断所有学生都依赖 AI。",
        }
    )

    result = _run_async(
        summarizer.generate_summary(
            [item],
            date="2026-04-25",
            total_fetched=10,
            language="zh",
        )
    )

    assert "### 可选选题卡" in result
    assert "**标题**：孩子交上 AI 作业后" in result
    assert "**真实场景**：孩子为了完成当天作业" in result
    assert "**AI 具体介入**：AI 先替孩子完成了解题和表述。" in result
    assert "**真正过程问题**：孩子跳过了理解和验证。" in result
    assert "**证据成熟度**：可开发" in result
    assert "**适用边界**：可讲使用边界" in result


def test_generate_summary_zh_renders_teacher_topic_card_with_teacher_score():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata.update(
        {
            "parent_score": 5.5,
            "teacher_score": 9.0,
            "teacher_topic_title_zh": "AI 三分钟生成教案，老师最不能省掉哪一步",
            "teacher_topic_entry_zh": "备课与教学设计",
            "teacher_topic_hook_zh": "教案很完整，教学目标却不适合本班学生。",
            "teacher_key_fact_zh": "来源只确认工具可以生成教学材料。",
            "teaching_stage_zh": "备课",
            "teacher_task_zh": "根据本班学情设计一节课。",
            "teacher_ai_intervention_zh": "AI 先生成教案初稿和活动建议。",
            "teacher_process_problem_zh": "把目标和评价标准也交给了 AI。",
            "teacher_action_zh": "先确定学生起点和本课评价证据。",
            "student_evidence_zh": "学生能否解释并迁移到新任务。",
            "teacher_course_connection_zh": "不建议本条明显露出课程",
            "teacher_content_goal_zh": "认知",
            "teacher_evidence_maturity_zh": "可开发",
            "teacher_suitability_note_zh": "只适用于有人工审核的备课场景。",
        }
    )

    result = _run_async(
        summarizer.generate_summary(
            [item],
            date="2026-07-31",
            total_fetched=32,
            language="zh",
            audience="teacher",
        )
    )

    assert "### 教师端正式选题卡" in result
    assert "⭐️ 9.0/10" in result
    assert "**教学环节**：备课" in result
    assert "**AI 具体介入**：AI 先生成教案初稿和活动建议。" in result
    assert "**学生可见证据**" in result
    assert "**证据成熟度**：可开发" in result
    assert "家长判断" not in result


def test_generate_candidate_index_keeps_unselected_titles_and_links():
    summarizer = DailySummarizer()
    selected = _make_item(1)
    selected.metadata.update(
        {
            "title_zh": "重要事项一",
            "summary_zh": "这是第一条中文概述。",
            "parent_score": 8.0,
            "parent_reason": "适合家庭作业场景。",
            "teacher_score": 9.0,
            "teacher_reason": "适合课堂评价场景。",
            "category": "k12-practice",
        }
    )
    unselected = _make_item(2)
    unselected.metadata.update(
        {
            "title_zh": "重要事项二",
            "summary_zh": "这是第二条中文概述。",
            "parent_score": 4.0,
            "parent_reason": "缺少家庭场景。",
            "teacher_score": 5.0,
            "teacher_reason": "只有通用办公功能。",
            "category": "ai-products",
        }
    )

    result = summarizer.generate_candidate_index(
        [selected, unselected],
        "2026-07-31",
        {selected.id},
        {selected.id},
    )

    assert "进入 AI 评分阶段的 2 条候选" in result
    assert "家长端入选 1 条，教师端入选 1 条" in result
    assert "[重要事项二](https://example.com/items/2)" in result
    assert "这是第二条中文概述。" in result
    assert "Important Item 2" not in result
    assert "家长：缺少家庭场景" in result
    assert "教师：只有通用办公功能" in result
    assert result.count("CAND-") == 2


def test_generate_low_score_watchlist_keeps_only_both_low_unselected_items():
    summarizer = DailySummarizer()
    selected = _make_item(1)
    selected.metadata.update({"parent_score": 8.0, "teacher_score": 8.0})
    low = _make_item(2)
    low.ai_summary = "这是一条可留作方向回看的低分资讯。"
    low.metadata.update({"parent_score": 4.0, "teacher_score": 5.5})
    one_side_relevant = _make_item(3)
    one_side_relevant.metadata.update({"parent_score": 7.0, "teacher_score": 3.0})

    result = summarizer.generate_low_score_watchlist(
        [selected, low, one_side_relevant],
        "2026-08-01",
        {selected.id},
        {selected.id},
        low_score_floor=6.0,
    )

    assert "低于 6.0 分的 1 条资讯" in result
    assert "[Important Item 2](https://example.com/items/2)" in result
    assert "可留作方向回看的低分资讯" in result
    assert "Important Item 3" not in result


def test_generate_empty_summary_zh_uses_localized_analyzed_line():
    summarizer = DailySummarizer()

    result = _run_async(
        summarizer.generate_summary(
            [],
            date="2026-04-25",
            total_fetched=10,
            language="zh",
        )
    )

    assert "> 已分析 10 条内容，但没有达到重要性阈值的条目。" in result
    assert "Analyzed 10 items" not in result


def test_generate_summary_escapes_untrusted_text_in_all_output_contexts():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.title = '<script>alert("title")</script> [click](javascript:alert(1))'
    item.ai_summary = '<img src=x onerror="alert(1)"> **summary**'
    item.author = '<svg onload="alert(1)">'
    item.ai_tags = ['tag`](javascript:alert(1))']
    item.metadata.update(
        {
            "feed_name": '<b onclick="alert(1)">feed</b>',
            "background": '<iframe src="data:text/html,bad"></iframe>',
            "community_discussion": '[bad](data:text/html,bad)',
            "sources": [{"title": '<img src=x onerror="alert(1)">', "url": "https://example.com/ref"}],
        }
    )

    result = _run_async(summarizer.generate_summary([item], "2026-04-25", 1))

    assert "<script>" not in result
    assert "<img src=x" not in result
    assert "<iframe" not in result
    assert "<b onclick" not in result
    assert "](javascript:" not in result
    assert "](data:text/html" not in result
    assert "&lt;script&gt;" in result
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in result


def test_generate_summary_rejects_unsafe_urls_and_quote_injection():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata.update(
        {
            "discussion_url": 'javascript:alert("discussion")',
            "sources": [
                {"title": 'Quoted "><script>alert(1)</script>', "url": 'https://example.com/\" onmouseover=\"alert(1)'},
                {"title": "JavaScript", "url": "javascript:alert(1)"},
                {"title": "Data", "url": "data:text/html,<script>alert(1)</script>"},
            ],
        }
    )

    result = _run_async(summarizer.generate_summary([item], "2026-04-25", 1))

    assert 'href="https://example.com/%22%20onmouseover=%22alert%281%29"' in result
    assert '<li>JavaScript</li>' in result
    assert '<li>Data</li>' in result
    assert 'href="javascript:' not in result
    assert 'href="data:' not in result
    assert '<script>' not in result


def test_generate_summary_preserves_normal_http_links():
    summarizer = DailySummarizer()
    item = _make_item(1)
    item.metadata.update(
        {
            "discussion_url": "https://example.com/discuss?id=1#comments",
            "sources": [{"title": "Useful reference", "url": "https://docs.example.com/path?q=one&lang=en"}],
        }
    )

    result = _run_async(summarizer.generate_summary([item], "2026-04-25", 1))

    assert "[Important Item 1](https://example.com/items/1)" in result
    assert "[Discussion](https://example.com/discuss?id=1#comments)" in result
    assert 'href="https://docs.example.com/path?q=one&amp;lang=en"' in result
