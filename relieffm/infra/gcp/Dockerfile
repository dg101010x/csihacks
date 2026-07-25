# Reproducible training/serving image. Not used by train_vm.sh (which runs
# directly on a Deep Learning VM image for simplicity) -- this is for
# reproducing a run outside GCP, or for a future containerized Vertex AI /
# model_gateway deployment.
FROM pytorch/pytorch:2.4.0-cuda12.1-cudnn9-runtime

WORKDIR /opt/relieffm
COPY . .
RUN pip install --no-cache-dir -e .

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["uvicorn", "services.model_inference.app:app", "--host", "0.0.0.0", "--port", "8080"]
