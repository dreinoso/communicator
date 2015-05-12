# coding=utf-8
"""	Este objeto se ocupa de leer las configuraciones establecidas para
	el sistema, para determinar el comportamiento del mismo

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Abril de 2015 """

class ConfigReader(object):
	warningsOn = True			#Establece si se deben mostrar advertencias
	notificationOn = True		#Establece si se deben mostrar notificaciones

	def __init__(self):
		self.readConfigFile()

	def __del__(self):
		pass
	
	def readConfigFile(self):
		pass