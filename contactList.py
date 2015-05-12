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

#Cuentas de correo permitidas para la interacción.
allowedEmails = dict()
allowedEmails = {'Cliente1': 'cliente1.datalogger@gmail.com',
				'Cliente2': 'Cliente2.daalogger@gmail.com'}

allowedIpAdress = dict()
allowedIpAdress = {'Cliente1': '192.168.1.1',
				'Cliente2': '127.0.0.1'}