# coding=utf-8
"""	Este objeto se ocupa de leer las configuraciones establecidas para
	el sistema, para determinar el comportamiento del mismo

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Abril de 2015 """

import os

priorityLevels = dict() # Diccionario para la selección de envio por prioridades
priorityLevels = {'ethernet': 4,
				'bluetooth': 4,
				'email': 2,
				'sms': 0}

consoleLoggingLevel = 'INFO' # Valores que determinan el nivel de notificaciones en consola y en archivo log
fileLoggingLevel = 'DEBUG'


def readConfigFile():
	configurationFile =  open('properties.conf').readlines() # Apertura de Archivo
	configurationFile = ''.join(configurationFile) # Conversión a String para ejecución
	try:
		exec(configurationFile)
		return '[CONFIG READER] Archivo de configuración cargado correctamente.'
	except Exception:
		return None