FROM python:3.8-bullseye
ENV LC_ALL=C.UTF-8
RUN apt update && apt upgrade -y
WORKDIR /usr/src/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
ENTRYPOINT ["python", "main.py"]