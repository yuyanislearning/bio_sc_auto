# ScAuto : A multi-agent architecture for automated single cell analysis with human feedback.

## Setup
### Autogen
Autogen installation

Follow the instructions [here](https://microsoft.github.io/autogen/docs/installation/) to install autogen.

ScAuto supports two types of code execution: Docker and local. Docker allows to create consistent environments that are portable and isolated from the host OS, while local is similar to how it is executed normally. 

### Docker
Instruction for installing Docker can be found [here](https://microsoft.github.io/autogen/docs/installation/Docker)

```
docker build -t singlecell:1.0 . # build docker image
```

if runnning docker with colima, need to set the docker.sock file, check this:
https://github.com/abiosoft/colima/blob/main/docs/FAQ.md#cannot-connect-to-the-docker-daemon-at-unixvarrundockersock-is-the-docker-daemon-running

```
COLIMA_HOME=~/.colima
sudo ln -sf $COLIMA_HOME/default/docker.sock /var/run/docker.sock
```


To install packages that are not installed already, modify the Dockerfile and rebuild the image.

### OpenAI API
To use model from OpenAI, provide the OPENAI_API_KEY to .env file:
```
OPENAI_API_KEY="YOUR_API_KEY"
```

Similary, if you would like to track usage with AgentOps, provide the keys in .env file.



## Run
```{bash}
python main.py \
    --code_exec DockerCLI \
    --human_input ALWAYS \
    --logfile runtime.log \
    --prompt {Your_prompt_file} \
    --work_dir {Working_directory}
```

To start the conversion, a prompt of the question needs to be provided. 

You can incorporate the neccessary description of the dataset, the location of the dataset (note that if you are using a docker, that should be the relative path in docker, and make sure that you put the dataset in the working directory for docker), and finally the bioinformatics analysis you want to perform and the desired output.

Put this prompt in a text file and provide it by --prompt.

work_dir will be the working directory where the analysis will be performed and the results will be stored.



You can also follow the example notebook to run a notebook instead of scripts





