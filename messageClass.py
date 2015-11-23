# coding=utf-8

class Message(object):

	sender = None	# Emisor del mensajes, la fuente
	receiver= None	# Receptor del mensajes, a quien esta destinado

	device = None	# Dispositivo por el que se prefiere el envío
	priority = None	# Prioridad del mensaje para envio (Valores posibles 0-99)

	isInstance = True

	def __init__(self, _sender, _receiver, _device):
		"""Se establecen los parametros esenciales que debe tener una Instancia de Mensaje
		del coomunicador.
		@param _receiver: Receptor del mensajes, a quien esta destinado
		@type: string
		@param _sender: Emisor del mensajes, la fuente
		@type: string
		@param _device: Dispositivo por el que se prefiere el envío
		@type: string"""
		self.device = _device
		self.sender = _sender
		self.receiver = _receiver

class SimpleMessage(Message):

	plainText = None

	def __init__(self, _sender, _receiver, _plainText, _device = None):
		Message.__init__(self, _sender, _receiver, _device)
		self.plainText = _plainText
		self.priority = 10

class FileMessage(Message):

	fileName = None	# Nombre del archivo a enviar o la ruta con el nombre si estuviera 
					# en otra carpeta /ruta/archivo.txt

	def __init__(self, _sender, _receiver, _fileName, _device = None):
		"""Se establecen los parametros esenciales que debe tener una Instancia de Archivo
		del coomunicador
		@param _receiver: Receptor del mensajes, a quien esta destinado
		@type: string
		@param _sender: Emisor del mensajes, la fuente
		@type: string
		@param _device: Dispositivo por el que se prefiere el envío
		@type: string
		@param _fileName:  Nombre del archivo a enviar o la ruta del archivo
		@type: string"""
		Message.__init__(self, _sender, _receiver, _device)
		self.fileName = _fileName
		self.priority = 10