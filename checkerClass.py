 # coding=utf-8
"""	Este objeto se ocupa de testar las conexiones disponibles en el sistema
	para que el comunicador haga uso de estas.

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Abril de 2015 """

import os
import re
import time
import socket
import inspect
import threading

class Checker(object):

	killChecker = False
	availableSms = False			#Establece si el modo SMS esta disponible
	availableEmail = False		#Establece si el modo EMAIL esta disponible
	availableEthernet = False    #Establece si el modo ETHERNET esta disponible
	availableBluetooth = False	#Establece si el modo BLUTOOTH esta disponible

	def __init__(self, _ethernetInstance, _bluetoothInstance, _emailInstance):
		self.ethernetInstance = _ethernetInstance
		self.bluetoothInstance = _bluetoothInstance
		self.emailInstance = _emailInstance

	def __del__(self):
		print 'Objeto ' + self.__class__.__name__ + ' destruido.'
	
	def verifyEthernetConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio del objeto Ethernet.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		ethernetDevices = os.popen('ip link show').readlines()
		wlanActiveInterfaces = 0
		ethActiveInterfaces = 0
		wlanPattern = re.compile('wlan[0-9]+') #Se buscan interfaces de 0 a 100
		ethPattern = re.compile('eth[0-9]+')
		statePattern = re.compile('state UP')
		for interface in ethernetDevices:
			if wlanPattern.search(interface) != None and statePattern.search(interface) != None:
				wlanActiveInterfaces = wlanActiveInterfaces + 1
			if ethPattern.search(interface) != None and statePattern.search(interface) != None:
				ethActiveInterfaces = ethActiveInterfaces + 1
		#print '[MODO ETHERNET] ' + str(ethActiveInterfaces) + ' interfaz/es Ethernet activa/s y ' + str(wlanActiveInterfaces) + ' interfaz/es WLan activa/s.'
		if ethActiveInterfaces + wlanActiveInterfaces > 0:
			if not self.ethernetInstance.isActive:
				self.ethernetInstance.isActive = True
				ethernetThread = threading.Thread(target = self.ethernetInstance.receivePacket, name = 'ethernetReceptor')
				ethernetThread.start()
				print '[ETHERNET] Listo para usarse.'
			return True
		else:
			if self.ethernetInstance.isActive:
				self.ethernetInstance.isActive = False
			return False

	def verifyBluetoothConnection(self):
		bluetoothDevices = os.popen('hcitool dev').readlines()
		bluetoothDevices.pop(0)
		if len(bluetoothDevices) > 0:
			if not self.bluetoothInstance.isActive:
				self.bluetoothInstance.isActive = True
				bluetoothThread = threading.Thread(target = self.bluetoothInstance.receivePacket, name = 'bluetoothReceptor')
				bluetoothThread.start()
				print '[BLUETOOTH] Listo para usarse.'
			return True
		else:
			if self.bluetoothInstance.isActive:
				self.bluetoothInstance.isActive = False
			return False

	def verifyEmailConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio del objeto Email.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		REMOTE_SERVER = "www.google.com"
		try:
			host = socket.gethostbyname(REMOTE_SERVER) # Obtiene el DNS
			s = socket.create_connection((host, 80), 2) # Se determina si es alcanzable
			if not self.emailInstance.isActive:
				self.emailInstance.connect()
				self.emailInstance.isActive = True
				self.emailThread = threading.Thread(target = self.emailInstance.receivePacket, name = 'emailReceptor')
				self.emailThread.start()
				print '[EMAIL] Listo para usarse.'
			return True
		except:
			#print '[MODO EMAIL] No se pudo iniciar el sistema, establezca una conexión a internet para solucionarlo.'
			if self.emailInstance.isActive:
				self.emailInstance.isActive = False
			return False

	def verifySmsConnection(self):
		return False

	def verifyConnections(self):
		while not self.killChecker:
			self.availableEthernet = self.verifyEthernetConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			self.availableEmail = self.verifyEmailConnection()
			time.sleep(3)
		self.bluetoothInstance.isActive = False
		self.emailInstance.isActive = False
		self.ethernetInstance.isActive = False
		print '[CHECKER] Funcion \'%s\' terminada.' % inspect.stack()[0][3]
