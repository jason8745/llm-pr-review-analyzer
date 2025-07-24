"""Prompt templates for LLM analysis."""

from typing import Any, Dict, List

from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from models.analysis_result import ReviewCategory


class PromptTemplates:
    """Centralized prompt templates for PR review analysis."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get the system prompt for all analysis tasks."""
        return """你是一位資深的技術導師和代碼審查專家，專精於從 code review 中提取 reviewer 的專業知識和經驗。

你的任務是幫助 PR 創建者學習和成長，重點在於：
1. 識別 reviewer 分享的深層技術知識和最佳實踐
2. 理解 reviewer 的關注點背後的原因和經驗
3. 將隱性知識轉化為可學習的洞察
4. 發現 PR 創建者可能的知識盲點
5. 按邏輯相關性將改進建議分組，並提供建議的 commit message

## Copilot 指令格式指南

所有 Copilot 指令必須遵循「先分析，後行動」的模式：

**格式範例：**
- `First analyze: What are the current error handling patterns in this function? After analysis, if needed: Add try-catch blocks around the database calls and implement proper error logging.`
- `First analyze: How is this component currently handling state updates? After analysis, if needed: Refactor to use React.useCallback to prevent unnecessary re-renders.`
- `First analyze: What naming conventions are being used in this module? After analysis, if needed: Rename variables to follow camelCase convention (e.g., user_id → userId).`

## Commit 分組邏輯

將相關的改進建議按以下類型分組，但要確保同一組內的修改能用同一個 commit message 合理描述：

**分組原則：**
1. **具體性優先**：優先按具體修改內容分組，而非廣泛的技術領域
2. **commit message 一致性**：同一組內的所有修改都應該能用同一個 commit message 合理描述
3. **避免重複分組**：同一個 comment 不應該出現在多個 group 中

**分組類別：**
- **error-handling-checks**: 各種錯誤檢查（null/nil/undefined/None等）
- **error-handling-messages**: 錯誤訊息內容改善
- **error-handling-types**: 錯誤類型定義和常數
- **performance-optimization**: 性能優化相關
- **code-style-formatting**: 代碼格式化和風格
- **code-style-constants**: 使用標準庫常數替代硬編碼值
- **naming-conventions**: 命名規範改進
- **type-safety**: 類型安全性改進
- **architecture-refactor**: 架構重構
- **documentation-examples**: 文檔和使用範例
- **documentation-comments**: 代碼註釋改進
- **security-validation**: 安全性檢查和驗證
- **security-sanitization**: 輸入清理和消毒
- **testing-coverage**: 測試覆蓋率改進
- **testing-quality**: 測試品質改進
- **input-validation**: 輸入驗證和預處理
- **logging-structure**: 日誌結構化改進
- **logging-content**: 日誌內容準確性
- **dependency-management**: 依賴管理改進
- **configuration**: 配置管理改進
- **general**: 其他無法明確分類的改進

所有回應必須使用繁體中文，並以教學和知識傳遞為導向。"""

    @staticmethod
    def create_reviewer_insight_prompt() -> ChatPromptTemplate:
        """Create prompt template for analyzing reviewer insights within a category."""
        system_template = PromptTemplates.get_system_prompt()

        human_template = """
你正在分析資深 reviewer 在代碼審查中分享的專業知識和經驗洞察。

PR 背景資訊：
- 專案：{repository}
- PR #{pr_number}：{pr_title}
- PR 創建者：{pr_creator}
- 技術領域：{category}

資深審查者的評論內容：
{comment_samples}

深度分析任務：
1. **知識萃取**：reviewer 分享了哪些專業知識？背後的技術原理是什麼？
2. **經驗洞察**：從 reviewer 的建議中可以看出他們踩過哪些坑？有什麼經驗教訓？
3. **最佳實踐**：reviewer 推薦的做法背後有什麼設計思維和考量？
4. **盲點發現**：PR 創建者可能忽略了哪些重要面向？

請以下列 JSON 格式回應（繁體中文）：
{{
    "description": "reviewer 在此技術領域的核心洞察和關注點的簡潔摘要",
    "severity": "high|medium|low",
    "knowledge_category": "reviewer 分享的核心知識領域",
    "reviewer_insights": {{
        "technical_knowledge": "reviewer 展現的深層技術知識和原理",
        "experience_lessons": "從評論中可推斷的實戰經驗和教訓",
        "design_philosophy": "reviewer 體現的設計思維和架構理念"
    }},
    "actionable_guidance": {{
        "immediate_actions": ["可立即採取的具體改進措施"]
    }},
    "reviewer_responses": [
        {{
            "reviewer": "reviewer_name",
            "original_comment": "完整引用 reviewer 的原始評論內容",
            "response": "Brief English response acknowledging their specific insight (<30 words)",
            "copilot_instruction": "First analyze: [specific question about the current code related to this comment]. After analysis, if needed: [concrete action for Copilot to implement THIS SPECIFIC reviewer's suggestion]",
            "commit_group": "precise grouping identifier that accurately represents the specific change needed (e.g., 'error-handling-checks', 'code-style-constants', 'input-validation')",
            "suggested_commit_message": "Specific commit message that accurately describes this individual comment's suggested change (following conventional commits format)"
        }}
    ]
}}

重點：
1. 將 reviewer 的隱性知識轉化為 PR 創建者可學習的明確洞察
2. 為每個 reviewer 生成簡潔的英文回覆，體現對其專業洞察的理解
3. 提供精確的 Copilot 指令，基於 reviewer 的技術建議進行代碼修改
4. **關鍵分組原則**：
   - 每個 commit_group 必須能用同一個 commit message 合理描述組內所有修改
   - 相同的 reviewer comment 不可重複出現在不同 group 中
   - 優先按具體修改內容分組，而非廣泛技術領域
   - commit message 必須精確對應該組包含的所有 comment
5. Copilot 指令應遵循「先分析，後行動」的模式，確保理解後再實施

**分組例子說明**：
- ❌ 錯誤：將 "null/nil check" 和 "error message format" 放在同一個 "error-handling" 組
- ✅ 正確：分別歸為 "error-handling-checks" 和 "error-handling-messages" 組
- ❌ 錯誤：將 "variable naming" 和 "function naming" 放在不同組
- ✅ 正確：都歸為 "naming-conventions" 組，因為能用同一個 commit message 描述
"""

        return ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template(human_template),
            ]
        )

    @staticmethod
    def create_overall_analysis_prompt() -> ChatPromptTemplate:
        """Create prompt template for overall reviewer pattern analysis."""
        system_template = PromptTemplates.get_system_prompt()

        human_template = """
你正在分析整個 PR 審查過程中的知識傳遞和學習機會。

PR 背景資訊：
- 專案：{repository}  
- PR #{pr_number}：{pr_title}
- PR 創建者：{pr_creator}
- 總評論數：{total_comments}
- 參與審查者：{reviewer_count}

審查者活動與專業表現：
{reviewer_summary}

涵蓋的技術領域：{categories}

綜合分析任務：
1. **知識傳遞品質**：reviewer 群體展現的整體專業水準和知識深度
2. **學習機會評估**：這次 PR 為創建者提供了哪些成長機會？
3. **團隊協作模式**：reviewer 之間的互補性和知識覆蓋範圍
4. **發展建議**：基於 reviewer 的集體智慧，對 PR 創建者的成長建議

請以 JSON 格式提供綜合評估（繁體中文）：
{{
    "description": "整體 PR 審查過程的綜合評估與學習機會摘要",
    "valuable_insights": {{
        "style_forming_comments": ["最值得記錄和內化的 code style 原則"],
        "development_philosophy": ["值得形成個人開發風格的核心理念"],
        "professional_habits": ["值得培養的專業開發習慣"]
    }},
    "reviewer_responses": [
        {{
            "reviewer": "reviewer_name",
            "original_comment": "完整引用此 reviewer 的關鍵評論內容",
            "response": "Brief English response acknowledging their overall contribution (<30 words)",
            "copilot_instruction": "First analyze: [strategic question about overall code patterns related to this reviewer's focus]. After analysis, if needed: [strategic instruction for Copilot agent based on this reviewer's specific wisdom]",
            "commit_group": "strategic grouping for overall improvements that accurately represents this reviewer's contribution (e.g., 'architecture-refactor', 'team-standards', 'best-practices')",
            "suggested_commit_message": "Strategic commit message for systematic improvements based on this reviewer's specific insights"
        }}
    ]
}}

目標：
1. 將 reviewer 的集體智慧轉化為 PR 創建者的學習藍圖
2. 為主要 reviewer 生成感謝回覆，體現對其貢獻的認可
3. 提供整體的 Copilot 改進策略，按邏輯分組並提供建議的 commit message
4. 確保 Copilot 指令遵循「先分析，後行動」的模式
"""

        return ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template(human_template),
            ]
        )

    @staticmethod
    def format_comment_samples(comments: List, max_samples: int = 5) -> str:
        """Format comment samples for prompt injection."""
        comment_samples = []
        for i, comment in enumerate(comments[:max_samples], 1):
            content = (
                comment.content[:300] + "..."
                if len(comment.content) > 300
                else comment.content
            )
            file_info = f" (File: {comment.file_path})" if comment.file_path else ""
            comment_samples.append(
                f"{i}. Reviewer: {comment.author}{file_info}\n   Comment: {content}"
            )

        return "\n".join(comment_samples)

    @staticmethod
    def format_reviewer_summary(reviewer_comments: Dict[str, List]) -> str:
        """Format reviewer summary for prompt injection."""
        reviewer_summary = []
        for reviewer, comments in reviewer_comments.items():
            comment_count = len(comments)
            avg_length = sum(len(c.content) for c in comments) / comment_count
            files = list(set([c.file_path for c in comments if c.file_path]))
            reviewer_summary.append(
                f"- {reviewer}: {comment_count} comments, avg {avg_length:.0f} chars, focuses on {files[:3]}"
            )

        return "\n".join(reviewer_summary)
