# set base image
FROM docker.io/arm64v8/ubuntu:24.04

#Set Working directory in container
WORKDIR /Jaska

# copy file where is python depencies

COPY requirements.txt .

# install depencies

RUN pip install -r requirements.txt

# copy other files and directories

COPY main.py .
COPY ogmain.py .
COPY environment.yaml .
COPY README.md .
COPY testi.py .
COPY testigui.py .
COPY source/ .

CMD [ "python", "./testigui.py" ]