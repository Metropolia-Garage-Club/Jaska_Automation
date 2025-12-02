# asetetaan pää kuva
FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Luodaa käyttäjä rootin tilalle ja lisätään dialoutryhmään jotta voidaan lukea usb laitteita
ARG USER=Jaakko
ARG UID=1000
RUN useradd --create-home --uid ${UID} ${USER} \
    && usermod -a -G dialout ${USER} 

#Luodaan työskentely kirjasto
WORKDIR /Jaska

# kopioidaan python riippuvuudet

COPY requirements.txt .

# asennetaan ne

RUN pip install --no-cache-dir -r /Jaska/requirements.txt

# Kopiodaan kaikki muutkin tidostot

COPY main.py .
COPY ogmain.py .
COPY environment.yaml .
COPY README.md .
COPY testi.py .
COPY testigui.py .
COPY source/ ./source

# annetaan kättäjälle oikeudet
RUN chown -R ${USER}:${USER} /Jaska

USER ${USER}
WORKDIR /Jaska
# varmistetaan että python loytää tarvittavat tiedostot
ENV PYTHONPATH="/Jaska"

# Nicegui portti näkyviin
EXPOSE 8080

#suoritetaan nicegui
CMD [ "python", "testigui.py" ]