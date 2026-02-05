"""
AI/LLM Blocks 集合
---------------------------
目标：简单易用 + 丰富的场景
- 简单易用：核心是一个通用 LLMCallerBlock，支持基本调用；专用 blocks 继承或组合它，减少重复配置。
- 丰富的场景：提供通用调用 + 专用 blocks（如聊天、总结、翻译、代码生成），覆盖常见用例。
- 设计原则：
  - 最小配置：默认值覆盖常见用例；选项直观。
  - 模块化：输入/输出标准化（e.g., messages in, response out）。
  - 异步 + 错误处理：内置重试/日志。
  - 集成：使用环境变量 for API key；支持 stream/non-stream。

依赖：openai SDK (AsyncOpenAI)

统一导出：AI_LLM_BLOCKS 列表，用于注册。
"""

import asyncio
import os
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI

from flow.block import BaseBlock


# =========================================================
# Core / Caller
# =========================================================


class LLMCallerBlock(BaseBlock):
    """通用 LLM 调用器：核心 block，支持任意 messages 调用 DeepSeek API"""

    NAME = "LLMCaller"
    CATEGORY = "AI/LLM"
    STREAMING = True

    def __init__(self):
        super().__init__()

        self.add_input("messages")  # list[dict]: 输入消息列表 (required for call)

        self.add_output("response")  # str: 完整响应 or streamed chunks (as list[str])

        # 简单选项
        self.add_select_option(
            "model", items=["deepseek-chat", "deepseek-coder"], default="deepseek-chat"
        )  # 模型选择
        self.add_checkbox_option("stream", default=False)  # 是否流式
        self.add_number_option(
            "temperature", default=0.7, min_val=0.0, max_val=2.0
        )  # 创造性
        self.add_integer_option("max_tokens", default=512, min_val=1)  # 最大输出长度

        self._client: Optional[AsyncOpenAI] = None
        self._retry_count = 3  # 内置重试

    def _init_client(self):
        if self._client is None:
            api_key = "sk-bef0a9fc3a8744039566060d22af6086"
            self._client = AsyncOpenAI(
                api_key=api_key, base_url="https://api.deepseek.com"
            )
        return self._client

    async def _call_api(self, messages: List[Dict[str, str]]) -> Any:
        client = self._init_client()
        params = {
            "model": self.get_option("model"),
            "messages": messages,
            "stream": self.get_option("stream"),
            "temperature": self.get_option("temperature"),
            "max_tokens": self.get_option("max_tokens"),
        }
        for attempt in range(self._retry_count):
            try:
                return await client.chat.completions.create(**params)
            except Exception as e:
                if attempt == self._retry_count - 1:
                    raise
                await asyncio.sleep(1)  # 简单重试延迟
                self._log_error(e, f"API call retry {attempt + 1}")

    async def on_compute(self, execution_id=None):
        messages = self.get_interface("messages")
        if not messages or not isinstance(messages, list):
            self._log_error(ValueError("Invalid messages"), "No valid messages")
            return

        response = await self._call_api(messages)

        if self.get_option("stream"):
            chunks = []
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    chunks.append(chunk.choices[0].delta.content)
            self.set_interface("response", "".join(chunks))  # 收集完整响应
        else:
            content = response.choices[0].message.content.strip()
            self.set_interface("response", content)


# =========================================================
# Helpers / Builders
# =========================================================


class PromptBuilderBlock(BaseBlock):
    """提示构建器：简单组合 system + user prompt"""

    NAME = "PromptBuilder"
    CATEGORY = "AI/LLM"

    def __init__(self):
        super().__init__()

        self.add_input("system_prompt")  # str: 系统指令 (optional)
        self.add_input("user_input")  # str: 用户输入 (required)
        self.add_input("history")  # optional list[dict]: 聊天历史

        self.add_output("messages")  # list[dict]:  готовые消息

        self.add_textarea_input_option(
            "default_system", default="You are a helpful assistant."
        )

    async def on_compute(self, execution_id=None):
        system = self.get_interface("system_prompt") or self.get_option(
            "default_system"
        )
        user = self.get_interface("user_input")
        history = self.get_interface("history") or []

        if not user:
            return

        messages = [{"role": "system", "content": system}] if system else []
        messages.extend(history)
        messages.append({"role": "user", "content": user})

        self.set_interface("messages", messages)


class ResponseHandlerBlock(BaseBlock):
    """响应处理器：解析/格式化 LLM 输出"""

    NAME = "ResponseHandler"
    CATEGORY = "AI/LLM"

    def __init__(self):
        super().__init__()

        self.add_input("response")  # str: LLM 原始响应

        self.add_output("parsed")  # any: 解析结果 (str/dict/list)

        self.add_select_option(
            "output_format", items=["Text", "JSON", "List"], default="Text"
        )  # 输出格式

    async def on_compute(self, execution_id=None):
        response = self.get_interface("response")
        if not response:
            return

        fmt = self.get_option("output_format")

        if fmt == "JSON":
            try:
                parsed = json.loads(response)
            except json.JSONDecodeError as e:
                self._log_error(e, "JSON parse failed")
                parsed = {"error": "Invalid JSON", "raw": response}
        elif fmt == "List":
            parsed = [line.strip() for line in response.splitlines() if line.strip()]
        else:
            parsed = response.strip()

        self.set_interface("parsed", parsed)


# =========================================================
# Scenarios / Chat
# =========================================================


class ChatBotBlock(LLMCallerBlock):
    """聊天机器人：简单聊天场景，内置历史管理"""

    NAME = "ChatBot"
    CATEGORY = "AI/LLM/Scenarios"

    def __init__(self):
        super().__init__()

        self.add_input("user_message")  # str: 当前用户消息
        self.add_input(
            "chat_history"
        )  # optional list[dict]: 历史 (auto-managed if not provided)

        self.add_output("reply")  # str: 机器人回复
        self.add_output("new_history")  # list[dict]: 更新后的历史

        self.add_textarea_input_option(
            "system_prompt", default="You are a friendly chatbot."
        )
        self._internal_history: List[Dict[str, str]] = []  # 内置状态

    async def on_compute(self, execution_id=None):
        user_msg = self.get_interface("user_message")
        if not user_msg:
            return

        history = self.get_interface("chat_history") or self._internal_history
        system = self.get_option("system_prompt")

        messages = [{"role": "system", "content": system}] if system else []
        messages.extend(history)
        messages.append({"role": "user", "content": user_msg})

        self.set_interface("messages", messages)  # 复用父类输入
        await super().on_compute(execution_id)

        reply = self.get_interface("response")
        if reply:
            self.set_interface("reply", reply)
            new_history = history + [
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": reply},
            ]
            self.set_interface("new_history", new_history)
            self._internal_history = new_history  # 更新内置历史


# =========================================================
# Scenarios / Summarize
# =========================================================


class TextSummarizerBlock(LLMCallerBlock):
    """文本总结：专用场景，自动构建总结提示"""

    NAME = "TextSummarizer"
    CATEGORY = "AI/LLM/Scenarios"

    def __init__(self):
        super().__init__()

        self.add_input("text")  # str: 要总结的文本

        self.add_output("summary")  # str: 摘要

        self.add_select_option(
            "style", items=["Concise", "Detailed", "Bullets"], default="Concise"
        )  # 风格
        self.add_integer_option("length", default=100, min_val=50, max_val=500)  # 字数

    async def on_compute(self, execution_id=None):
        text = self.get_interface("text")
        if not text:
            return

        style = self.get_option("style")
        length = self.get_option("length")

        prompt = f"Summarize the following text in a {style.lower()} way, around {length} words:\n\n{text}"

        messages = [
            {"role": "system", "content": "You are a summarization expert."},
            {"role": "user", "content": prompt},
        ]

        self.set_interface("messages", messages)
        await super().on_compute(execution_id)

        summary = self.get_interface("response")
        self.set_interface("summary", summary)


# =========================================================
# Scenarios / Translate
# =========================================================


class TranslatorBlock(LLMCallerBlock):
    """文本翻译：支持多语言，简单易用"""

    NAME = "Translator"
    CATEGORY = "AI/LLM/Scenarios"

    def __init__(self):
        super().__init__()

        self.add_input("text")  # str: 要翻译的文本
        self.add_input("source_lang")  # optional str: 源语言 (auto-detect if None)

        self.add_output("translated")  # str: 翻译结果

        self.add_text_option("target_lang", default="English")  # 目标语言

    async def on_compute(self, execution_id=None):
        text = self.get_interface("text")
        if not text:
            return

        source = self.get_interface("source_lang") or "auto"
        target = self.get_option("target_lang")

        prompt = f"Translate the following text from {source} to {target}:\n\n{text}"

        messages = [
            {"role": "system", "content": "You are a professional translator."},
            {"role": "user", "content": prompt},
        ]

        self.set_interface("messages", messages)
        await super().on_compute(execution_id)

        translated = self.get_interface("response")
        self.set_interface("translated", translated)


# =========================================================
# Scenarios / CodeGen
# =========================================================


class CodeGeneratorBlock(LLMCallerBlock):
    """代码生成：基于描述生成代码片段"""

    NAME = "CodeGenerator"
    CATEGORY = "AI/LLM/Scenarios"

    def __init__(self):
        super().__init__()

        self.add_input("description")  # str: 代码需求描述

        self.add_output("code")  # str: 生成的代码

        self.add_select_option(
            "language", items=["Python", "JavaScript", "Java", "C++"], default="Python"
        )  # 编程语言

    async def on_compute(self, execution_id=None):
        desc = self.get_interface("description")
        if not desc:
            return

        lang = self.get_option("language")

        prompt = f"Write a {lang} code snippet that does the following:\n{desc}\nProvide only the code, no explanations."

        messages = [
            {"role": "system", "content": "You are a code generation expert."},
            {"role": "user", "content": prompt},
        ]

        self.set_interface("messages", messages)
        await super().on_compute(execution_id)

        code = self.get_interface("response")
        self.set_interface("code", code)


# =========================================================
# 统一导出
# =========================================================

AI_LLM_BLOCKS = [
    LLMCallerBlock,
    PromptBuilderBlock,
    ResponseHandlerBlock,
    ChatBotBlock,
    TextSummarizerBlock,
    TranslatorBlock,
    CodeGeneratorBlock,
]
