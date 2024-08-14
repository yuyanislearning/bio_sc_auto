
import importlib.metadata
import json
import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from openai.types.beta.assistant import Assistant
from packaging.version import parse

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

def filter_config(
    config_list: List[Dict[str, Any]],
    filter_dict: Optional[Dict[str, Union[List[Union[str, None]], Set[Union[str, None]]]]],
    exclude: bool = False,
) -> List[Dict[str, Any]]:
    
    if filter_dict:
        return [
            item
            for item in config_list
            if all(_satisfies_criteria(item.get(key), values) != exclude for key, values in filter_dict.items())
        ]
    return config_list

def _satisfies_criteria(value: Any, criteria_values: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, list):
        return bool(set(value) & set(criteria_values))  # Non-empty intersection
    else:
        return value in criteria_values


def config_list_from_json(
    env_or_file: str,
    file_location: Optional[str] = "",
    openai_key_file: Optional[str] = "",
    filter_dict: Optional[Dict[str, Union[List[Union[str, None]],
                                          Set[Union[str, None]]]]] = None
) -> List[Dict[str, Any]]:

    env_str = None

    if env_str:
        # The environment variable exists. We should use information from it.
        if os.path.exists(env_str):
            # It is a file location, and we need to load the json from the file.
            with open(env_str, "r") as file:
                json_str = file.read()
        else:
            # Else, it should be a JSON string by itself.
            json_str = env_str
        config_list = json.loads(json_str)
    else:
        # The environment variable does not exist.
        # So, `env_or_file` is a filename. We should use the file location.
        if file_location is not None:
            config_list_path = os.path.join(file_location, env_or_file)
        else:
            config_list_path = env_or_file

        with open(config_list_path) as json_file:
            config_list = json.load(json_file)
            #added in OAI key
            for item in config_list:
                item["api_key"] = OPENAI_API_KEY#open(openai_key_file, 'r').read()
    return filter_config(config_list, filter_dict)