FROM ai-effect-local-seed-studio-api:guided-prompt-first-v1
COPY apps/api/app /app/app
COPY deploy/aie37/initialize.py /qualification/initialize.py
COPY deploy/aie37/contracts.json /qualification/contracts.json
LABEL org.ai-effect.qualification="aie37-dutch-v1"
