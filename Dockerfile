FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Override at runtime: docker run -e TENANT_CONFIG=tenants/beachhacks.yaml ...
ENV TENANT_CONFIG=tenants/test_tenant.yaml

CMD ["python", "-m", "adapters.agent"]
