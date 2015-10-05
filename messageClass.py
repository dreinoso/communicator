# coding=utf-8

class Message(object):

	receiver= ''	# Receptor del mensajes, a quien esta destinado
	sender = ''		# Emisor del mensajes, la fuente
	priority = 1	# Prioridad del mensaje para envio (Valores posibles 0-99)
	timeOut = 0 	# Tiempo en segundos, despues del cual el mensaje es descartado
	device = ''		# Dispositivo por el que se prefiere el envío

	def __init__(self, _receiver, _sender, _priority, _timeOut, _device):
		"""Se establecen los parametros esenciales que debe tener una instancia de mensaje
		del coomunicador
		@type: list"""
		self.receiver = _receiver
		self.sender = _sender
		self.priority = _priority
		self.timeOut = _timeOut
		self.device = _device

class FileMessage (Message):

	fileName = ''	# Nombre del archivo a enviar o la ruta con el nombre si estuviera 
					# en otra carpeta /ruta/archivo.txt

	def __init__(self, _receiver, _sender, _priority, _timeOut, _device, _fileName):
		"""Se establecen los parametros esenciales que debe tener una instancia de mensaje
		del coomunicador
		@type: list"""
		self.receiver = _receiver
		self.sender = _sender
		self.priority = _priority
		self.timeOut = _timeOut
		self.device = _device
		self.fileName = _fileName
