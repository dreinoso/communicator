# coding=utf-8
"""	Este objeto se ocupa de leer las configuraciones establecidas para
	el sistema, para determinar el comportamiento del mismo

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: 17 de Abril de 2015 """

#  Configuraciones LAN 
LAN_PROTOCOL = 'TCP'
LOCAL_HOST = '192.168.1.124'
UDP_PORT = 5016
CLOSE_PORT = True # Para cerrar el puerto en caso de estar ocupado

# Configuraciones Bluetooth 
BLUETOOTH_PROTOCOL = 'TCP'
BLUETOOTH_SERVICE_NAME = 'RFCOMM-Client01'
BLUETOOTH_MAC		   = '00:24:7E:64:7B:4A'
BLUETOOTH_UUID		   = '94f39d29-7d6d-437d-973b-fba39e49d4ee'

# Configuraciones Email 
EMAIL_SERVER = 'servidorcentral.datalogger@gmail.com'
PASS_SERVER  = 'servidorcentral1234'
SMTP_SERVER = 'smtp.gmail.com'
IMAP_SERVER = 'imap.gmail.com'
SMTP_PORT = 587
IMAP_PORT = 993

# Configuraciones Sms 
CLARO_MESSAGES_CENTER = 543200000001
CLARO_WEB_PAGE = 876966

priorityLevels = dict() # Diccionario para la selección de envio por prioridades
priorityLevels = {'ethernet': 4,
				'bluetooth': 4,
				'email': 2,
				'sms': 0}

consoleLoggingLevel = 'INFO' # Valores que determinan el nivel de notificaciones en consola y en archivo log
fileLoggingLevel = 'DEBUG'


def readConfigFile():
	"""Se leen las configuraciones de un archivo definido, en caso de que la lectra 
	sea valida no habra excepción
	@return: Mensaje con un mensaje de que la lectura fue correcta o nada en caso contrario
	@type: str"""
	try:
		configurationFile =  open('properties.conf').readlines() # Apertura de Archivo
		configurationFile = ''.join(configurationFile) # Conversión a String para ejecución
		exec(configurationFile)
		return '[CONFIG READER] Archivo de configuración cargado correctamente.'
	except Exception:
		return None