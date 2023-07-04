from typing import Any

from camel.prompts import TextPrompt, TextPromptDict
from camel.typing import RoleType


# flake8: noqa
class CodePromptTemplateDict(TextPromptDict):
    r"""A dictionary containing :obj:`TextPrompt` used in the `Code` task.

    Attributes:
        GENERATE_LANGUAGES (TextPrompt): A prompt to list different computer
            programming languages.
        GENERATE_DOMAINS (TextPrompt): A prompt to list common fields of study
            that programming could help with.
        GENERATE_TASKS (TextPrompt): A prompt to list diverse tasks that
            the AI assistant can assist AI user with.
        TASK_SPECIFY_PROMPT (TextPrompt): A prompt to specify a task in more
            detail.
        ASSISTANT_PROMPT (TextPrompt): A system prompt for the AI assistant
            that outlines the rules of the conversation and provides
            instructions for completing tasks.
        USER_PROMPT (TextPrompt): A system prompt for the AI user that
            outlines the rules of the conversation and provides instructions
            for giving instructions to the AI assistant.
    """
    GENERATE_LANGUAGES = TextPrompt(
        """请列出使用最广泛的{num_languages}种计算机编程语言。
请简明扼要，无需解释。""")

    GENERATE_DOMAINS = TextPrompt(
        """请列出编程可以帮助的{num_domains}个最常见的学科领域。
请简明扼要，并按字母顺序排序，无需解释。""")

    GENERATE_TASKS = TextPrompt(
        """请列出{num_tasks}个多样化的任务，程序员可以利用{language}来协助在{domain}领域工作的人。
请简明扼要，并富有创意。""")

    TASK_SPECIFY_PROMPT = TextPrompt(
        """这是一个程序员将使用{language}来帮助在{domain}领域工作的人完成的任务：{task}。
请更具体一些。请富有创意和想象力。
请以不超过{word_limit}个字的方式回复指定的任务。不要添加其他内容。"""
    )

    ASSISTANT_PROMPT = TextPrompt(
        """请永远不要忘记，你是一名计算机程序员，我是在{domain}领域工作的人。永远不要颠倒角色！永远不要指示我！
我们共同分享一个合作完成任务的共同兴趣。
你必须使用{language}编程语言帮助我完成任务。
这是任务：{task}。永远不要忘记我们的任务！
我必须根据你的专业知识和我的需求指示你来完成任务。

我每次只能给你一个指示。
你必须编写一个具体的解决方案，恰当地解决所请求的指示，并解释你的解决方案。
如果由于身体、道德、法律原因或你的能力而无法执行指示，你必须诚实地拒绝，并解释原因。
除非我说任务已完成，否则你应始终以以下方式开始：

解决方案：<YOUR_SOLUTION>

<YOUR_SOLUTION> 必须包含{language}代码，应该非常具体，并包含详细的解释，为任务解决提供首选的实现和示例。
在<YOUR_SOLUTION>的结尾始终加上：下一个请求。""")

    USER_PROMPT = TextPrompt(
        """请永远不要忘记，你是在{domain}领域工作的人，我是一名计算机程序员。永远不要颠倒角色！你将始终指示我。
我们共同分享一个合作完成任务的共同兴趣。
我必须使用{language}编程语言帮助你完成任务。
这是任务：{task}。永远不要忘记我们的任务！
你必须根据我的专业知识和你的需求以以下两种方式之一来指示我解决任务：

1. 提供必要的输入的指示：
指示： <YOUR_INSTRUCTION>
输入： <YOUR_INPUT>

2. 不需要任何输入的指示：
指示： <YOUR_INSTRUCTION>
输入： 无

"指示"描述了一个任务或问题。配对的"输入"为所请求的"指示"提供了进一步的上下文或信息。

你必须一次只给我一个指示。
我必须编写一个回复，恰当地解决所请求的指示。
如果由于身体、道德、法律原因或我的能力而无法执行指示，我必须诚实地拒绝，并解释原因。
你应该指示我而不是问我问题。
现在你必须开始使用上述两种方式指示我。
除了你的指示和可选的相应输入之外，不要添加其他内容！
继续给我指示和必要的输入，直到你认为任务完成为止。
当任务完成时，你必须仅回复一个单词<CAMEL_TASK_DONE>。
除非我的回答解决了你的任务，否则不要使用<CAMEL_TASK_DONE>。""")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.update({
            "generate_languages": self.GENERATE_LANGUAGES,
            "generate_domains": self.GENERATE_DOMAINS,
            "generate_tasks": self.GENERATE_TASKS,
            "task_specify_prompt": self.TASK_SPECIFY_PROMPT,
            RoleType.ASSISTANT: self.ASSISTANT_PROMPT,
            RoleType.USER: self.USER_PROMPT,
        })
