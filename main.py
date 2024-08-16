
import os
import json
import requests
import sys
from src.groupchat import init_groupchat
from src.agents.init_agents import bioagent
import autogen

## RAG data curation 
from src.agents.init_RAG_agents import RAG_bioagent
from src.RAG_groupchat import init_rag_groupchat

import argparse
from dotenv import load_dotenv
# load keys
load_dotenv()

argparser = argparse.ArgumentParser()
argparser.add_argument("--config", default='./OAI_config.json', help="Path to OAI config file")
argparser.add_argument("--llm", default='gpt-4o-mini', help="LLM model name")
argparser.add_argument("--code_exec", default='LocalCLI', help="Code executor, choose from DockerCLI and LocalCLI")
argparser.add_argument("--human_input", default='ALWAYS', help="Human input mode, choose from ALWAYS, NEVER, TERMINATE")
argparser.add_argument("--log_with_agentops", default=False, help="Log with agentops")
argparser.add_argument("--agentops_tag", default='', help="Agentops tag")
argparser.add_argument("--logfile", default="runtime.log", help="Log file name")
argparser.add_argument("--prompt", default='example_prompt.txt', help="Prompt file to start the conversation")
argparser.add_argument("--work_dir", default='./', help="Working directory")
argparser.add_argument("--data_curation", default=False, help="Flag for if data curation is needed.")
argparser.add_argument("--data_curation_prompt", default='data_curation_example_prompt.txt', help="Prompt file to start conversation when using data curation module.")

args = argparser.parse_args()

OAI_CONFIG = args.config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = args.llm # 'gpt-4o-mini
CODE_EXTENSIONS = args.code_exec
HUMAN_INPUT_MODE = args.human_input # ['ALWAYS', 'NEVER', 'TERMINATE','CODE_ONLY', 'PLAN_ONLY', 'REVIEW_ONLY']
LOG_WITH_AGENTOPS = args.log_with_agentops
data_curation = args.data_curation

def main():

    if LOG_WITH_AGENTOPS:
        import agentops
        agentops.init(default_tags=[args.agentops_tag])
    else:
        # log
        logging_session_id = autogen.runtime_logging.start(
            logger_type="file", config={"filename": args.logfile}
        )
        print("Logging session ID: " + str(logging_session_id))

    #check if OAI files exist (key, config)

    #if using OpenAI models
    if 'gpt' not in LLM_MODEL: # not fully implemented, use with caution
        #check if OLLAMA server is running
        ollama_response = requests.get("http://0.0.0.0:11434/")
        if ollama_response.status_code == 200 :
            print("OLLAMA server is running on following address: %s" % "http://0.0.0.0:11434/")
            print("OLLAMA api endpoint: %s\n" % "http://127.0.0.1:11434/v1")
        else:
            print("""
                USER WARNING: OLLAMA server is not running on seen endpoint. Local LLMs are inactive. 
                Please start OLLAMA on designated endpoint or change OAI config to match endpoint.
                Designated endpoint: http://127.0.0.1:11434/v1
                """)
        
    
    #### For Groupchat Without Data Curation #### 
    if not data_curation:
        #create agents
        agents = bioagent(OAI_CONFIG, OPENAI_API_KEY, LLM_MODEL, HUMAN_INPUT_MODE, args.work_dir)
        planner = agents.create_planner()
        bioinformatician = agents.create_bioinformatician()
        code_executor = agents.create_code_executor(code_executer = CODE_EXTENSIONS)
        summarizer = agents.create_summarizer()
        reviewer = agents.create_reviewer()

        # agent_list = [planner, data_scientist, software_engineer, biologist]
        # use dict to query by key instead of index
        agent_dict = {
            "planner": planner,
            "bioinformatician": bioinformatician,
            "code_executor": code_executor,
            "summarizer": summarizer,
            "reviewer": reviewer
        }

        #create groupchat
        groupchat, groupchat_manager = init_groupchat(agent_dict = agent_dict, OAI_config = OAI_CONFIG, openai_key_file = OPENAI_API_KEY, LLM_model = LLM_MODEL)


        prompt = open(args.prompt, 'r').read()
        

        groupchat_manager.initiate_chat(planner, message = prompt, verbose=True)
    
    if data_curation:
        #initiate RAG agents 
        RAG_agents = RAG_bioagent(OAI_CONFIG, OPENAI_API_KEY, LLM_MODEL)
        boss = RAG_agents.create_boss(code_executer = CODE_EXTENSIONS)
        boss_aid = RAG_agents.create_boss_aid(code_executer = CODE_EXTENSIONS)
        coder = RAG_agents.create_coder()
        pm = RAG_agents.create_pm()
        rag_reviewer = RAG_agents.create_reviewer()

        #initiate automated scRNA agents
        agents = bioagent(OAI_CONFIG, OPENAI_API_KEY, LLM_MODEL, HUMAN_INPUT_MODE, args.work_dir)
        planner = agents.create_planner()
        bioinformatician = agents.create_bioinformatician()
        code_executor = agents.create_code_executor(code_executer = CODE_EXTENSIONS)
        summarizer = agents.create_summarizer()
        reviewer = agents.create_reviewer()

        rag_agent_dict = {
            "boss_aid": boss_aid,
            "boss": boss,
            "coder": coder, 
            "pm": pm,
            "rag_reviewer": rag_reviewer
        }

        scauto_agent_dict = {
            "planner": planner,
            "bioinformatician": bioinformatician,
            "code_executor": code_executor,
            "summarizer": summarizer,
            "reviewer": reviewer
        }

        ### Create groupchat for Data Curation 
        rag_groupchat, rag_groupchat_manager = init_rag_groupchat(agent_dict = rag_agent_dict, OAI_config = OAI_CONFIG, openai_key_file = OPENAI_API_KEY, LLM_model = LLM_MODEL)

        ### Create groupchat for Automated scRNA analysis
        groupchat, groupchat_manager = init_groupchat(agent_dict = scauto_agent_dict, OAI_config = OAI_CONFIG, openai_key_file = OPENAI_API_KEY, LLM_model = LLM_MODEL)
        

        def workflow():
            
            prompt = open(args.data_curation_prompt, 'r').read()
            
            tasks = [
                    f"""
                    Given the biomedical task below, I want to query and fetch relevant single-cell data and
                    its associated metadata from the Cellxgene-census dataset.
                    
                    Make sure to download and save the adata object(s) in the appropriate format. Once the adata object successfully downloads, reply 'TERMINATE'.
                    
                    Since the dataset will be large, just extract a small subset of the data for now.

                    Here is the biomedical task:
                    {prompt}
                    """,
                    f"""
                    The adata object containing the relevant dataset has been created. Please use Python and Scanpy to read and analyze the file.

                    Here is the biomedical task:
                    {prompt}
                    """
                    ]

            # Initiate the first task with rag_groupchat_manager
            res1 = boss.initiate_chat(
                recipient=rag_groupchat_manager,
                message=tasks[0],
                summary_method="reflection_with_llm",
                summary_prompt="Please indicate what is in the anndata object, where it is stored, and how it can be accessed.",
            )

            # Check if the first task is completed
            if res1:
                # Initiate the second task with groupchat_manager
                res2 = groupchat_manager.initiate_chat(
                    recipient=groupchat_manager,
                    message=tasks[1],
                    summary_method="reflection_with_llm",
                    summary_prompt="Please summarize the analysis and results."
                )
                return res2
            else:
                print("The first task was not completed successfully.")
                return None

        # Execute the workflow
        workflow()

    if LOG_WITH_AGENTOPS:
        agentops.end_session("Success")
    else:
        autogen.runtime_logging.stop()


if __name__ == '__main__':
    main()