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

from autogen import ConversableAgent, AssistantAgent, UserProxyAgent



class LLM_AGENT_BASE():
    r"""Base Class for agents (autogen agents)

        Args:
            agent_type (str): The type of agent assigned
                Possible values are "Conversable", "Assistant", "UserProxy"
                (1) Initializes Conversable Agent
                (2) Initializes Assistant Agent
                (3) Initializes UserProxy Agent
            name(str, or Optional): The name of the LLM agent, used to for the used to identify the agent during conversation 
            description (str, or Optional): description of the agent, used by other agents to refer to this instance
            system_message (str, or Optional): the prompt given to the LLM agent when initialized. characterization of roles/responsibilities
            human_input_mode (str): whether to ask for human inputs every time a message is received.
                Possible values are "ALWAYS", "TERMINATE", "NEVER".
                (1) When "ALWAYS", the agent prompts for human input every time a message is received.
                    Under this mode, the conversation stops when the human input is "exit",
                    or when is_termination_msg is True and there is no human input.
                (2) When "TERMINATE", the agent only prompts for human input only when a termination message is received or
                    the number of auto reply reaches the max_consecutive_auto_reply.
                (3) When "NEVER", the agent will never prompt for human input. Under this mode, the conversation stops
                    when the number of auto reply reaches the max_consecutive_auto_reply or when is_termination_msg is True.
            llm config (dict, or Optional): the llm config used to assign the LLM to the agent

            function_map: function map
            code_execution_config: code execution configuration

    """

    def __init__(
        self,
        agent_type: Literal["Conversable", "Assistant", "UserProxy"] = "Conversable",
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_message: Optional[str] = None,
        human_input_mode: Literal["ALWAYS", "NEVER", "TERMINATE"] = "TERMINATE",
        function_map: Optional[Dict[str, Callable]] = None,
        code_execution_config:  Union[Dict, Literal[False]] = False,
        llm_config: Optional[str] = None,
        is_termination_msg = None,
        max_consecutive_auto_reply = None
    ) -> None:

        self.agent_type = agent_type
        self.name = name
        self.system_message = system_message
        self.description = description
        self.human_input_mode = human_input_mode
        self.function_map = function_map
        self.code_execution_config = code_execution_config
        self.llm_config = llm_config
        self.is_termination_msg = is_termination_msg,
        self.max_consecutive_auto_reply = max_consecutive_auto_reply

        self.agent = None
    

def LLM_AGENT(*args, **kwargs):

        agent = LLM_AGENT_BASE(*args, **kwargs)

        if agent.agent_type is None:
            print("No agent type specified")
            return None
        
        if agent.agent_type not in ["Conversable", "Assistant", "UserProxy"]: raise Exception("Agent Type not available for %s" % agent.name)

        elif agent.agent_type == "Conversable":
            agent.agent = ConversableAgent(
                            name = agent.name,
                            description = agent.description,
                            system_message = agent.system_message,
                            human_input_mode = agent.human_input_mode,
                            llm_config = agent.llm_config,
                            function_map = agent.function_map,
                            code_execution_config = agent.code_execution_config,
                            max_consecutive_auto_reply = agent.max_consecutive_auto_reply
                                        )
        elif agent.agent_type == "Assistant":
            agent.agent = AssistantAgent(
                            name = agent.name,
                            description = agent.description,
                            system_message = agent.system_message,
                            human_input_mode = agent.human_input_mode,
                            llm_config = agent.llm_config,
                            function_map = agent.function_map,
                            max_consecutive_auto_reply = agent.max_consecutive_auto_reply
                                        )
        elif agent.agent_type == "UserProxy":
            agent.agent = UserProxyAgent(
                            name = agent.name,
                            description = agent.description,
                            system_message = agent.system_message,
                            max_consecutive_auto_reply = agent.max_consecutive_auto_reply
                                        )
        
        return agent.agent
