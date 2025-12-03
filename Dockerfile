# asetetaan pää kuva - käytetään camera kuvaa jossa on ZED SDK
FROM ghcr.io/haitomatic/jaska-dev:camera AS builder

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Install Miniforge for better ARM64 support on Jetson
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    bzip2 \
    ca-certificates \
    build-essential \
    gcc \
    libffi-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Miniforge
RUN wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh -O /tmp/miniforge.sh && \
    bash /tmp/miniforge.sh -b -p /opt/conda && \
    rm /tmp/miniforge.sh

ENV PATH=/opt/conda/bin:$PATH

# Luodaa käyttäjä rootin tilalle ja lisätään dialoutryhmään jotta voidaan lukea usb laitteita
ARG USER=Jaakko
ARG UID=2000
RUN useradd --create-home --uid ${UID} ${USER} \
    && usermod -a -G dialout ${USER}

#Luodaan työskentely kirjasto
WORKDIR /Jaska

# kopioidaan conda environment definition
COPY environment.yaml .

# Create conda environment from environment.yaml
RUN conda env create -f environment.yaml && \
    conda clean -afy

# Install ZED Python API from the SDK installation into conda environment
RUN cd /usr/local/zed/lib/python3 && \
    /opt/conda/envs/jaska/bin/pip install --no-cache-dir .

# kopioidaan python riippuvuudet (nicegui, etc.)
COPY requirements.txt .

# asennetaan ne conda environmenttiin
RUN /opt/conda/envs/jaska/bin/pip install --no-cache-dir -r /Jaska/requirements.txt

# Kopiodaan kaikki muutkin tidostot

COPY main.py .
COPY ogmain.py .
COPY README.md .
COPY testi.py .
COPY testigui.py .
COPY source/ ./source

# annetaan kättäjälle oikeudet
RUN chown -R ${USER}:${USER} /Jaska

# Set up conda activation script
RUN echo "#!/bin/bash" > /opt/conda/activate_jaska.sh && \
    echo "source /opt/conda/etc/profile.d/conda.sh" >> /opt/conda/activate_jaska.sh && \
    echo "conda activate jaska" >> /opt/conda/activate_jaska.sh && \
    chmod +x /opt/conda/activate_jaska.sh

# Add ZED SDK Python bindings to PYTHONPATH
ENV PYTHONPATH="/Jaska:/usr/local/zed/lib/python3:${PYTHONPATH}"

# Source conda environment in bashrc for root
RUN echo "source /opt/conda/activate_jaska.sh" >> /root/.bashrc

# Source conda environment in bashrc for user
RUN echo "source /opt/conda/activate_jaska.sh" >> /home/${USER}/.bashrc

USER ${USER}
WORKDIR /Jaska

# Nicegui portti näkyviin
EXPOSE 8080

# Create entrypoint script that activates conda environment
USER root
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Activate conda environment\n\
source /opt/conda/activate_jaska.sh\n\
\n\
# Execute command\n\
exec "$@"\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

USER ${USER}

ENTRYPOINT ["/entrypoint.sh"]
#suoritetaan nicegui
CMD [ "python", "testigui.py" ]