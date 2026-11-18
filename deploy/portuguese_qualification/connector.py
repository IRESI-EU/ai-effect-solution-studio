"""Launch only the configured connector in the isolated qualification project."""
import sys
sys.path.insert(0, '/qualification-source')
from common import create_app
import uvicorn


def no_legacy(request):
    raise ValueError('Legacy dispatch is not installed in this qualification environment')


uvicorn.run(create_app({'TrainModel': no_legacy, 'GenerateData': no_legacy}), host='0.0.0.0', port=8080, log_level='warning')
