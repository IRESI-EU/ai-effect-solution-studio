FROM ai-effect-aie37-api:qualification-v3
COPY apps/api/app /app/app
LABEL org.ai-effect.integration="qualified-dutch-goal-to-results-v1"
