# coding=utf-8
"""	Este objeto se ocupa de leer las configuraciones establecidas para
	el sistema, para determinar el comportamiento del mismo

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: 17 de Abril de 2015 """

# Configuraciones LAN 
LAN_PROTOCOL = 'TCP'
LOCAL_HOST   = 'localhost'
TCP_PORT 	 = 6000 
UDP_PORT     = 6010
CLOSE_PORT   = True # Para cerrar el puerto en caso de estar ocupado

# Configuraciones Bluetooth 
BLUETOOTH_PROTOCOL	   = 3
BLUETOOTH_SERVICE_NAME = 'RFCOMM-Client01'
BLUETOOTH_MAC		   = '00:24:7E:64:7B:4A'
BLUETOOTH_UUID		   = '94f39d29-7d6d-437d-973b-fba39e49d4ee'

# Configuraciones Email
EMAIL_SERVER = 'client01.datalogger@gmail.com'
PASS_SERVER  = 'client01dl'
SMTP_SERVER  = 'smtp.gmail.com'
IMAP_SERVER  = 'imap.gmail.com'
SMTP_PORT	 = 587
IMAP_PORT	 = 993

# Configuraciones Sms
CLARO_MESSAGES_CENTER  = 543200000001
CLARO_TELEPHONE_NUMBER = 3516178949
CLARO_WEB_PAGE         = 876966
CLARO_CHARACTER_LIMIT  = 160

priorityLevels = dict() # Diccionario para la selección de envio por prioridades
priorityLevels = {'lan' : 0,
				  'bluetooth': 0,
				  'email'	 : 0,
				  'sms'		 : 4}

consoleLoggingLevel = 'INFO' # Valores que determinan el nivel de notificaciones en consola y en archivo log
fileLoggingLevel = 'DEBUG'

def readConfigFile():
	"""Se leen las configuraciones de un archivo definido, en caso de que la lectra 
	sea valida no habra excepción
	@return: Mensaje con un mensaje de que la lectura fue correcta o nada en caso contrario
	@type: str"""
	try:
		configurationFile = open('properties.conf').readlines() # Apertura de Archivo
		configurationFile = ''.join(configurationFile) # Conversión a String para ejecución
		exec(configurationFile)
		return True
	except Exception:
		return False
