 # coding=utf-8

"""	Contiene los parametros necesarios para configurar el servicio de email.
    Tambien se encuentra almacenada una lista de confianza cuyo contenido son
    los numeros telefonicos e emails que tendran autorizacion a operar con el
    programa.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Abril de 2015 """

# Hosts permitidos
allowedHosts = dict()
allowedHosts = {'client02' : ('192.168.1.6', 6000, 6010)}

# Direcciones MAC permitidas
allowedMacAddress = dict()
allowedMacAddress = {'client02' : ('RFCOMM-Client02', '11:11:11:11:11:11', '94f39d29-7d6d-437d-973b-fba39e49d4ef')}

# Cuentas de correo permitidas
allowedEmails = dict()
allowedEmails = {'client02' : 'client02.datalogger@gmail.com',
				 'client03' : 'mauriciolg.90@gmail.com'}

# Numeros telefónicos permitidos
allowedNumbers = dict()
allowedNumbers = {'client02' : 3512560536,
				  'client03' : 3512641040}
