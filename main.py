
import os
import json
import requests
import sys
from src.groupchat import init_groupchat
from src.agents.init_agents import bioagent
import autogen

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

args = argparser.parse_args()

OAI_CONFIG = args.config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_MODEL = args.llm # 'gpt-4o-mini
CODE_EXTENSIONS = args.code_exec
HUMAN_INPUT_MODE = args.human_input # ['ALWAYS', 'NEVER', 'TERMINATE','CODE_ONLY', 'PLAN_ONLY', 'REVIEW_ONLY']
LOG_WITH_AGENTOPS = args.log_with_agentops

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

    if LOG_WITH_AGENTOPS:
        agentops.end_session("Success")
    else:
        autogen.runtime_logging.stop()




if __name__ == '__main__':
    main()