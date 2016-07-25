 # coding=utf-8

import sys
import logging

CONSOLE_FORMAT = '[%(levelname)s] %(message)s'
FILE_FORMAT = '[%(asctime)s][%(levelname)s] %(message)s'

logger = logging.getLogger(__name__) # Creamos el objeto Logger

def set(FILE_LOG, FILE_LOGGING_LEVEL, CONSOLE_LOGGING_LEVEL):
	logger.setLevel(logging.DEBUG)

	fileFormatter = logging.Formatter(FILE_FORMAT) # Creamos el 'formatter' para el archivo LOG
	fileHandler = logging.FileHandler(FILE_LOG)    # Creamos el 'handler' para el archivo LOG
	fileHandler.setLevel(FILE_LOGGING_LEVEL)       # Establecemos el nivel para almacenar los mensajes
	fileHandler.setFormatter(fileFormatter)        # Establecemos el formato de los mensajes
	logger.addHandler(fileHandler)                 # Añadimos el 'handler' al objeto Logger

	consoleFormatter = logging.Formatter(CONSOLE_FORMAT) # Creamos el 'formatter' para la consola
	consoleHandler = logging.StreamHandler(sys.stdout)   # Creamos el 'handler para la consola
	consoleHandler.setLevel(CONSOLE_LOGGING_LEVEL)       # Establecemos el nivel para mostrar los mensajes
	consoleHandler.setFormatter(consoleFormatter)        # Establecemos el formato de los mensajes
	logger.addHandler(consoleHandler)                    # Añadimos el 'handler' al objeto Logger

def write(logType, message):
	if logType is 'DEBUG': logger.debug(message)
	elif logType is 'INFO': logger.info(message)
	elif logType is 'WARNING': logger.warn(message)
	elif logType is 'ERROR': logger.error(message)
	elif logType is 'CRITICAL': logger.critical(message)
	else: logger.error('Intento de escribir en Log erroneo no se designo un tipo de log correcto')
