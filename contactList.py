 # coding=utf-8

"""	Contiene los parametros necesarios para configurar el servicio de email.
    Tambien se encuentra almacenada una lista de confianza cuyo contenido son
    los numeros telefonicos e emails que tendran autorizacion a operar con el
    programa.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

# Configuración Email
EMAIL_SERVER = 'servidorcentral.datalogger@gmail.com'
PASS_SERVER  = 'servidorcentral1234'
SMTP_SERVER = 'smtp.gmail.com'
IMAP_SERVER = 'imap.gmail.com'
SMTP_PORT = 587
IMAP_PORT = 993

# Configuración Ethernet
LOCAL_HOST = '192.168.1.124'
UDP_PORT = 5016

# Configuración Sms
CLARO_MESSAGES_CENTER = 543200000001
CLARO_WEB_PAGE = 876966

# Configuración Bluetooth
BLUETOOTH_SERVICE_NAME = 'RFCOMM-Client01'
BLUETOOTH_MAC		   = '00:24:7E:64:7B:4A'
BLUETOOTH_UUID		   = '94f39d29-7d6d-437d-973b-fba39e49d4ee'

# Direcciones IP y puertos permitidos
allowedIpAddress = dict()
allowedIpAddress = {'Client02': ('192.168.1.110', 5025)}

# Direcciones MAC permitidas
allowedMacAddress = dict()
allowedMacAddress = {'Client02' : ('RFCOMM-Client02', '64:27:37:90:B5:B6', '94f39d29-7d6d-437d-973b-fba39e49d4ef')}

# Cuentas de correo permitidas
allowedEmails = dict()
allowedEmails = {'Client02': 'client02.datalogger@gmail.com'}

# Numeros de teléfono permitidos
allowedNumbers = dict()
allowedNumbers = {'Client02' : 3512560536}
