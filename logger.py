 # coding=utf-8
"""Modulo para encargarse de las funciones de logging, es decir la escritura
	de los eventos del sistema.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

import logging
import configReader

loggingLevels = {'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL}

configReader.readConfigFile()
consoleLoggingLevel = configReader.consoleLoggingLevel.upper() # Se requiere nombres en mayúscula
fileLoggingLevel =  configReader.fileLoggingLevel.upper()

logger = ''

def set(name):
	"""Se configura el logger, los manejadores (junto con los niveles de mensajes) 
	y los formatos de los mismos.
	@param name: Nombre del objeto logger
	@type name: str
	"""
	global logger
	logger = logging.getLogger(name) # se crea el objeto logger
	logger.setLevel(loggingLevels[fileLoggingLevel])

	consoleHandler = logging.StreamHandler() # Se crea el manejador de consola
	consoleHandler.setLevel(consoleLoggingLevel) # Se define el nivel para mostrar mensajes
	consoleFormatter = logging.Formatter('[%(levelname)s] %(message)s') # Se crea y configura el formato
	consoleHandler.setFormatter(consoleFormatter)
	logger.addHandler(consoleHandler) # Se añade el manejador al objeto logger

	fileHandler = logging.FileHandler('Historial_de_Eventos.log') # Se crea el manejador para archivo de log (no requiere cierre)
	fileHandler.setLevel(fileLoggingLevel) # Se define el nivel para almacenar mensajes
	fileFormatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s') # Se crea y configura el formato
	fileHandler.setFormatter(fileFormatter)
	logger.addHandler(fileHandler) # Se añade el manejador al objeto logger

def write(logType, message):
	"""Se añade un mensaje al logger si es correcto el tipo de mensaje, el mensaje
	es añadido tanto al archivo logger como mostrado en consola dependiendo de los
	niveles que se hayan definido.
	@param logType: Tipo de mensaje Log
	@type logType: str
	@param message: Mensaje para logger.
	@type message: str"""
	global logger
	if logType == 'DEBUG': logger.debug(message)
	elif logType == 'INFO': logger.info(message)
	elif logType == 'WARNING': logger.warn(message)
	elif logType == 'ERROR': logger.error(message)
	elif logType == 'CRITICAL': logger.critical(message)
	else: logger.error('Intento de escribir en Log erroneo no se designo un tipo de log correcto')
