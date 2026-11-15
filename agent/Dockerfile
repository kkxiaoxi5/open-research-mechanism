FROM python:3.12-slim
WORKDIR /app
COPY src/ ./src/
COPY skills/ ./skills/
ENV PYTHONPATH=/app/src
EXPOSE 8765
# State lives on a volume so the ledger survives the container.
CMD ["python", "-m", "mechanism_agent", "--home", "/state", "serve", \
     "--host", "0.0.0.0", "--port", "8765"]
