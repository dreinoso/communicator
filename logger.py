 # coding=utf-8

import logging
import sys
import configReader

loggingLevels = {'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL}

consoleLoggingLevel = configReader.consoleLoggingLevel.upper()
fileLoggingLevel =  configReader.fileLoggingLevel.upper()

logger = ''
fileHandler = ''

def set(name):
	global logger
	logger = logging.getLogger(name)
	logger.setLevel(loggingLevels[fileLoggingLevel])

	consoleHandler = logging.StreamHandler() # create console handler and set level to debug
	consoleHandler.setLevel(logging.DEBUG)
	consoleFormatter = logging.Formatter('[%(levelname)s] %(message)s') # create formatter
	consoleHandler.setFormatter(consoleFormatter) # add formatter to ch
	logger.addHandler(consoleHandler) # add ch to logger

	fileHandler = logging.FileHandler('Historial_de_Eventos.log') # Se crea el manejador para archivo de log
	fileHandler.setLevel(logging.DEBUG)
	fileFormatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s') # create formatter
	fileHandler.setFormatter(fileFormatter) # add formatter to ch
	logger.addHandler(fileHandler) # add ch to logger

#def close():
#	fileHandler.close()

def write(logType, message):
	global logger
	if logType == 'DEBUG': logger.debug(message)
	elif logType == 'INFO': logger.info(message)
	elif logType == 'WARNING': logger.warn(message)
	elif logType == 'ERROR': logger.error(message)
	elif logType == 'CRITICAL': logger.critical(message)
	else: logger.error('Intento de escribir en Log erroneo no se designo un tipo de log correcto')
