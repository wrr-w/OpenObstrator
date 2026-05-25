import sys; sys.path.insert(0, '.')
from server.app import app
import uvicorn
uvicorn.run(app, host='127.0.0.1', port=8092, log_level='info')
