FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	HOST=0.0.0.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

COPY . .
RUN pip install --no-cache-dir -r control_scripts/blockly/requirements.txt \
	&& bash scripts/fetch_vendor.sh

# Run as a non-root user; the app writes to demos/ and the user demos volume.
RUN useradd --create-home --uid 1000 trilobot \
	&& mkdir -p /data/demos \
	&& chown -R trilobot:trilobot /data/demos /app/control_scripts/blockly/demos
ENV TRILOBOT_USER_DEMOS_DIR=/data/demos
VOLUME /data/demos

EXPOSE 8750

CMD ["python", "scripts/docker_entrypoint.py"]
