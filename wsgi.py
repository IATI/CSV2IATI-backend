import logging, sys
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0, 'ABS_PATH_TO_PYENV_IN_CONVERTER_FOLDER/CSV-IATI-Converter/pyenv/lib/python2.7/site-packages')
sys.path.insert(0, 'ABS_PATH_TO_CONVERTER_FOLDER/CSV-IATI-Converter')
from csviati import app as application
