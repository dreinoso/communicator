# coding=utf-8

class Message(object):

	sender = None	# Emisor del mensaje, la fuente
	receiver= None	# Receptor del mensaje, a quien esta destinado
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

class InfoMessage(Message):

	infoText = None

	def __init__(self, _sender, _receiver, _infoText):
		Message.__init__(self, _sender, _receiver)
		self.infoText = _infoText
		self.priority = 10