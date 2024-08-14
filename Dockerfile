# Start with the existing image as a base
FROM conda/miniconda3

# Update package lists and install additional packages
# RUN sudo apt-get update
# RUN sudo apt-get install -y \
#     build-essential \
#     python3-dev \
#     libhdf5-dev

# ENV PATH="/root/miniconda3/bin:${PATH}"


# RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh && \
#     mkdir -p /root/.conda && \
#     bash miniconda.sh -b -p /root/miniconda3 && \
#     rm -f miniconda.sh 
RUN conda install -c conda-forge scanpy python-igraph leidenalg
# RUN python -m pip install scanpy

# Set the default command to execute when the container starts
# CMD ["executable", "parameters"]
# CMD ["echo", "$PATH"]
CMD ["python", "-c", "import scanpy; print(scanpy.version)"]
