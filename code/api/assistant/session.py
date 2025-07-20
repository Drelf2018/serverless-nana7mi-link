from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Union

from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessage,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)


@dataclass
class Session:
    model: str
    client: AsyncOpenAI
    messages: List[ChatCompletionMessageParam]

    @classmethod
    def new(cls, model: str, client: AsyncOpenAI, system: str = "", history: Optional[Iterable[Optional[str]]] = None, *args, **kwargs):
        """
        新会话

        Args:
            model (str): 对话模型
            client (AsyncOpenAI): 客户端
            system (str, optional):
                设定对话的全局上下文或助手的行为指令或者以 `file:///` 开头的提示词文件路径
            history (Optional[Iterable[Optional[str]]], optional):
                按照“用户-助手-用户”的顺序给出的历史对话，当元素为空时会跳过
                但是有些平台不允许出现连续的用户或助手输入，请自行判断是否留空

        Returns:
            会话
        """
        messages = []
        # 添加系统提示词
        if system is None:
            system = ""
        if system != "":
            if system.startswith("file:///"):
                file = Path(system.removeprefix("file:///"))
                with open(file, "r", encoding="utf-8") as fp:
                    content = fp.read()
                messages.append(ChatCompletionSystemMessageParam(role="system", content=content, name=system))
            else:
                messages.append(ChatCompletionSystemMessageParam(role="system", content=system))
        # 添加历史对话
        if history is not None:
            for idx, message in enumerate(history):
                if message is None:
                    continue
                if idx & 1 == 0:
                    messages.append(ChatCompletionUserMessageParam(role="user", content=message))
                else:
                    messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=message))
        # 创建会话
        return cls(model=model, client=client, messages=messages, *args, **kwargs)

    def dump(self) -> Dict[str, Union[str, List[str]]]:
        """
        导出会话

        Returns:
            可用于重建会话的字典
        """
        data = {
            "url": str(self.client.base_url),
            "key": self.client.api_key,
            "model": self.model,
            "system": "",
            "history": [m.get("content", "") for m in self.messages],
        }
        if len(self.messages) > 0:
            system = self.messages[0]
            if system["role"] == "system":
                if system.get("name", "") != "":
                    data["system"] = system["name"]
                else:
                    data["system"] = system["content"]
                data["history"] = data["history"][1:]
        return data

    @classmethod
    def load(cls, data: Dict[str, Union[str, List[str]]], *args, **kwargs):
        """
        载入会话

        Args:
            data (Dict[str, Union[str, List[str]]]): 用于重建会话的字典

        Returns:
            会话实例
        """
        model = data.get("model", "")
        system = data.get("system", "")
        history = data.get("history", [])
        client = AsyncOpenAI(api_key=data.get("key"), base_url=data.get("url"))
        return cls.new(model=model, client=client, system=system, history=history, *args, **kwargs)

    def __str__(self) -> str:
        """
        纯文本消息

        Returns:
            会话中最后一条消息的文本，通常是助手的回复
        """
        if len(self.messages) == 0:
            return ""
        return self.messages[-1].get("content", "")

    async def message_handler(self, message: ChatCompletionMessage) -> ChatCompletionAssistantMessageParam:
        """
        消息处理

        Args:
            message (ChatCompletionMessage): 助手回复的消息

        Returns:
            处理后的消息，用于添加在会话的消息列表末尾
        """
        return ChatCompletionAssistantMessageParam(message.model_dump())

    async def create(self, input: str, *args, **kwargs) -> str:
        """
        创建回复

        Args:
            input (str): 用户输入

        Returns:
            助手的回复
        """
        self.messages.append(ChatCompletionUserMessageParam(role="user", content=input))
        response = await self.client.chat.completions.create(model=self.model, messages=self.messages, stream=False, *args, **kwargs)
        reply = await self.message_handler(response.choices[0].message)
        self.messages.append(reply)
        return str(self)


@dataclass
class DeepSeek(Session):
    async def message_handler(self, message: ChatCompletionMessage):
        if self.model == "deepseek-reasoner":
            setattr(message, "reasoning_content", None)
        return await super().message_handler(message)


async def create(input: str, model: str, client: AsyncOpenAI, system: str = "", history: Optional[Iterable[Optional[str]]] = None, *args, **kwargs) -> str:
    """
    创建对话

    Args:
        input (str): 用户输入
        model (str): 对话模型
        client (AsyncOpenAI): 客户端
        system (str): 系统提示词
        history (Optional[Iterable[Optional[str]]], optional): 历史对话

    Returns:
        助手的纯文本回复
    """
    return await Session.new(model=model, client=client, system=system, history=history).create(input, *args, **kwargs)
