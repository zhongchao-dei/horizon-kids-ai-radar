"""Daily summary generation — pure programmatic rendering."""

import html
import hashlib
import re
from typing import Dict, List, Literal, Optional, Set
from urllib.parse import quote, urlsplit

from ..models import ContentItem


_CJK = r"[\u4e00-\u9fff\u3400-\u4dbf]"
_ASCII = r"[A-Za-z0-9]"
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()<>#!|])")
_MARKDOWN_BLOCK_START = re.compile(r"(?m)^( {0,3})(>|[-+] |\d+[.)] )")
_URL_SAFE_CHARS = ":/?#[]@!$&'*,;=~%+"


def _escape_markdown(value: object) -> str:
    """Render untrusted text literally while retaining its readable content."""
    escaped = html.escape(str(value), quote=True)
    escaped = _MARKDOWN_SPECIAL.sub(r"\\\1", escaped)
    return _MARKDOWN_BLOCK_START.sub(r"\1\\\2", escaped)


def _safe_url(value: object) -> Optional[str]:
    """Return an HTML/Markdown-safe HTTP(S) URL, or None for unsafe URLs."""
    raw = str(value).strip()
    if not raw or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        parsed.port
    except (TypeError, ValueError):
        return None
    encoded = quote(raw, safe=_URL_SAFE_CHARS)
    return html.escape(encoded, quote=True)


def _pangu(text: str) -> str:
    """Insert a space between CJK and ASCII letters/digits (Pangu spacing)."""
    text = re.sub(rf"({_CJK})({_ASCII})", r"\1 \2", text)
    text = re.sub(rf"({_ASCII})({_CJK})", r"\1 \2", text)
    return text


LABELS = {
    "en": {
        "header": "Horizon Daily",
        "source": "Source",
        "background": "Background",
        "discussion": "Discussion",
        "references": "References",
        "tags": "Tags",
        "selected_items": "From {total} items, {selected} important content pieces were selected",
        "empty_analyzed": "Analyzed {total} items, but none met the importance threshold.",
        "empty_body": (
            "No significant developments today. This might indicate:\n"
            "- A quiet day in your tracked sources\n"
            "- The AI score threshold is too high\n"
            "- Your information sources need expansion\n\n"
            "Consider:\n"
            "1. Lowering the `ai_score_threshold` in config.json\n"
            "2. Adding more diverse information sources\n"
            "3. Checking if the AI model is working correctly\n"
        ),
    },
    "zh": {
        "header": "Horizon 每日速递",
        "source": "来源",
        "background": "背景",
        "discussion": "社区讨论",
        "references": "参考链接",
        "tags": "标签",
        "topic_card": "可选选题卡",
        "selected_items": "从 {total} 条内容中筛选出 {selected} 条重要资讯。",
        "empty_analyzed": "已分析 {total} 条内容，但没有达到重要性阈值的条目。",
        "empty_body": (
            "今日暂无重要动态，可能原因：\n"
            "- 今天关注的信息源较平静\n"
            "- AI 评分阈值设置过高\n"
            "- 信息源种类有待扩充\n\n"
            "建议：\n"
            "1. 在 config.json 中降低 `ai_score_threshold`\n"
            "2. 添加更多多样化的信息源\n"
            "3. 检查 AI 模型是否正常工作\n"
        ),
    },
}


class DailySummarizer:
    """Generates daily Markdown summaries from pre-analyzed content items."""

    def __init__(self):
        pass

    async def generate_summary(
        self,
        items: List[ContentItem],
        date: str,
        total_fetched: int,
        language: str = "en",
        audience: Optional[Literal["parent", "teacher"]] = None,
    ) -> str:
        """Generate daily summary in Markdown format.

        Items are rendered in score-descending order (already sorted by orchestrator).

        Args:
            items: High-scoring content items (already enriched)
            date: Date string (YYYY-MM-DD)
            total_fetched: Total number of items fetched before filtering
            language: Output language, either "en" or "zh"

        Returns:
            str: Markdown formatted summary
        """
        labels = LABELS.get(language, LABELS["en"])

        if not items:
            # A formal list can be empty while the same day's research queue
            # still contains high-value leads. Do not blame a score threshold
            # or tell the user to change configuration; the lead section is
            # appended by the orchestrator immediately after this header.
            if language == "zh":
                return (
                    f"# Horizon 每日速递 - {date}\n\n"
                    f"> 已分析 {total_fetched} 条内容；本日暂无已核验的正式选题。\n\n"
                    "> 请继续查看下方“高价值待核（重点追踪）”，不要把证据状态误读成选题价值。\n\n"
                    "---\n\n"
                )
            return (
                f"# Horizon Daily - {date}\n\n"
                f"> Analyzed {total_fetched} items; no evidence-complete formal topic today.\n\n"
                "> See the high-value research leads below; evidence status is not a value judgment.\n\n"
                "---\n\n"
            )

        header = (
            f"# {labels['header']} - {date}\n\n"
            f"> {labels['selected_items'].format(total=total_fetched, selected=len(items))}\n\n"
            "---\n\n"
        )

        # TOC
        toc_entries = []
        for i, item in enumerate(items):
            _t = item.metadata.get(f"title_{language}") or item.title
            t = _escape_markdown(_t)
            if language == "zh":
                t = _pangu(t)
            score = self._audience_score(item, audience)
            toc_entries.append(f"{i + 1}. [{t}](#item-{i + 1}) \u2b50\ufe0f {score}/10")
        toc = "\n".join(toc_entries) + "\n\n---\n\n"

        parts = [
            self._format_item(item, labels, language, i + 1, audience=audience)
            for i, item in enumerate(items)
        ]

        return header + toc + "".join(parts)

    def generate_research_leads(
        self,
        items: List[ContentItem],
        date: str,
        *,
        language: str = "zh",
        audience: Optional[Literal["parent", "teacher"]] = None,
    ) -> str:
        """Render enriched high-value leads that did not clear formal publication.

        A quiet formal-news day must not look like a broken radar.  These cards
        are usable as cases, background, or source-reading tasks, but their
        evidence boundary remains visible and they are never labelled formal
        daily topics.
        """
        if not items:
            return ""
        labels = LABELS.get(language, LABELS["en"])
        heading = (
            "## 高价值待核（重点追踪）\n\n"
            "> 以下内容的素材价值达到 7 分及以上，但原文、关键条款、实施细节或当天新增事实仍需确认。"
            "它们不是正式选题，不能直接当作已证实结论。\n\n"
            if language == "zh"
            else "## Developable research leads\n\n> These are enriched leads, not formal daily topics.\n\n"
        )
        parts = [
            self._format_item(
                item,
                labels,
                language,
                i + 1,
                audience=audience,
                card_heading_override=(
                    "高价值待核卡（重点追踪）" if language == "zh" else "High-value research lead"
                ),
            )
            for i, item in enumerate(items)
        ]
        return heading + "".join(parts)

    def generate_candidate_index(
        self,
        items: List[ContentItem],
        date: str,
        parent_selected_ids: Set[str],
        teacher_selected_ids: Set[str],
        language: str = "zh",
    ) -> str:
        """Render every deduplicated, scored candidate as a compact audit table."""
        if language != "zh":
            raise ValueError("The dual-audience candidate index currently supports zh only")

        sorted_items = sorted(
            items,
            key=lambda item: max(
                self._numeric_score(item.metadata.get("parent_score")),
                self._numeric_score(item.metadata.get("teacher_score")),
                self._numeric_score(item.ai_score),
            ),
            reverse=True,
        )
        lines = [
            f"# K12 AI 全部候选资讯｜{date}",
            "",
            (
                f"> 保存当天去重后进入 AI 评分阶段的 {len(sorted_items)} 条候选。"
                f"家长端入选 {len(parent_selected_ids)} 条，教师端入选 {len(teacher_selected_ids)} 条。"
            ),
            "",
            "> 未入选不等于无价值；本表用于回看筛选方向。标题和概述均为中文，链接仍指向原始来源；候选不会仅因未进入前 3—5 条而消失。",
            "",
            "| 候选 ID | 中文标题与概述（原文链接） | 来源 | 发布时间 | 分类 | 家长素材价值 | 教师素材价值 | 未入选／待观察原因 |",
            "|---|---|---|---|---|---|---|---|",
        ]

        for item in sorted_items:
            candidate_id = self._candidate_id(item)
            title = self._table_text(self._zh_title(item), limit=100)
            url = _safe_url(item.url)
            title_link = f"[{title}]({url})" if url else title
            overview = self._table_text(self._zh_summary(item), limit=160)
            title_and_overview = f"{title_link}<br>{overview}"
            meta = item.metadata
            source = meta.get("feed_name") or item.author or item.source_type.value
            source_text = self._table_text(source, limit=36)
            published = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "未知"
            category = self._table_text(meta.get("category") or "other", limit=28)

            parent_selected = item.id in parent_selected_ids
            teacher_selected = item.id in teacher_selected_ids
            parent_status = self._selection_status(
                meta.get("parent_score", item.ai_score), parent_selected
            )
            teacher_status = self._selection_status(
                meta.get("teacher_score", item.ai_score), teacher_selected
            )

            notes = []
            if not parent_selected:
                notes.append(
                    "家长：" + self._plain_text(
                        meta.get("parent_reason") or item.ai_reason or "相关性不足或排名未进入前列",
                        limit=58,
                    )
                )
            if not teacher_selected:
                notes.append(
                    "教师：" + self._plain_text(
                        meta.get("teacher_reason") or item.ai_reason or "相关性不足或排名未进入前列",
                        limit=58,
                    )
                )
            if not notes:
                notes.append("家长端、教师端均入选")
            note_text = self._table_text("；".join(notes), limit=130)

            lines.append(
                "| "
                + " | ".join(
                    [
                        candidate_id,
                        title_and_overview,
                        source_text,
                        published,
                        category,
                        parent_status,
                        teacher_status,
                        note_text,
                    ]
                )
                + " |"
            )

        return "\n".join(lines) + "\n"

    def generate_low_score_watchlist(
        self,
        items: List[ContentItem],
        date: str,
        parent_selected_ids: Set[str],
        teacher_selected_ids: Set[str],
        low_score_floor: float,
        language: str = "zh",
    ) -> str:
        """Render only unselected candidates that are low for both audiences."""
        if language != "zh":
            raise ValueError("The low-score watchlist currently supports zh only")

        low_items = [
            item
            for item in items
            if item.id not in parent_selected_ids
            and item.id not in teacher_selected_ids
            and max(
                self._numeric_score(item.metadata.get("parent_score", item.ai_score)),
                self._numeric_score(item.metadata.get("teacher_score", item.ai_score)),
            )
            < low_score_floor
        ]
        low_items.sort(
            key=lambda item: max(
                self._numeric_score(item.metadata.get("parent_score", item.ai_score)),
                self._numeric_score(item.metadata.get("teacher_score", item.ai_score)),
            ),
            reverse=True,
        )

        lines = [
            f"# K12 AI 低分待观察资讯｜{date}",
            "",
            (
                f"> 收录当天未进入家长端或教师端选题池，且两端评分均低于 "
                f"{low_score_floor:.1f} 分的 {len(low_items)} 条资讯。"
            ),
            "",
            "> 仅供回看方向，不进入长期知识页，也不代表内容错误或永远无价值。",
            "",
        ]

        if not low_items:
            lines.append("今天没有符合条件的低分待观察资讯。")
            return "\n".join(lines) + "\n"

        for index, item in enumerate(low_items, start=1):
            title = self._table_text(self._zh_title(item), limit=120)
            url = _safe_url(item.url)
            title_link = f"[{title}]({url})" if url else title
            overview = self._plain_text(
                self._zh_summary(item),
                limit=180,
            )
            lines.extend(
                [
                    f"## {index}. {title_link}",
                    "",
                    f"- 简要概述：{overview}",
                    "",
                ]
            )

        return "\n".join(lines).rstrip() + "\n"

    def generate_webhook_overview(
        self,
        items: List[ContentItem],
        date: str,
        total_fetched: int,
        language: str = "en",
    ) -> str:
        """Generate a compact overview for multi-message webhook delivery."""
        labels = LABELS.get(language, LABELS["en"])
        if not items:
            return self._generate_empty_summary(date, total_fetched, labels)

        if language == "zh":
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"> 从 {total_fetched} 条内容中筛选出 {len(items)} 条重要资讯。\n\n"
                "下面会按新闻逐条发送详情，你可以只看感兴趣的标题。\n\n"
            )
        else:
            header = (
                f"# {labels['header']} - {date}\n\n"
                f"> Selected {len(items)} important items from {total_fetched} fetched items.\n\n"
                "Details will be sent item by item so you can read only the topics you care about.\n\n"
            )

        entries = []
        for i, item in enumerate(items, start=1):
            title = _escape_markdown(item.metadata.get(f"title_{language}") or item.title)
            if language == "zh":
                title = _pangu(title)
            score = item.ai_score or "?"
            url = _safe_url(item.url)
            title_link = f"[{title}]({url})" if url else title
            entries.append(f"{i}. {title_link} \u2b50\ufe0f {score}/10")

        return header + "\n".join(entries)

    def generate_webhook_item(
        self,
        item: ContentItem,
        language: str,
        index: int,
        total: int,
    ) -> str:
        """Generate one item message for multi-message webhook delivery."""
        labels = LABELS.get(language, LABELS["en"])
        prefix = f"第 {index}/{total} 条\n\n" if language == "zh" else f"Item {index}/{total}\n\n"
        return prefix + self._format_item(item, labels, language, index).rstrip("-\n ")

    def _format_item(
        self,
        item: ContentItem,
        labels: dict,
        language: str,
        index: int,
        audience: Optional[Literal["parent", "teacher"]] = None,
        card_heading_override: Optional[str] = None,
    ) -> str:
        """Format a single ContentItem into Markdown."""
        _title = (
            self._zh_title(item)
            if language == "zh"
            else item.metadata.get(f"title_{language}") or item.title
        )
        title = _escape_markdown(_title)
        raw_url = str(item.url)
        url = _safe_url(raw_url)
        score = self._audience_score(item, audience)
        meta = item.metadata

        summary = (
            self._zh_summary(item)
            if language == "zh"
            else meta.get(f"detailed_summary_{language}")
            or meta.get("detailed_summary")
            or item.ai_summary
            or ""
        )
        background = meta.get(f"background_{language}") or meta.get("background") or ""
        discussion = (
            meta.get(f"community_discussion_{language}")
            or meta.get("community_discussion")
            or ""
        )

        summary = _escape_markdown(summary)
        background = _escape_markdown(background)
        discussion = _escape_markdown(discussion)

        if language == "zh":
            title = _pangu(title)
            summary = _pangu(summary)
            background = _pangu(background)
            discussion = _pangu(discussion)

        # Source line with parts joined by " · ", link appended at end
        source_type = item.source_type.value
        source_parts = [_escape_markdown(source_type)]
        if meta.get("subreddit"):
            source_parts.append(_escape_markdown(f"r/{meta['subreddit']}"))
        if meta.get("feed_name"):
            source_parts.append(_escape_markdown(meta["feed_name"]))
        else:
            source_parts.append(_escape_markdown(item.author or "unknown"))
        if item.published_at:
            if language == "zh":
                source_parts.append(
                    f"{item.published_at.month}月{item.published_at.day}日 "
                    f"{item.published_at:%H:%M}"
                )
            else:
                day = item.published_at.strftime("%d").lstrip("0")
                source_parts.append(item.published_at.strftime(f"%b {day}, %H:%M"))
        source_line = " \u00b7 ".join(source_parts)  # ·

        discussion_url = meta.get("discussion_url")
        if discussion_url:
            safe_discussion_url = _safe_url(discussion_url)
            if safe_discussion_url and str(discussion_url) != raw_url:
                source_line += f' · [{labels["discussion"]}]({safe_discussion_url})'

        title_link = f"[{title}]({url})" if url else title

        lines = [
            f'<a id="item-{index}"></a>',
            f"## {title_link} \u2b50\ufe0f {score}/10",  # ⭐️
            "",
            summary,
            "",
            source_line,
        ]

        topic_fields = self._topic_fields(audience)
        topic_title_field = topic_fields[0][1] if topic_fields else None
        if language == "zh" and topic_title_field and meta.get(topic_title_field):
            card_heading = card_heading_override or (
                "教师端正式选题卡"
                if audience == "teacher"
                else "家长端正式选题卡"
                if audience == "parent"
                else labels["topic_card"]
            )
            lines.extend(["", f"### {card_heading}"])
            for label, field in topic_fields:
                value = meta.get(field)
                if value:
                    rendered = _pangu(_escape_markdown(value))
                    lines.append(f"- **{label}**：{rendered}")

        if background:
            lines.append("")
            lines.append(f"**{labels['background']}**: {background}")

        sources = meta.get("sources") or []
        if sources:
            reference_items = []
            for source in sources:
                reference_title = html.escape(str(source.get("title", "")), quote=True)
                reference_url = _safe_url(source.get("url", ""))
                if reference_url:
                    reference_items.append(f'<li><a href="{reference_url}">{reference_title}</a></li>\n')
                else:
                    reference_items.append(f"<li>{reference_title}</li>\n")
            items_html = "".join(reference_items)
            lines += [
                "",
                f'<details><summary>{labels["references"]}</summary>\n<ul>\n{items_html}\n</ul>\n</details>',
            ]

        if discussion:
            lines.append("")
            lines.append(f"**{labels['discussion']}**: {discussion}")

        if item.ai_tags:
            tags_str = ", ".join([f"`#{_escape_markdown(t)}`" for t in item.ai_tags])
            lines.append("")
            lines.append(f"**{labels['tags']}**: {tags_str}")

        lines.append("")
        lines.append("---")

        return "\n".join(lines) + "\n\n"

    @staticmethod
    def _numeric_score(value: object) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _audience_score(
        self,
        item: ContentItem,
        audience: Optional[Literal["parent", "teacher"]],
    ) -> object:
        if audience:
            value = item.metadata.get(f"{audience}_score")
            if value is not None:
                return value
        return item.ai_score if item.ai_score is not None else "?"

    @staticmethod
    def _topic_fields(
        audience: Optional[Literal["parent", "teacher"]],
    ) -> tuple[tuple[str, str], ...]:
        if audience == "teacher":
            return (
                ("这条新闻讲什么", "teacher_topic_context_zh"),
                ("标题", "teacher_topic_title_zh"),
                ("今天的新意", "teacher_why_now"),
                ("入口", "teacher_topic_entry_zh"),
                ("钩子", "teacher_topic_hook_zh"),
                ("关键事实", "teacher_key_fact_zh"),
                ("教学环节", "teaching_stage_zh"),
                ("教师真实任务", "teacher_task_zh"),
                ("AI 具体介入", "teacher_ai_intervention_zh"),
                ("真正过程问题", "teacher_process_problem_zh"),
                ("教师判断／动作", "teacher_action_zh"),
                ("学生可见证据", "student_evidence_zh"),
                ("课程连接", "teacher_course_connection_zh"),
                ("内容目标", "teacher_content_goal_zh"),
                ("证据成熟度", "teacher_evidence_maturity_zh"),
                ("适用边界", "teacher_suitability_note_zh"),
            )
        return (
            ("这条新闻讲什么", "topic_context_zh"),
            ("标题", "topic_title_zh"),
            ("今天的新意", "parent_why_now"),
            ("入口", "topic_entry_zh"),
            ("钩子", "topic_hook_zh"),
            ("关键事实", "key_fact_zh"),
            ("真实场景", "parent_real_scene_zh"),
            ("AI 具体介入", "parent_ai_intervention_zh"),
            ("真正过程问题", "process_problem_zh"),
            ("因果链", "causal_chain_zh"),
            ("可见证据", "visible_evidence_zh"),
            ("家长判断", "parent_judgment_zh"),
            ("课程连接", "course_connection_zh"),
            ("内容目标", "content_goal_zh"),
            ("证据成熟度", "parent_evidence_maturity_zh"),
            ("适用边界", "suitability_note_zh"),
        )

    @staticmethod
    def _candidate_id(item: ContentItem) -> str:
        digest = hashlib.sha1(str(item.url).encode("utf-8")).hexdigest()[:10]
        return f"CAND-{digest}"

    @staticmethod
    def _plain_text(value: object, limit: int) -> str:
        text = re.sub(r"\s+", " ", str(value)).strip()
        if len(text) > limit:
            text = text[: max(0, limit - 1)].rstrip() + "…"
        return text

    @classmethod
    def _table_text(cls, value: object, limit: int) -> str:
        return _escape_markdown(cls._plain_text(value, limit))

    @staticmethod
    def _zh_title(item: ContentItem) -> str:
        return str(item.metadata.get("title_zh") or "中文标题待补译")

    @staticmethod
    def _zh_summary(item: ContentItem) -> str:
        return str(
            item.metadata.get("detailed_summary_zh")
            or item.metadata.get("summary_zh")
            or "中文概述待补译，请查看原文链接。"
        )

    @classmethod
    @classmethod
    def _selection_status(cls, score: object, selected: bool) -> str:
        numeric = cls._numeric_score(score)
        if selected:
            label = "\u5165\u9009"
        elif numeric >= 7:
            label = "\u9ad8\u4ef7\u503c\u5f85\u6838"
        else:
            label = "\u5f85\u89c2\u5bdf"
        return f"{label} {numeric:.1f}"
    def _generate_empty_summary(self, date: str, total_fetched: int, labels: dict) -> str:
        """Generate summary when no high-scoring items were found."""
        return (
            f"# {labels['header']} - {date}\n\n"
            f"> {labels['empty_analyzed'].format(total=total_fetched)}\n\n"
            + labels["empty_body"]
        )
