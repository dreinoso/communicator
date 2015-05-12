 # coding=utf-8
"""	Este objeto se ocupa de testar las conexiones disponibles en el sistema
	para que el comunicador haga uso de estas.

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Abril de 2015 """

import socket

class Checker(object):

	smsAvailability = False			#Establece si el modo SMS esta disponible
	emailAvailability = False		#Establece si el modo EMAIL esta disponible
	ethernetAvailability = False    #Establece si el modo ETHERNET esta disponible
	bluetoothAvaliability = False	#Establece si el modo BLUTOOTH esta disponible

	def __init__(self):
		self.smsAvailability = self.verifySmsConnection()
		self.emailAvailability = self.verifyEmailConnection()
		self.ethernetAvailability = self.verifyEthernetConnection()
		self.bluetoothAvaliability = self.verifyBluetoothConnection()

	def __del__(self):
		pass
	
	def verifySmsConnection(self):
		return False

	def verifyEmailConnection(self):
		REMOTE_SERVER = "www.google.com"
		try:
			host = socket.gethostbyname(REMOTE_SERVER) # Obtiene el DNS
			s = socket.create_connection((host, 80), 2) # Se determina si es alcanzable
			return True
		except:
			print '[MODO EMAIL] No se pudo iniciar el sistema, establezca una conexión a internet para solucionarlo.'
		return False

	def verifyEthernetConnection(self):
		try: 
			s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			s.connect(("gmail.com",80))
			ipList =  s.getsockname() 
			if ipList[0] != None:
				#print ipList[0] #Muestra la dirección IP del programa.
				return True
				
		except Exception as e:
			print '[MODO ETHERNET] No se pudo iniciar este modo, establezca conexión a una LAN para solucionarlo.'	
		return False

	def verifyBluetoothConnection(self):
		return False