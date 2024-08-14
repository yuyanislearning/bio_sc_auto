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


class bioagent():
    def __init__(self, 
                 OAI_config: Optional[str] = None, 
                 openai_key_file: Optional[str] = None, 
                 LLM_model: Optional[str] = "gpt-3.5-turbo",
                 Human_input: Optional[str] = "ALWAYS",
                 work_dir: Optional[str] = None,
                 ):
        self.OAI_config = OAI_config
        self.openai_key_file = openai_key_file
        self.LLM_model = LLM_model
        self.Human_input = Human_input
        self.work_dir = work_dir
        assert Human_input in ['ALWAYS', 'NEVER', 'TERMINATE','CODE_ONLY', 'PLAN_ONLY', 'REVIEW_ONLY']
        
        self.human_input_mode = Human_input if Human_input in ['ALWAYS', 'NEVER', 'TERMINATE'] else 'TERMINATE' 

        self.environment_message = (
            "Topic prompt for all agents:\n"
            "\n"
            "You are part of a collaborative multi-agent system designed to proform bioinformatics analysis "
            "based on a given research question. Each of you has a specific role:\n"
            "\n"
            "Planner: Project manager and Lead Scientist who is responsible to create the analytic plan.\n"
            "Bioinformatician: Bioinformatics response for writing the scirpts for analysis.\n"
            "Code Executor: To execute the analysis script and return the results.\n"
            "Reviewer: To review the results of the analysis and determine whether the results has answered the research question.\n"
            "Summarizer: Summarize the results of the analysis and and generate a summary report.\n"
            "\n"
            "Stay focused on your individual roles, collaborate effectively, and aim to perfrom the bioinformatics analysis to answer the research question.\n"
            "\n"
            "----------------------------------------------------------------\n"
        )

    def create_planner(self):
        r""" Creates the planner for the agent system"""

        system_message = (
                        "You have 10 plus years of experience in designing workflows for the analysis of single cell omics data. \n"
                        "You have expertise in single cell data analysis and know how code in python should be organized. \n"
                        "You ensure that your workflow design is in alignment with the best practices of single cell analysis.\n"
                        "You are able to plan and oversee the execution of such workflows without writing or executing any code yourself.\n"
                        "\n"
                        "Given the dataset and goal, formulate a step by step plan for the Bioinformatician to execute.\n"
                        "Each step should provides general idea and be clear enough for the computational scientist to follow.\n"
                        "For example, step 1: Load the dataset and explore the data.\n"
                        "Step 2: Perform data preprocessing and quality control.\n"
                        "The plan should not contain code nor suggestion of package.\n"
                        "Please pass all relevant information after the plan, for example, data locaation.\n"
        )
                        # it often gives wrong code or suggestion
        system_message = self.environment_message + system_message

        description = """
                    Project manager and Lead Scientist who is responsible to create the analytic plan.
                    """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict=filter_dict
                                        )

        planner = LLM_AGENT(
                            agent_type = "Assistant",
                            name = "planner", 
                            system_message = system_message, 
                            description = description,
                            human_input_mode = self.human_input_mode if self.Human_input!='PLAN_ONLY' else 'ALWAYS',
                            llm_config = {"config_list": config_list}
                                )
        return planner

    def create_bioinformatician(self) -> LLM_AGENT:
        r""" Creates the bioinformatician of the agent system"""

        rare_error_solutions = (
            "For error:\n"
            "if 'log1p' in adata.uns_keys() and adata.uns['log1p']['base'] is not None: KeyError: 'base'\n"
            "Solution:\n"
            "put the following code ahead: \n"
            "adata.uns['log1p']['base'] = None\n"
            "\n"
            "For error:\n"
            "sc.pl.rank_genes_groups_dotplot(adata).savefig('results.png') \n"
            "AttributeError: 'NoneType' object has no attribute 'savefig\n"
            "Solution:\n"
            "sc pl functions usually has an argument: 'save', where the file name should be passed to save the figure.\n"
            "for example: sc.pl.rank_genes_groups_dotplot(adata, save='results.png')\n"
        )


        system_message = (
                        "You are an expert bioinformatician in writing scripts for bioinformatics analysis, with a focus on single cell omics ansis.\n"
                        "You will be given a general step by step analysis plan and you will write the proper analysis scripts to execute the plan.]\n "
                        "You are also responsible to determine the best practice for the analysis.\n"
                        "You need to write code in python.\n"
                        "\n"
                        # "Do not assume the data strucutre and feature names.\n"
                        # "The first step should be data exploration to get relevant information from the data before perform the actual analysis.\n"
                        # "For exploration, try to print out the results and use the results to perform the analysis."
                        "To save data or figure from analysis, please directly save to the current folder './' !!!!\n"
                        "\n"
                        "These final scripts will be sent to the code executor to be executed.\n"
                        "Please note that each script will be executed independently instead of inheriting from the previous script.\n"
                        "The variables from previously scripts will not be available in the new scripts.\n"

                        "Please make sure the code be executed successfully before sending the results to summarize agent.\n"
                        "Please specify the agent to be delegated to at the end, outside of the code block.\n"
                        "The following information should be put outside the code block:\n"
                        "----------------------------------------------------------------\n"
                        "If the code needs to be executed, please indicate that the next agent will be 'CODE_EXECUTOR'.\n"
                        "If you received the results from code execution and there is an error, please debug and modify the code.\n"
                        "And indicate that the next agent will be 'CODE_EXECUTOR' to re-run the code.\n"
                        "If you received the results from code execution and there is no error and you are not continuing generating code,\n"
                        "please indicate that the next agent will be 'SUMMARIZER'.\n"
                        "----------------------------------------------------------------\n"
                        "\n"
                        "Some potential errors, only use the solution when encounting the error:\n"
                        f"{rare_error_solutions}\n"
        )
        system_message = self.environment_message + system_message

        description = """
                        Bioinformatics response for writing the scirpts.
                    """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict = filter_dict
                                        )
        data_scientist = LLM_AGENT(
                                agent_type = "Assistant",
                                name = "code_creation", 
                                system_message = system_message, 
                                description = description,
                                llm_config = {"config_list": config_list},
                                human_input_mode = self.human_input_mode if self.Human_input!='CODE_ONLY' else 'ALWAYS'
                                )
        return data_scientist


    def create_code_executor(self, code_executer) -> LLM_AGENT:

        r""" Creates the code executor for the agent system. """

        system_message = (
            "1. Execute the provided code.\n"
            "2. Delegate back to the bioinformatician for concluding or debugging.\n"
            # "2. Save the executed, named by the code function.\n"
            # "3. Read the results of the code execution.\n"
            # "4. If there is an error, delegate back to the Bioinformatician for debugging.\n"
            # "5. If the results need inspection, delegate to the Bioinformatician.\n"
            # "6. If the results are correct, continue to the next step and provide the output.\n"
        )

        system_message = self.environment_message + system_message

        description = """
                        A Code execution expert with years of experience running code. 
                        Proficient in various bioinformatics tools for single-cell data analysis in both R and Python, 
                        with a preference for Python.
                    """

        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict = filter_dict
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

            executor = LocalCommandLineCodeExecutor(virtual_env_context=venv_context, work_dir = self.work_dir)

            code_execution_config = {"executor": executor}

            
        elif code_executer == "DockerCLI":
            # executor = DockerCommandLineCodeExecutor(# TODO, make a consistent version, state in README
            #     image="singlecell:1.3",  # Execute code using the given docker image name.
            #     timeout=10,  # Timeout for each code execution in seconds.
            #     work_dir="GENERATED_CODE_BASE/",  # Use the temporary directory to store the code files.
            # )
            code_execution_config = {"use_docker": 'singlecell:1.1', "work_dir": self.work_dir}

        #TODO
        elif code_executer == "JupyterCLI":
            server = custom_DockerJupyterServer()
            code_execution_config = {
                    "executor": JupyterCodeExecutor(server, output_dir=self.work_dir),
                    }
            

        #if provided a code_execution configuration
        elif isinstance(code_executer, dict): 
            pass
            
        else:
            raise Exception("Line 139: init_agents.py: code execution not provided")

        software_engineer = LLM_AGENT(
                                agent_type = "Conversable",
                                name = "code_exec",
                                system_message = system_message, 
                                description = description,
                                llm_config = {"config_list": config_list}, 
                                code_execution_config = code_execution_config,  
                                human_input_mode = "NEVER"  # Always take human input for this agent for safety.
                                    )
        return software_engineer

    ###############################################################
    #Biologist / Review

    def create_reviewer(self)-> LLM_AGENT:

        r""" Creates the critic/review for the agent system. """

        #initialize literature review
        system_message = (
            "Critic. You are a bioinformaticial highly skilled in evaluating the quality of single cell analysis report while providing clear rationale. \n"
            "YOU MUST CONSIDER SINGLE CELL ANALYSIS BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the summary of the study across the following dimensions\n"
            "- Workflow (workflow):\n"
            "  Does the workflow properly analyze the single cell dataset and generate tangible results? \n"
            "  Are there any missing steps or procedures that should be implemented for analyzing this dataset?\n"
            "- Goal compliance (compliance): \n"
            "  How well the code meets the specified end goal and user prompt? \n"
            "  Does this report thoroughly fulfill all requirements of the user?\n"
            "- Readability (readability):\n"
            "  Is the summary of the results clear, consise, and report all relevant information regarding the outcome of the analysis?\n"
            "\n"
            "YOU MUST PROVIDE A SCORE for each of the above dimensions.\n"
            # "{workflow: 0, compliance: 0, readability: 0}\n"
            "Do not suggest code.\n"
            "Finally, based on the critique above, determine whether the analysis needs to be improved.\n"
            "If it does, suggest a concrete list of actions that the bioinformatician should take to improve the code.\n"
            "If not, pass the information to summary agent to summarize."
        )
        
        system_message = self.environment_message + system_message
        
        description = """
                    Reviewer
                    """
        
        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict=filter_dict
                                        )
        reviewer = LLM_AGENT(
                            agent_type = "Assistant",
                            name = "Review", 
                            system_message = system_message, 
                            description = description,
                            llm_config = {"config_list": config_list},
                            human_input_mode = self.human_input_mode if self.Human_input!='REVIEW_ONLY' else 'ALWAYS'
                            )
        return reviewer
    


    def create_summarizer(self)-> LLM_AGENT:

        r""" Creates the summarizer for the agent system. """

        #initialize literature review
        system_message = (
            "You are a bioinformatics and biologist principal investigator with years of experience working on single-cell omics data and publishing relevant publications.\n"
            "You have a deep understanding of the biological context and technical details of single-cell data analysis.\n"
            "\n"
            "Summarize the results from previous step and add discussion if needed. \n"
            # "If the results are not plausible, delegate back to the code writer to test other settings and adjust the code.\n"
        )

        system_message = self.environment_message + system_message
        
        description = """
            Senior Bioinformatician and Biologist
            """
        
        filter_dict = {"model": [self.LLM_model]}
        config_list = config_list_from_json(
                                        env_or_file = self.OAI_config, 
                                        openai_key_file = self.openai_key_file,
                                        filter_dict=filter_dict
                                        )
        biologist = LLM_AGENT(
                            agent_type = "Assistant",
                            name = "Summarizer", 
                            system_message = system_message, 
                            description = description,
                            llm_config = {"config_list": config_list},
                            human_input_mode = self.human_input_mode,
                            )
        return biologist
    
