 # coding=utf-8
"""	Este objeto se ocupa de testar las conexiones disponibles en el sistema
	para que el comunicador haga uso de estas.

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Abril de 2015 """

import os
import time
import socket
import threading

class Checker(object):

	killChecker = False
	availableSms = False			#Establece si el modo SMS esta disponible
	availableEmail = False		#Establece si el modo EMAIL esta disponible
	availableEthernet = False    #Establece si el modo ETHERNET esta disponible
	availableBluetooth = False	#Establece si el modo BLUTOOTH esta disponible

	def __init__(self, bluetoothInstance):
		self.bluetoothInstance = bluetoothInstance

	def __del__(self):
		print 'Objeto ' + self.__class__.__name__ + ' destruido.'
	
	def verifySmsConnection(self):
		return False

	def verifyEmailConnection(self):
		return False

		REMOTE_SERVER = "www.google.com"
		try:
			host = socket.gethostbyname(REMOTE_SERVER) # Obtiene el DNS
			s = socket.create_connection((host, 80), 2) # Se determina si es alcanzable
			return True
		except:
			print '[MODO EMAIL] No se pudo iniciar el sistema, establezca una conexión a internet para solucionarlo.'
		return False

	def verifyEthernetConnection(self):
		return False

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
		bluetoothDevices = os.popen('hcitool dev').readlines()
		bluetoothDevices.pop(0)
		if len(bluetoothDevices) > 0:
			if not self.bluetoothInstance.isActive:
				self.bluetoothInstance.isActive = True
				self.availableBluetooth = True
				bluetoothThread = threading.Thread(target = self.bluetoothInstance.receivePacket, name = 'bluetoothReceptor')
				bluetoothThread.start()
				print '[BLUETOOTH] Listo para usarse.'
		else:
			if self.bluetoothInstance.isActive:
				self.availableBluetooth = False
				self.bluetoothInstance.isActive = False
				self.bluetoothInstance.killBluetooth = True

	def verifyConnections(self):
		while not self.killChecker:
			self.verifyBluetoothConnection()
			time.sleep(3)
		self.bluetoothInstance.killBluetooth = True
