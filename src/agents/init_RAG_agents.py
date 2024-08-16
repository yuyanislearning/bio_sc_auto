import importlib.metadata
import json
import logging
import os
import re
import tempfile
import time
import ast
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union


from .agent_BASE import LLM_AGENT
from ..utils.OAI_utils import config_list_from_json
from ..jupyter_docker_exec.jupyter_execution import custom_DockerJupyterServer

from autogen.coding.jupyter import JupyterCodeExecutor, LocalJupyterServer
from autogen.coding import DockerCommandLineCodeExecutor, LocalCommandLineCodeExecutor
from autogen.code_utils import create_virtual_env


class RAG_bioagent():
    def __init__(self, 
                 OAI_config: Optional[str] = None, 
                 openai_key_file: Optional[str] = None, 
                 LLM_model: Optional[str] = "gpt-3.5-turbo",
                 Human_input: Optional[str] = "ALWAYS"):
        self.OAI_config = OAI_config
        self.openai_key_file = openai_key_file
        self.LLM_model = LLM_model
        self.Human_input = Human_input
        assert Human_input in ['ALWAYS', 'NEVER', 'TERMINATE','CODE_ONLY', 'PLAN_ONLY', 'REVIEW_ONLY']
        
        self.human_input_mode = Human_input if Human_input in ['ALWAYS', 'NEVER', 'TERMINATE'] else 'TERMINATE' 


    def create_boss(self, code_executer):
        r""" Creates the boss for the agent system"""

        description = """
                    The boss who ask questions and give tasks.
                    """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict=filter_dict
                                        )
        
        # Create an agent with code executor configuration that uses docker.

        if code_executer == "LocalCLI": 

            # Create the virtual environment
            venv_context = create_virtual_env(".venv")
        
            # List of packages to install
            packages_to_install = ["numpy",
                                "pandas",
                                "scanpy",
                                "scanpy[leiden]",
                                "cellxgene-census"]  

            pip_executable = ".venv/bin/pip"  # For Unix-based systems (Linux, macOS)
            subprocess.check_call([pip_executable, "install"] + packages_to_install)
            executor = LocalCommandLineCodeExecutor(virtual_env_context=venv_context, work_dir = "GENERATED_CODE_BASE/", timeout=60*5)
            code_execution_config = {"executor": executor, "use_docker": False}

            
        elif code_executer == "DockerCLI":
            # executor = DockerCommandLineCodeExecutor(# TODO, make a consistent version, state in README
            #     image="singlecell:1.3",  # Execute code using the given docker image name.
            #     timeout=10,  # Timeout for each code execution in seconds.
            #     work_dir="GENERATED_CODE_BASE/",  # Use the temporary directory to store the code files.
            # )
            code_execution_config = {"use_docker": 'singlecell:1.1', "work_dir": "GENERATED_CODE_BASE/"}

       
        elif code_executer == "JupyterCLI":
            server = custom_DockerJupyterServer()
            code_execution_config = {
                    "executor": JupyterCodeExecutor(server, output_dir="GENERATED_CODE_BASE/"),
                    }
            

        #if provided a code_execution configuration
        elif isinstance(code_executer, dict): 
            pass
        else:
            raise Exception("Line 139: init_agents.py: code execution not provided")


        boss = LLM_AGENT(
                        agent_type = "UserProxy",
                        name = "Boss", 
                        system_message = "", 
                        description = description,
                        human_input_mode = 'ALWAYS',
                        code_execution_config = code_execution_config,
                                )
        return boss

    def create_boss_aid(self, code_executer) -> LLM_AGENT:


        description = """
                    Assistant who has extra content retrieval power for solving difficult problems.
                    """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict = filter_dict
                                        )
        
        retrieve_config_ = {
                        "task": "code",
                        "docs_path": "https://chanzuckerberg.github.io/cellxgene-census/_sources/notebooks/api_demo/census_query_extract.ipynb.txt",
                        "chunk_token_size": 1000,
                        "model": config_list[0]["model"],
                        "collection_name": "groupchat",
                        "get_or_create": True,
                        }
        
# Create an agent with code executor configuration that uses docker.

        if code_executer == "LocalCLI": 

            # Create the virtual environment
            venv_context = create_virtual_env(".venv")
        
            # List of packages to install
            packages_to_install = ["numpy",
                                "pandas",
                                "scanpy",
                                "scanpy[leiden]",
                                "cellxgene-census"]  


            pip_executable = ".venv/bin/pip"  # For Unix-based systems (Linux, macOS)
            subprocess.check_call([pip_executable, "install"] + packages_to_install)
            executor = LocalCommandLineCodeExecutor(virtual_env_context=venv_context, work_dir = "GENERATED_CODE_BASE/", timeout = 60*5)
            code_execution_config = {"executor": executor, "use_docker": False}

            
        elif code_executer == "DockerCLI":
            # executor = DockerCommandLineCodeExecutor(# TODO, make a consistent version, state in README
            #     image="singlecell:1.3",  # Execute code using the given docker image name.
            #     timeout=10,  # Timeout for each code execution in seconds.
            #     work_dir="GENERATED_CODE_BASE/",  # Use the temporary directory to store the code files.
            # )
            code_execution_config = {"use_docker": 'singlecell:1.1', "work_dir": "GENERATED_CODE_BASE/"}

        #TODO
        elif code_executer == "JupyterCLI":
            server = custom_DockerJupyterServer()
            code_execution_config = {
                    "executor": JupyterCodeExecutor(server, output_dir="GENERATED_CODE_BASE/"),
                    }
            

        #if provided a code_execution configuration
        elif isinstance(code_executer, dict): 
            pass
        else:
            raise Exception("Line 139: init_agents.py: code execution not provided")

        boss_aid = LLM_AGENT(
                                agent_type = "RetrieveUserProxy",
                                name = "Boss_Assistant", 
                                system_message = "", 
                                description = description,
                                human_input_mode = "NEVER",
                                retrieve_config = retrieve_config_,
                                code_execution_config = code_execution_config
                                )
        return boss_aid


    def create_coder(self) -> LLM_AGENT:

        system_message = (
            "You are a senior python engineer, you provide python code to answer questions."
        )

        description = """
                       Senior Python Engineer who can write code to solve problems and answer questions.
                    """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict = filter_dict
                                        )
        


        coder = LLM_AGENT(
                                agent_type = "Assistant",
                                name = "Senior_Python_Engineer",
                                system_message = system_message, 
                                description = description,
                                llm_config = {"config_list": config_list}, 
                                human_input_mode = "NEVER"  # Always take human input for this agent for safety.
                                    )
        return coder


    def create_pm(self) -> LLM_AGENT:

        system_message = (
            "You are a Senior Biomedical Inoformatics Investigator."
        )

        description = """
                Senior Biomedical Informatics Investigator who can design and plan the project.                    
                """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict = filter_dict
                                        )
        


        pm = LLM_AGENT(
                                agent_type = "Assistant",
                                name = "Senior_Biomedical_Informatics_Investigator",
                                system_message = system_message, 
                                description = description,
                                llm_config = {"config_list": config_list}, 
                                human_input_mode = "NEVER"  # Always take human input for this agent for safety.
                                    )
        return pm
    
    def create_reviewer(self) -> LLM_AGENT:

        system_message = (
            "You are a code reviewer."
        )

        description = """
                Code Reviewer who can review the code.
                """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict = filter_dict
                                        )

        def termination_msg(x):
            return isinstance(x, dict) and "TERMINATE" == str(x.get("content", ""))[-9:].upper()


        reviewer = LLM_AGENT(
                                agent_type = "Assistant",
                                name = "Code_Reviewer",
                                system_message = system_message, 
                                description = description,
                                llm_config = {"config_list": config_list}, 
                                human_input_mode = "NEVER",  # Always take human input for this agent for safety.
                                is_termination_msg = termination_msg,
                                )
        return reviewer