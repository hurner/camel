# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import inspect
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from colorama import Fore
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential

from camel.agents import ChatAgent
from camel.messages import BaseMessage, OpenAIMessage
from camel.typing import ModelType, RoleType
from camel.utils import num_tokens_from_messages, openai_api_key_required

FUNC_SYS_MSG = """No special instruction"""


@dataclass(frozen=True)
class FuncConfig:
    temperature: float = 0.0


class FuncAgent(ChatAgent):
    r"""Class for managing conversations of CAMEL Agents supporting
    OpenAI function calling

    Args:
        role_name (str): the name of the role to be played
        functions (List[Callable]): list of functions available for using
        model (ModelType, optional): The LLM model to use for generating
            responses. (default :obj:`ModelType.GPT_4`)
        model_config (Any, optional): Configuration options for the LLM model.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        verbose (bool, optional): Whether to print the critic's messages.
        logger_color (Any): The color of the logger displayed to the user.
            (default: :obj:`Fore.MAGENTA`)
        output_language (str): the language to be output
    """

    def __init__(
        self,
        role_name: str,
        functions: List[Callable],
        model: ModelType = ModelType.GPT_4_FUNC,
        model_config: Optional[Any] = None,
        message_window_size: Optional[int] = None,
        verbose: bool = False,
        logger_color: Any = Fore.MAGENTA,
        output_language: str = None,
    ) -> None:
        self.verbose = verbose
        self.logger_color = logger_color

        self.role_name: str = role_name
        self.role_type: RoleType = RoleType.FUNC

        system_message = BaseMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content=FUNC_SYS_MSG,
        )

        self.functions = []
        self.func_dict = {}
        for func in functions:
            self.func_dict[func.__name__] = func
            self.add_func(func)

        model_config = FuncConfig()

        super().__init__(
            system_message=system_message,
            model=model,
            model_config=model_config,
            message_window_size=message_window_size,
            output_language=output_language,
        )

    def add_func(self, func: Callable):
        func_dict = FuncAgent.parse_doc(func)
        self.functions.append(func_dict)

    @staticmethod
    def parse_doc(func) -> Dict[str, Any]:
        """
        Parse the docstrings of a function to extract function name,
        description and parameters.

        Args:
            func (Callable): the function to be parsed
        Returns:
            Dict[str, Any]: A dictionary with the function's name,
                description, and parameters.
        """

        doc = inspect.getdoc(func)

        # Parse function description
        func_desp = re.search(r'(.*?)Args', doc, re.DOTALL).group(1).strip()

        # Parse argument descriptions
        param_desp = re.findall(
            r'(\w+)\s*:\s*(\w+)\n(.*?)(?=\n\w+\s*:\s*|\nReturns|$)', doc,
            re.DOTALL)

        # Parameters from the function signature
        sign_params = list(inspect.signature(func).parameters.keys())

        properties = {}
        required = []
        for name, type, desp in param_desp:
            name = name.strip()
            type = type.strip()
            desp = desp.strip()

            required.append(name)
            properties[name] = {
                "type": type,
                "description": desp,
            }

        if len(sign_params) != len(required):
            raise ValueError(
                f"Number of parameters in function signature "
                f"({len(sign_params)})"
                f"does not match that in docstring ({len(required)})")

        for param in sign_params:
            if param not in required:
                raise ValueError(f"Parameter '{param}' in function signature"
                                 "is missing in the docstring")

        parameters = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

        func_dict = {
            "name": func.__name__,
            "description": func_desp,
            "parameters": parameters,
        }

        return func_dict

    @staticmethod
    def get_msg_dict(
        role: str,
        content: Optional[str] = None,
        func_name: Optional[str] = None,
        args: Optional[Dict] = None,
        result: Optional[Any] = None,
    ) -> OpenAIMessage:
        msg_dict = {"role": role}

        if role == "user":
            msg_dict["content"] = content
        elif role == "assistant":
            msg_dict["content"] = content

            msg_dict["function_call"] = {}
            msg_dict["function_call"]["name"] = func_name
            msg_dict["function_call"]["arguments"] = str(args)

            # msg_dict["function_call"] = str(msg_dict["function_call"])
        elif role == "function":
            msg_dict["name"] = func_name

            content = {"result": {str(result)}}
            msg_dict["content"] = f'{content}'

        return msg_dict

    def get_num_tokens(self) -> int:
        messages = []
        for message in self.messages:
            msg = message.copy()
            for key in msg.keys():
                msg[key] = str(msg[key])
            messages.append(msg)
        return num_tokens_from_messages(messages, self.model)

    @retry(wait=wait_exponential(min=5, max=60), stop=stop_after_attempt(5))
    @openai_api_key_required
    def step(
        self,
        input_message: BaseMessage,
    ) -> Tuple[BaseMessage, bool, Dict[str, Any]]:
        r"""Performs a step of chatting with potential function calling

        Args:
            input_message (BaseMessage): The input message.

        Returns:
            Tuple[BaseMessage, bool, Dict[str, Any]]: A tuple
                containing the output messages, function execution status, and
                additional information.
        """
        self.messages = [input_message.to_openai_user_message()]

        func_call = False
        while True:
            # Check whether token limit is exceeded
            num_tokens = self.get_num_tokens()
            if num_tokens >= self.model_token_limit:
                output_message = []

                info = self.get_info(
                    None,
                    None,
                    ["max_tokens_exceeded"],
                    num_tokens,
                )

                return (output_message, func_call, info)

            # Run OpenAI API
            response = self.model_backend.run(self.messages, self.functions)

            if self.verbose:
                print('-' * 24, "response", '-' * 24)
                print(response)

            # Check the type of returned response
            if not isinstance(response, dict):
                raise RuntimeError("OpenAI returned unexpected struct")

            choice = response.choices[0]

            # The functional running has been terminated
            if choice["finish_reason"] == "stop":
                print("Received STOP signal")
                if func_call:
                    output_message = [
                        BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict=None,
                            content=choice["message"]["content"],
                        )
                    ]

                info = self.get_info(
                    response["id"],
                    response["usage"],
                    [str(choice["finish_reason"])],
                    num_tokens,
                )

                break

            # Executing a function call
            elif choice["finish_reason"] == "function_call":
                func_call = True

                func_name = choice.message["function_call"].name
                func = self.func_dict[func_name]

                args = choice.message["function_call"].arguments
                args = eval(args)

                # Pass the extracted arguments to the indicated function
                result = func(**args)

                assist_msg = self.get_msg_dict("assistant",
                                               func_name=func_name, args=args)
                func_msg = self.get_msg_dict("function", func_name=func_name,
                                             result=result)

                # Update the messages
                self.messages += [assist_msg, func_msg]

            else:
                raise RuntimeError(
                    f"Unexpected finish_reason from choice: {choice}")

        return (output_message, func_call, info)
