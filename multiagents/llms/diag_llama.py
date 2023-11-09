import logging
import os
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from multiagents.llms.base import LLMResult
from . import llm_registry
from .base import BaseChatModel, BaseCompletionModel, BaseModelArgs
import requests
import json
import aiohttp
import asyncio
import time
import random
import re
from termcolor import colored
import sys
sys.path.append("../../../")
from llama2.inference import llama_inference

def remove_charts(text):
    pattern = r'\[chart\].*?\.html'
    output = re.sub(pattern, '', str(text), flags=re.DOTALL)

    return output

class DiagLlamaChatArgs(BaseModelArgs):
    max_in_len: int = Field(default=3072)
    beam_size: int = Field(default=2)
    max_length: int = Field(default=1000)

@llm_registry.register("diag-llama")
class DiagLlamaChat(BaseChatModel):
    args: DiagLlamaChatArgs = Field(default_factory=DiagLlamaChatArgs)
    conversation_history: List = []

    def __init__(self, max_retry: int = 100, **kwargs):
        super().__init__(**kwargs)  # Call the constructor of the base class
        args = DiagLlamaChatArgs()
        args = args.dict()

        self.conversation_history = []

        for k, v in args.items():
            args[k] = kwargs.pop(k, v)
        if len(kwargs) > 0:
            logging.warning(f"Unused arguments: {kwargs}")
        super().__init__(args=args, max_retry=max_retry)
        

    def _construct_system_messages(self, prompt: str):
        return [{"role": "system", "content": prompt}]

    def _construct_messages(self, prompt: str):
        return [{"role": "user", "content": prompt, "time": time.strftime("%H:%M:%S", time.localtime())}]

    def change_messages(self, role_description, messages):

        if role_description != "":
            role_message = self._construct_system_messages(role_description)
            self.conversation_history = role_message + messages
        else:
            self.conversation_history = messages

    def parse(self):
        messages = self.conversation_history

        new_messages = []
        for message in messages:
            # pop the time key-value from the message
            if "time" in message:
                message.pop("time")
            new_messages.append({"role": message["role"], "content": llama_inference.preprocess(message["content"])})
        
        mark_idx = llama_inference.classify(new_messages)
        if len(new_messages) > 2:
            if mark_idx == 5:
                new_messages = llama_inference.process_review(new_messages)
            elif mark_idx == 6:
                new_messages = llama_inference.process_solution(new_messages)
            elif mark_idx == 7:
                new_messages = llama_inference.process_refine(new_messages)

        output = llama_inference.inference(new_messages, max_in_len=self.args.max_in_len, max_length=self.args.max_length, beam_size=self.args.beam_size)

        output = remove_charts(output)
        
        # import pdb; pdb.set_trace()
        return {"role": "assistant", "content": output, "time": time.strftime("%H:%M:%S", time.localtime())}
    
    def generate_response(self, prompt: str) -> LLMResult:
        AssertionError

    async def agenerate_response(self, prompt: str) -> LLMResult:
        AssertionError