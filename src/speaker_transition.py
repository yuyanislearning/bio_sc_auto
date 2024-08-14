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

from src.agents.agent_BASE import LLM_AGENT


def custom_FSM_transition(
    agent_dict: Optional[Dict] = None,
    ) -> Dict[str, Any]:
    r""" Custom FSM state transition for a specified list of agents, ordered by importance.

    Args:
        agent_list (Optional[List[LLM_AGENT]], optional): Order of agents, based on importance. The suggested order is [planner, code_generator, code_executor, review] . Defaults to None.

    Returns:
        Dict[str, Any]: Returns optimal state transition
    """

    allowed_speaker_transitions_dict = {
        agent_dict['planner']:[agent_dict['bioinformatician']],
        agent_dict['bioinformatician']:[agent_dict['code_executor'],  agent_dict['reviewer']], 
        agent_dict['code_executor']:[agent_dict['bioinformatician']],
        agent_dict['reviewer']: [agent_dict['summarizer']]   
    }

    return allowed_speaker_transitions_dict


def custom_state_transition(
    agent_dict: Optional[List[LLM_AGENT]] = None,    
    ) -> Callable:
    r""" Custom state transition for a specified list of agents, ordered by importance.

    Args:
        agent_list (Optional[List[LLM_AGENT]], optional): Order of agents, based on importance. The suggested order is [planner, code_generator, code_executor, review] . Defaults to None.

    Returns:
        State transition function for groupchat
    """

    def state_transition(last_speaker, groupchat):
        messages = groupchat.messages
        
        #override the speaker transition when results are done
        if "SUMMARIZER" in messages[-1]["content"]:
                # If the last message is approved, let the engineer to speak
            return agent_dict['summarizer']
        
        #override 
        elif "CODE_EXECUTOR" in messages[-1]["content"]:
                # If the last message is approved, let the engineer to speak
            return agent_dict['code_executor']


        else: 
            return "auto"
        
    return state_transition
            

