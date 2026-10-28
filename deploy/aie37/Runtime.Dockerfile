ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG CAPTURE_ROLE
ENV PILOT_CAPTURE_ROLE=${CAPTURE_ROLE}
COPY deploy/aie37/runtime.py deploy/aie37/capture_algorithms.py deploy/aie37/contracts.json /app/qualification/
COPY apps/api/app/services/dutch_capture_contract.py apps/api/app/services/parameter_values.py /app/qualification/
LABEL org.ai-effect.qualification="aie37-dutch-v1"
CMD ["python", "/app/qualification/runtime.py"]
