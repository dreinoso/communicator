# coding=utf-8
import messageClass

class ExampleMessage(messageClass.Message):

	atribute1 = 0 
	atribute2 = ''

	def __init__(self, _receiver, _sender, _priority, _timeOut, _device):
		"""Se establecen los parametros esenciales que debe tener una instancia de mensaje
		del coomunicador
		@type: list"""
		self.receiver = _receiver  	# Receptor del mensajes, a quien esta destinado
		self.sender = _sender 		# Emisor del mensajes, la fuente
		self.priority = _priority	# Prioridad del mensaje para envio (Valores posibles 0-99)
		self.timeOut = _timeOut		# Tiempo en segundos, despues del cual el mensaje es descartado
		self.device = _device		#

	def setAtribute1(self, _atribute1):
		self.atribute1 = _atribute1

	def setAtribute2(self, _atribute2):
		self.atribute2 = _atribute2

class ExampleFile(messageClass.FileMessage):

	atribute1 = 0 
	atribute2 = ''

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

	def setAtribute1(self, _atribute1):
		self.atribute1 = _atribute1

	def setAtribute2(self, _atribute2):
		self.atribute2 = _atribute2