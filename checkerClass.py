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
import subprocess

class Checker(object):

	killChecker = False
	availableSms = False			#Establece si el modo SMS esta disponible
	availableEmail = False		#Establece si el modo EMAIL esta disponible
	availableEthernet = False    #Establece si el modo ETHERNET esta disponible
	availableBluetooth = False	#Establece si el modo BLUTOOTH esta disponible

	def __init__(self, _smsInstance, _ethernetInstance, _bluetoothInstance, _emailInstance):
		self.smsInstance = _smsInstance
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
		wlanActiveInterfaces = False
		ethActiveInterfaces = False
		wlanPattern = re.compile('wlan[0-9]+') #Se buscan interfaces de 0 a 100
		ethPattern = re.compile('eth[0-9]+')
		statePattern = re.compile('state UP')
		for interface in ethernetDevices:
			if wlanPattern.search(interface) and statePattern.search(interface):
				wlanActiveInterfaces = True
				break
			elif ethPattern.search(interface) and statePattern.search(interface):
				ethActiveInterfaces = True
				break
		if ethActiveInterfaces or wlanActiveInterfaces:
			if not self.ethernetInstance.isActive:
				self.ethernetInstance.connect()
				self.ethernetInstance.isActive = True
				ethernetThread = threading.Thread(target = self.ethernetInstance.receive, name = 'ethernetReceptor')
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
				bluetoothThread = threading.Thread(target = self.bluetoothInstance.receive, name = 'bluetoothReceptor')
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
		TEST_REMOTE_SERVER = 'www.google.com'
		try:
			remoteHost = socket.gethostbyname(TEST_REMOTE_SERVER)
			testSocket = socket.create_connection((remoteHost, 80), 2) # Se determina si es alcanzable
			if not self.emailInstance.isActive:
				self.emailInstance.connect()
				self.emailInstance.isActive = True
				self.emailThread = threading.Thread(target = self.emailInstance.receive, name = 'emailReceptor')
				self.emailThread.start()
				print '[EMAIL] Listo para usarse.'
			return True
		except:
			if self.emailInstance.isActive:
				self.emailInstance.isActive = False
			return False

	def verifySmsConnection(self):
		ttyUSBPattern = re.compile('ttyUSB[0-9]+')
		wvdialProcess = subprocess.Popen('wvdialconf', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		wvdialOutput, wvdialError = wvdialProcess.communicate()
		modemsList = ttyUSBPattern.findall(wvdialOutput)
		if len(modemsList) > 0:
			if not self.smsInstance.isActive:
				self.smsInstance.connect('/dev/' + modemsList[0])
				self.smsInstance.isActive = True
				self.smsThread = threading.Thread(target = self.smsInstance.receive, name = 'smsReceptor')
				self.smsThread.start()
				print '[SMS] Listo para usarse.'
			return True
		else:
			if self.smsInstance.isActive:
				self.smsInstance.isActive = False
			return False

	def verifyConnections(self):
		while not self.killChecker:
			self.availableSms = self.verifySmsConnection()
			self.availableEthernet = self.verifyEthernetConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			self.availableEmail = self.verifyEmailConnection()
			time.sleep(3)
		self.smsInstance.isActive = False
		self.bluetoothInstance.isActive = False
		self.emailInstance.isActive = False
		self.ethernetInstance.isActive = False
		print '[CHECKER] Funcion \'%s\' terminada.' % inspect.stack()[0][3]
