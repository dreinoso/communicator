# coding=utf-8

class Message(object):

	sender = None	# Emisor del mensajes, la fuente
	receiver= None	# Receptor del mensajes, a quien esta destinado
	priority = None	# Prioridad del mensaje para envio (valores posibles 0-99)

	def __init__(self, _sender, _receiver):
		"""Se establecen los parametros esenciales que debe tener una Instancia de Mensaje
		del coomunicador.
		@param _receiver: Receptor del mensajes, a quien esta destinado
		@type: string
		@param _sender: Emisor del mensajes, la fuente
		@type: string"""
		self.sender = _sender
		self.receiver = _receiver

class SimpleMessage(Message):

	plainText = None

	def __init__(self, _sender, _receiver, _plainText):
		Message.__init__(self, _sender, _receiver)
		self.plainText = _plainText
		self.priority = 10

class FileMessage(Message):

	fileName = None	# Nombre del archivo a enviar o la ruta con el nombre si estuviera 
					# en otra carpeta /ruta/archivo.txt

	def __init__(self, _sender, _receiver, _fileName):
		"""Se establecen los parametros esenciales que debe tener una Instancia de Archivo
		del coomunicador
		@param _receiver: Receptor del mensajes, a quien esta destinado
		@type: string
		@param _sender: Emisor del mensajes, la fuente
		@type: string
		@param _fileName:  Nombre del archivo a enviar o la ruta del archivo
		@type: string"""
		Message.__init__(self, _sender, _receiver)
		self.fileName = _fileName
		self.priority = 10