#Módulo de Comunicación Inteligente

Corresponde a un módulo de comunicación inteligente para comunicación punto a punto. Las comunicaciones que se pretenden son:
SMS, GPRS, EMAIL, TCP/IP y BLUETOOTH.

##Requisitos del módulo

	- Python 2.7

	- Pip para la instalación de los módulos (sudo apt-get install pip)
	  En caso de problemas de dependencias con pip (sudo apt-get install python python-dev libatlas-base-dev gcc gfortran g++)

	- PyBluez para la ejecución con Bluetooth (sudo pip install pybluez)
	  En caso de problemas de dependencias con pip (sudo apt-get install libbluetooth-dev)

	- PySerial para la comunicación con el módem (sudo pip install pyserial)

##Requisitos de Configuración

	- Establecer en la lista de contactos (contactList.py) los contactos con los que se planea la comunicación, en los dispositivos
	  que se tengan disponibles.

	- Determinar las configuraciones que deseen para el funcionamiento del módulo en el archivo de configuración (config.json).
	  Los campos de las mismas se explican a continuación. Se debe tener en cuenta que para las opciones con Habilitación/Deshabilitación
	  se determinan con 0 deshabilitar, 1 para habilitar.
	
	{
	# --------- CONFIGURACIÓN COMMUNICATOR ---------
	"COMMUNICATOR":
	{
		"NAME"                : "Datalogger_1", # Nombre del Comunicador para identificarse
		"RECEPTION_FILTER"    : 0,              # (0/1) Habilitado: Filtra los mensajes que no sean de contactos registrados
		"TRANSMISSION_BUFFER" : 10,             # Máxima cantidad de elementos para el buffer de transmissión
		"RECEPTION_BUFFER"    : 10,             # Máxima cantidad de elementos para el buffer de recepción
		"RETRY_TIME"          : 5,              # Tiempo (en segundos) entre reintentos
		"REFRESH_TIME"        : 5               # Tiempo (en segundos) para verificar conexiones
		},
	# --------- CONFIGURACIÓN NETWORK ---------
	"NETWORK":
		{
		"PROTOCOL" : "TCP", # (TCP/UDP) Determinar el Protocolo a utilizar
		"TCP_PORT" : 5000,  # (1024 - 65635) Selección del puerto TCP para recepción de mensajes TCP
		"UDP_PORT" : 5010   # (1024 - 65635) Selección del puerto UDP para recepción de mensajes UDP.
	 	},
	# ------- CONFIGURACIÓN BLUETOOTH -------
		# PROTOCOL
		# 0 ---> L2CAP
		# 1 ---> HCI
		# 2 ---> SCO
		# 3 ---> RFCOMM
	"BLUETOOTH":
		{
		"PROTOCOL" : 3,                                     # (0/1/2/3) Determina el protocolo: 0-L2CAP; 1-HCI; 2-SCO; 3-RFCOMM
		"SERVICE"  : "BLUETOOTH-Client01",                  # Nombre del servicio Bluetooth con el que vamos a aparecer
		"UUID"     : "94f39d29-7d6d-437d-973b-fba39e49d4ee" # ID para el servicio (debe ser único)
		},
	# ------- CONFIGURACIÓN EMAIL -------
	"EMAIL":
		{
		"ACCOUNT"     : "client01.datalogger@gmail.com", # Cuenta de GMAIL
		"PASSWORD"    : "client01dl",                    # Contraseña de la cuenta
		"SUBJECT"     : "Comunicador Inteligente",       # Asunto para los mails que se envian
		"SMTP_SERVER" : "smtp.gmail.com",                # Servidor SMTP para envío de mensajes
		"IMAP_SERVER" : "imap.gmail.com",                # Servidor IMAP para recepción de mensajes
		"SMTP_PORT"   : 587,                             # Puerto del servidor SMTP
		"IMAP_PORT"   : 993                              # Puerto del servidor IMAP
		},
	# ------- CONFIGURACIÓN SMS -------
	"SMS":
		{
		"TIME_OUT"  : 1.5,  # Tiempo de respuesta ante una petición al módem
		"BAUD_RATE" : 19200 # Velocidad en baudios
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
	"FILE_LOGGING_LEVEL"    : "DEBUG", # Para el archivo log, por defecto se imprimen todas las notificaciones ('DEBUG')
	"CONSOLE_LOGGING_LEVEL" : "DEBUG"  # Para la consola,  por defecto se descartan los mesajes de depuración mostrando sólo lo más relevante ('INFO')
}

##Ejecución del Módulo

En su aplicación se debe tener importado el modulo "import communicator.py" (su programa debe estar en la misma carpeta del comunicador).
En caso de usar el módem se requiere correr la aplicación como root. 

Si se ejecuta la aplicación en una carpeta superior al Communicator se deben añadir las siguientes lineas para que se encuentre el módulo
de no estar añadido en las carpetas de librerias de Python:

	import sys
	sys.path.append(os.path.abspath('Communicator/'))

El uso del comunicador se basa en el llamado de las siguientes funciones:

###communicator.open()

	Se realiza la apertura, inicialización de los componentes que se tengan disponibles.

###communicator.send()

	Se envia de modo inteligente un paquete de datos a un contacto previamente registrado.
	El mensaje se envia por el medio mas óptimo encontrado.

	Envio de textoPlano/archivo: **communicator.send(textoPlano/filePath, contactoRegistrado, dispositivoPreferidoDeEnvio)**
		Este último campo puede obviarse y el comunicador será el que decida por donde deberá transmitir, es decir, communicator.send(mensajeComoCadena, contactoRegistrado)

	Envio de instancia mensaje: **communicator.send(instanciaDeMensaje, device = dispositivoPreferidoDeEnvio)**
		Deberia ser una instancia de la clase definida como Message (en messageClass.py). El último campo también puede obviarse y el comunicador será el que decida por donde
		deberá transmitir, es decir, communicator.send(instanciaDeMensaje)

###communicator.recieve()

	Se obtiene de un buffer el mensaje con mayor prioridad, sea este instancia o texto.

###communicator.close()

	Se cierran los periféricos del sistema, únicamente los abiertos previamente.

###communicator.lenght()

	Devuelve la cantidad de elementos recibidos que todavía no se han sacado del buffer.

###communicator.connectGPRS()

	Se realiza una conexión GPRS con el módem, pero se pierde la posibilidad del envio de mensajes, mientras este conectado GPRS.

###communicator.disconnectGPRS()

	Se termina la conexión GPRS.

Para mayor entenimiento del módulo se recomienda analizar el archivo de ejemplo "example.py".

##ISSUES

	- En caso de excpeción y el programa no finalize correctamente se debe eliminar un archivo temporal de manera manual:
		sudo rm /tmp/activeInterfaces 
