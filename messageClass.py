# coding=utf-8

class Message(object):

	receiver= ''	# Receptor del mensajes, a quien esta destinado
	sender = ''		# Emisor del mensajes, la fuente
	priority = 1	# Prioridad del mensaje para envio (Valores posibles 0-99)
	timeOut = 0 	# Tiempo en segundos, despues del cual el mensaje es descartado
	device = ''		# Dispositivo por el que se prefiere el envío

	def __init__(self, _receiver, _sender, _priority, _timeOut, _device):
		"""Se establecen los parametros esenciales que debe tener una Instancia de Mensaje
		del coomunicador.
		@param _receiver: Receptor del mensajes, a quien esta destinado
		@type: string
		@param _sender: Emisor del mensajes, la fuente
		@type: string
		@param _priority: Prioridad del mensaje para envio (Valores posibles 0-99)
		@type: int
		@param _timeOut: Tiempo en segundos, despues del cual el mensaje es descartado
		@type: int
		@param _device: Dispositivo por el que se prefiere el envío
		@type: string"""		
		self.receiver = _receiver
		self.sender = _sender
		self.priority = _priority
		self.timeOut = _timeOut
		self.device = _device

class FileMessage (Message):

	fileName = ''	# Nombre del archivo a enviar o la ruta con el nombre si estuviera 
					# en otra carpeta /ruta/archivo.txt
	received = False # Este campo indica si la recepción del archivo fue exitosa

	def __init__(self, _receiver, _sender, _priority, _timeOut, _device, _fileName):
		"""Se establecen los parametros esenciales que debe tener una Instancia de Archivo
		del coomunicador
		@param _receiver: Receptor del mensajes, a quien esta destinado
		@type: string
		@param _sender: Emisor del mensajes, la fuente
		@type: string
		@param _priority: Prioridad del mensaje para envio (Valores posibles 0-99)
		@type: int
		@param _timeOut: Tiempo en segundos, despues del cual el mensaje es descartado
		@type: int
		@param _device: Dispositivo por el que se prefiere el envío
		@type: string
		@param _fileName:  Nombre del archivo a enviar o la ruta del archivo
		@type: string"""
		self.receiver = _receiver
		self.sender = _sender
		self.priority = _priority
		self.timeOut = _timeOut
		self.device = _device
		self.fileName = _fileName
