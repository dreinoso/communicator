#Módulo de Comunicación Inteligente
Corresponde a un módulo de comunicación inteligente para comunicación punto a punto. Las comunicaciones que se pretenden son SMS, Email, Red, Wifi y Bluetooth.

##Requisitos del módulo
	-Python 2.7
	-Pip para la instalación de los módulos (sudo apt-get install pip)
		En caso de problemas de dependencias con pip (sudo apt-get install python python-dev libatlas-base-dev gcc gfortran g++)
	-PyBluez para la ejecución con Bluetooth (sudo pip install pybluez)
		En caso de problemas de dependencias con pip (sudo apt-get install libbluetooth-dev)
	-WVdial para obtener el puerto del módem (sudo apt-get install wvdial)
	-PySerial para la comunicación con el módem (sudo pip install pyserial)

##Requisitos de Configuración
	-Establecer en la lista de contactos (contactList.py) los contactos con los que se planea la comunicación, en los dispositivos que se tengan disponibles.
	-Determinar las configuraciones que deseen para el funcionamiento del módulo en el archivo de configuración (config.sjon). Los campos de las mismas se explican a continuación. Se debe tener en cuenta que para las opciones con Habilitación/Deshabilitación se determinan con 0 deshabilitar, 1 para habilitar.
	
	{
	# --------- CONFIGURACIÓN NETWORK ---------
	"COMMUNICATOR":
	{
		"NAME"					: "Datalogger_1", 	# Nombre del Communicador para identificarse
		"RECEPTION_FILTER"		: 1,				# (0/1) Habilitado: Filtra los mensajes que no sean de contactos registrados
		"TRANSMISSION_BUFFER" 	: 10,				# Máxima cantidad de elementos para el buffer de transmissión
		"RECEPTION_BUFFER" 		: 10,				# Máxima cantidad de elementos para el buffer de recepción
		"FILE_PRIORITY"			: 20,				# Prioridad fija para archivos simples
		"FILE_TIME_OUT"			: 300,				# Tiempo (en Segundos) para descarte de arcvhivo simple
		"MESSAGE_PRIORITY"		: 30,				# Prioridad fija para mensajes simples
		"MESSAGE_TIME_OUT"		: 400				# Tiempo (en Segundos) para descarte de mensaje simple
		},
	"NETWORK":
		{
		"LOCAL_ADDRESS" : "localhost", 	# (192.168.0.15) Dirección de Ip del Comunicador
		"SET_IP" 	: 1,				# (0/1) Habilitado: Configura la dirección IP de manera automática, en base a la interfaz que se tenga disponible
		"PROTOCOL"      : "UDP",		# (UDP/TCP) Determinar el Protocolo a utilizar
		"TCP_PORT"      : 5000,			# (1024 - 65635) Selección del puerto TCP para recepción de mensajes TCP
		"UDP_PORT"      : 5010,			# (1024 - 65635) Selección del puerto UDP para recepción de mensajes UDP. No puede ser el mismo que el puerto TCP
		"CLOSE_PORT"	: 1				# (0/1) Habilitado: Cierra los puertos TCP / UDP en caso de estar siendo ocupados por otro proceso
	 	},
	# ------- CONFIGURACIÓN BLUETOOTH -------
		# PROTOCOL
		# 0 ---> L2CAP
		# 1 ---> HCI
		# 2 ---> SCO
		# 3 ---> RFCOMM
	"BLUETOOTH":
		{
		"PROTOCOL"     : 3,			# (0/1/2/3) Determina el protocolo: 0 es L2CAP; 1 es HCI; 2 es SCO; 3 es RFCOMM
		"MAC"          : "00:24:7E:64:7B:4A",	# MAC del dispositivo Bluetooth, se puede averiguar con: 
		"SERVICE"      : "BLUETOOTH-Client01",  # 
		"UUID"         : "94f39d29-7d6d-437d-973b-fba39e49d4ee"  #
		},
	# ------- CONFIGURACIÓN EMAIL -------
	"EMAIL":
		{
		"NAME"        : "client01",			# Nombre del administrador de la cuenta de correo
		"ACCOUNT"     : "client01.datalogger@gmail.com",  # Nombre de la cuenta de correo electrónico, debe ser una cuenta de google
		"PASSWORD"    : "client01dl",		# Contraseña de la cuenta
		"SUBJECT"	  : "Comunicador Inteligente", # Asunto para los mails que se envian
		"SMTP_SERVER" : "smtp.gmail.com",	# Servidor de correo para envio (De cambiar este paramétro el módulo podría no funcionar)
		"IMAP_SERVER" : "imap.gmail.com",	# Servidor de correo para recepción (De cambiar este paramétro el módulo podría no funcionar)
		"SMTP_PORT"   : 587,				# Número de puerto para envio (De cambiar este paramétro el módulo podría no funcionar)
		"IMAP_PORT"   : 993					# Número de puerto para recepción (De cambiar este paramétro el módulo podría no funcionar)
		},
	# ------- CONFIGURACIÓN SMS -------
	"SMS":
		{
		"CLARO_MESSAGES_CENTER"  : 543200000001,  	# Centro de mensajes de claro, es para no rechazar esos mensajes
		"CLARO_TELEPHONE_NUMBER" : 3516178949,  	# N° de telefono del chip utilizado   
		"CLARO_WEB_PAGE"         : 876966,			# Página web de claro, es para no rechazar esos mensajes
		"CLARO_CHARACTER_LIMIT"  : 160 				# Limite de caracteres para mensajes de claro
		},
	# ------- NIVELES DE PRIORIDAD -------
		# 4 --> Alto
		# 3 --> Normal
		# 2 --> Bajo
		# 1 --> Muy bajo
		# 0 --> Inhabilidato
	"PRIORITY_LEVELS":
		{
		"NETWORK"   : 1,
		"SMS"       : 0,
		"EMAIL"     : 0,
		"BLUETOOTH" : 0
		},
	# ------- TIPOS DE NOTIFICACIONES -------
		# DEBUG    --> Depuración
		# INFO     --> Información
		# WARNING  --> Advertencia
		# ERROR    --> Error
		# CRITICAL --> Situación crítica
	"FILE_LOGGING_LEVEL"    : "DEBUG",		# Para el archivo log, por defecto se imprimen todas las notificaciones ('DEBUG')
	"CONSOLE_LOGGING_LEVEL" : "DEBUG"		# Para la consola,  por defecto se descartan los mesajes de depuración mostrando sólo lo más relevante ('INFO')
}

##Ejecución del Módulo
En su aplicación se debe tener importado el modulo "import communicator.py" (su programa debe estar en la misma carpeta del comunicador). En caso de usar el módem se requiere correr la aplicación como root. El uso del comunicador se basa en el llamado de las siguientes funciones:
###communicator.open()
	Se realiza la apertura, inicialización de los componentes que se tengan disponibles	.
###communicator.send()
	Se envia de modo inteligente un paquete de datos a un contacto previamente registrado el mensaje se envia por el medio mas óptimo encontrado. Se tienen 4 formas de envio
	Envio de mensaje simple: **communicator.send(mensajeComoCadena, contactoRegistrado, dispositivoPreferenteDeEnvio)**
		Este ultimo campo puede obviarse, es decir communicator.send(mensajeComoCadena, contactoRegistrado)
	Envio de instancia mensaje: **communicator.send(instanciaDeMensaje)**
		Puede ser una instancia de la clase definida Message (en messageClass.py) o una subclase de esta, requiere valores inciados.
	Envio de archivo simple: **communicator.send(nombreDeArchivo, contactoRegistrado, dispositivoPreferenteDeEnvio)**
		Este ultimo campo puede obviarse, es decir communicator.send(nombreDeArchivo, contactoRegistrado)
		Si el archivo no esta en la carpeta, se debe establecer tmb la ruta: nombreDeArchivo = ruta/nombreDeArchivo
	Envio de instancia archivo: **communicator.send(instanciaDeArchivo)**
		Puede ser una instancia de la clase definida FileMessage (en messageClass.py) o una subclase de esta, requiere valores inciados. 
		Con esta calse se cuenta con campos adicionales. FileName para el nombre del archivo y received que indica si la recepción fue exitosa. 
		El Comunicador se encarga de modificarlo, el usuario solo debe verificarlo.

	NT: La comunicación por isntancia de clases solo esta habilitada para NETWORK con TCP y UDP. Pero se añadirá para Email y Bluetooth.
###communicator.recieve()
	Se obtiene de un buffer circular el mensaje recibido mas antiguo, sea este instancia o texto (se debe hacer una comprobación puede ver el ejemplo en example.py)
###communicator.close()
	Se cierran los componentes del sistema, unicamente los abiertos previamente.
###communicator.lenght()
	Devuelve la cantidad de elementos recibidos que todavía no se han sacado del buffer.
###communicator.connectGPRS()
	Se realiza una conexión GPRS con el módem, pero se pierde la posibilidad del envio de mensajes, mientras este conectado GPRS.
###communicator.disconnectGPRS()
	Se termina la conexión GPRS.

Para mayor entenimiento del módulo se recomienda analizar el archivo de ejemplo "example.py".

##ISSUES
	-En caso de excpeción y el programa no finalize correctamente se debe eliminar un archivo temporal de manera manual: sudo rm /tmp/activeInterfaces 
	-No funciona el modo Bluetooth