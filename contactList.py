 # coding=utf-8

"""	Contiene los parametros necesarios para configurar el servicio de email.
    Tambien se encuentra almacenada una lista de confianza cuyo contenido son
    los numeros telefonicos e emails que tendran autorizacion a operar con el
    programa.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

# Direcciones IP y puertos permitidos
allowedIpAddress = dict()
allowedIpAddress = {'client02': ('192.168.1.110', 5025)}

# Direcciones MAC permitidas
allowedMacAddress = dict()
allowedMacAddress = {'client02' : ('RFCOMM-Client02', '64:27:37:90:B5:B6', '94f39d29-7d6d-437d-973b-fba39e49d4ef')}

# Cuentas de correo permitidas
allowedEmails = dict()
allowedEmails = {'client02' : 'client02.datalogger@gmail.com',
				 'client03' : 'meschoyez@gmail.com'}

# Numeros de teléfono permitidos
allowedNumbers = dict()
allowedNumbers = {'client02' : 3512560536,
				  'client03' : 123456789}
