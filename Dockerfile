FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1 \
	UV_COMPILE_BYTECODE=1 \
	UV_LINK_MODE=copy \
	PATH="/app/.venv/bin:$PATH" \
	HOST=0.0.0.0

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 curl ca-certificates \
	&& rm -rf /var/lib/apt/lists/*

COPY . .
RUN uv sync --frozen --no-dev \
	&& bash scripts/fetch_vendor.sh

# Run as a non-root user; the app writes to demos/ and the user demos volume.
RUN useradd --create-home --uid 1000 trilobot \
	&& mkdir -p /data/demos \
	&& chown -R trilobot:trilobot /data/demos /app/control_scripts/blockly/demos
ENV TRILOBOT_USER_DEMOS_DIR=/data/demos
VOLUME /data/demos
USER trilobot

EXPOSE 8750

CMD ["python", "control_scripts/blockly/app.py"]
