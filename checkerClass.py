 # coding=utf-8
"""	Este objeto se ocupa de testar las conexiones disponibles en el sistema
	para que el comunicador haga uso de estas.

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Abril de 2015 """

import socket
import os
import re

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
		"""Se determina la disponibilidad de la comunicación por medio del objeto Email.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
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
		"""Se determina la disponibilidad de la comunicación por medio del objeto Ethernet.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		ethernetDevices = os.popen('ip link show').readlines()
		wlanActiveInterfaces = 0
		ethActiveInterfaces = 0
		for interface in ethernetDevices:
			wlanPatron = re.compile('wlan[0-100]+')
			ethPatron = re.compile('eth[0-100]+')
			statePatron = re.compile('state UP')
			if wlanPatron.search(interface) != None and statePatron.search(interface) != None:
				wlanActiveInterfaces = wlanActiveInterfaces + 1
			if ethPatron.search(interface) != None and statePatron.search(interface) != None:
				ethActiveInterfaces = ethActiveInterfaces + 1
		print '[MODO ETHERNET] ' + str(ethActiveInterfaces) + ' interfaz/es Ethernet activa/s y ' + str(wlanActiveInterfaces) + ' interfaz/es WLan activa/s.'
		if ethActiveInterfaces + wlanActiveInterfaces > 0:
			return True
		return False

	def verifyBluetoothConnection(self):
		return False