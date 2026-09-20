FROM python:3.12-slim
WORKDIR /app
COPY implant/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY implant/ .
COPY crypto.py .
CMD ["python", "agent.py"]
