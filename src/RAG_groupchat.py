import importlib.metadata
import json
import logging
import os
import re
import tempfile
import time
import ast
from pathlib import Path
from typing_extensions import Annotated
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union

from autogen import GroupChat, GroupChatManager
from src.agents.agent_BASE import LLM_AGENT
from .speaker_transition import custom_FSM_transition, custom_state_transition
from .utils.OAI_utils import config_list_from_json


def _reset_agents(agent_list: Optional[List[Any]]):
    for agent in agent_list:
        agent.reset()

def init_rag_groupchat(
        agent_dict: Optional[Dict] = None,
        groupchat_config_path: Optional[str] = "groupchat_config.json",
        OAI_config: Optional[str] = None, 
        openai_key_file: Optional[str] = None,
        LLM_model: Optional[str] = "llama2:7b",
    ) -> Tuple[GroupChat, GroupChatManager]:
    """Initialize a groupchat based on the agent list, specifid by the groupchat config

    Args:
        agent_list (Optional[List[LLM_AGENT]], optional): List of agents, in order of importance. 
        groupchat_config_path (Optional[str], optional): path to config for parameters. Defaults to "groupchat_config.json".
        LLM_model: specify model to use, default is llama2:7b. available models in OAI config file

    Returns:
        Tuple[GroupChat, GroupChatManager]: returns groupchat, groupchat manager
    """

    agent_list = list(agent_dict.values())
    _reset_agents(agent_list)

    groupchat = GroupChat(
        agents= [agent_dict["boss_aid"], agent_dict["boss"], agent_dict["pm"], agent_dict["coder"], agent_dict["rag_reviewer"]],
        messages=[],
        max_round=20,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False,
    )

    filter_dict = {"model": [LLM_model]}
    config_list = config_list_from_json(
                                    env_or_file = OAI_config, 
                                    openai_key_file = openai_key_file,
                                    filter_dict=filter_dict
                                    )

    #assign retriever
    def retrieve_content(message: Annotated[
        str,
        "Refined message which keeps the original meaning and can be used to retrieve content for code generation and question answering.",
        ],
        agent = agent_dict["boss_aid"], n_results = 5):
        agent.n_results = n_results  # Set the number of results to be retrieved.
        # Check if we need to update the context.
        update_context_case1, update_context_case2 = agent._check_update_context(message)
        if (update_context_case1 or update_context_case2) and agent.update_context:
            agent.problem = message if not hasattr(agent, "problem") else agent.problem
            _, ret_msg = agent._generate_retrieve_user_reply(message)
        else:
            _context = {"problem": message}
            ret_msg = agent.message_generator(agent, None, _context)
        return ret_msg if ret_msg else message
    
    for caller in [agent_dict["pm"], agent_dict["coder"], agent_dict["rag_reviewer"]]:
        d_retrieve_content = caller.register_for_llm(
            description="retrieve content for code generation and question answering.", api_style="function"
        )(retrieve_content)

    for executor in [agent_dict["boss"], agent_dict["pm"]]:
        executor.register_for_execution()(d_retrieve_content)
    
    manager = GroupChatManager(groupchat = groupchat, llm_config = {"config_list": config_list})

    return groupchat, manager