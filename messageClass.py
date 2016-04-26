# coding=utf-8

class Message(object):

	sender = None	# Emisor del mensaje, la fuente
	receiver= None	# Receptor del mensaje, a quien esta destinado
	priority = None	# Prioridad del mensaje para envio

	def __init__(self, _sender, _receiver, _priority):
		self.sender = _sender
		self.receiver = _receiver
		self.priority = _priority

class InfoMessage(Message):

	infoText = None # Información a transmitir

	def __init__(self, _sender, _receiver, _infoText):
		Message.__init__(self, _sender, _receiver, 10)
		self.infoText = _infoText

class ConfigMessage(Message):

	startService = None # Servicio a iniciar
	stopService = None  # Servicio a detener

	def __init__(self, _sender, _receiver, _startService, _stopService):
		Message.__init__(self, _sender, _receiver, 5)
		self.startService = _startService
		self.stopService = _stopService