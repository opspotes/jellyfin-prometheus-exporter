FROM python:3.11-alpine

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
COPY main.py /app/main.py

EXPOSE 8000
CMD /app/main.py
