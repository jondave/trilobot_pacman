FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	HOST=0.0.0.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
	&& rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -r control_scripts/blockly/requirements.txt

EXPOSE 8750

CMD ["python", "control_scripts/blockly/app.py"]
