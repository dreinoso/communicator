 # coding=utf-8

"""	Contiene los parametros necesarios para configurar el servicio de email.
    Tambien se encuentra almacenada una lista de confianza cuyo contenido son
    los numeros telefonicos e emails que tendran autorizacion a operar con el
    programa.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

SMTP_SERVER = 'smtp.gmail.com'
IMAP_SERVER = 'imap.gmail.com'
SMTP_PORT = 587
IMAP_PORT = 993

#Configuración de la cuenta para el servidor (debe ser una cuenta de gmail)
EMAIL_SERVER = 'servidorcentral.datalogger@gmail.com'
PASS_SERVER  = 'servidorcentral1234'

# Configuracion Bluetooth local
BLUETOOTH_SERVICE_NAME = 'RFCOMM-Client01'
BLUETOOTH_MAC		   = '00:24:7E:64:7B:4A'
BLUETOOTH_UUID		   = '94f39d29-7d6d-437d-973b-fba39e49d4ee'


allowedIpAddress = dict()
allowedIpAddress = {'Client01': '192.168.1.1',
				   'Client02': '127.0.0.1'}

allowedPorts = dict()
allowedPorts = {'Client01': 5005,
				'Client02': 5006}

destinationBluetooth = dict()
destinationBluetooth = {'Client02' : ('RFCOMM-Client02', '11:11:11:11:11:11', '94f39d29-7d6d-437d-973b-fba39e49d4ef')}

sourceBluetooth = dict()
sourceBluetooth = {'11:11:11:11:11:11' : 'Client02'}

#Cuentas de correo permitidas para la interacción.
allowedEmails = dict()
allowedEmails = {'Client01': 'cliente1.datalogger@gmail.com',
				 'Client02': 'Cliente2.daalogger@gmail.com'}

allowedNumbers = dict()
allowedNumbers = {'Cliente01': '3512650513'}
