
import importlib.metadata
import json
import logging
import os
import re
import tempfile
import time
import ast
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union

from autogen import GroupChat, GroupChatManager
from src.agents.agent_BASE import LLM_AGENT
from .speaker_transition import custom_FSM_transition, custom_state_transition
from .utils.OAI_utils import config_list_from_json


def init_groupchat(
        agent_dict: Optional[Dict] = None,
        groupchat_config_path: Optional[str] = "groupchat_config.json",
        OAI_config: Optional[str] = None, 
        openai_key_file: Optional[str] = None,
        LLM_model: Optional[str] = "gpt-4o-mini",
    ) -> Tuple[GroupChat, GroupChatManager]:
    """Initialize a groupchat based on the agent list, specifid by the groupchat config

    Args:
        agent_list (Optional[List[LLM_AGENT]], optional): List of agents, in order of importance. Suggestion is [planner, scientist, code_exec, review]. Defaults to None.
        groupchat_config_path (Optional[str], optional): path to config for parameters. Defaults to "groupchat_config.json".
        LLM_model: specify model to use, default is llama2:7b. available models in OAI config file

    Returns:
        Tuple[GroupChat, GroupChatManager]: returns groupchat, groupchat manager
    """

    custom_FSM_transition_dict = custom_FSM_transition(agent_dict)
    custom_state_transition_method = custom_state_transition(agent_dict)
    agent_list = list(agent_dict.values())

    groupchat = GroupChat(
        agents = agent_list,
        messages = [],
        max_round = 100,
        func_call_filter = True,
        allowed_or_disallowed_speaker_transitions=custom_FSM_transition_dict,
        speaker_transitions_type="allowed",
        speaker_selection_method = custom_state_transition_method,
    )

    filter_dict = {"model": [LLM_model]}
    config_list = config_list_from_json(
                                    env_or_file = OAI_config, 
                                    openai_key_file = openai_key_file,
                                    filter_dict=filter_dict
                                    )

    manager = GroupChatManager(groupchat = groupchat, llm_config = {"config_list": config_list})

    return groupchat, manager
