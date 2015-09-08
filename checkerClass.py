 # coding=utf-8
"""	Este objeto se ocupa de testar las conexiones disponibles en el sistema
	para que el comunicador haga uso de estas.

	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - FCEFYN
	@date: Lunes 16 de Junio de 2015 """

import os
import re
import time
import socket
import inspect
import threading
import subprocess

import logger

TIME_REFRESH = 5

class Checker(object):

	lanThreadName = 'lanReceptor'
	smsThreadName = 'smsReceptor'
	emailThreadName = 'emailReceptor'
	bluetoothThreadName = 'bluetoothReceptor'

	threadNameList = [lanThreadName, smsThreadName, emailThreadName, bluetoothThreadName]

	availableLan = False       # Indica si el modo LAN está disponible
	availableSms = False       # Indica si el modo SMS está disponible
	availableEmail = False     # Indica si el modo EMAIL está disponible
	availableBluetooth = False # Indica si el modo BLUTOOTH está disponible

	isActive = False

	def __init__(self, _modemSemaphore, _lanInstance, _smsInstance, _bluetoothInstance, _emailInstance):
		self.modemSemaphore = _modemSemaphore
		self.lanInstance = _lanInstance
		self.smsInstance = _smsInstance
		self.emailInstance = _emailInstance
		self.bluetoothInstance = _bluetoothInstance
		# Establecemos las funciones que van a manejar las distintas instancias de recepción
		self.lanThread = threading.Thread(target = self.lanInstance.receive, name = self.lanThreadName)
		self.smsThread = threading.Thread(target = self.smsInstance.receive, name = self.smsThreadName)
		self.emailThread = threading.Thread(target = self.emailInstance.receive, name = self.emailThreadName)
		self.bluetoothThread = threading.Thread(target = self.bluetoothInstance.receive, name = self.bluetoothThreadName)

	def __del__(self):
		self.lanInstance.isActive = False
		self.smsInstance.isActive = False
		self.emailInstance.isActive = False
		self.bluetoothInstance.isActive = False
		# Esperamos que terminen los hilos receptores lanzados
		for receptorThread in threading.enumerate():
			if receptorThread.getName() in self.threadNameList and receptorThread.isAlive():
				receptorThread.join()
		logger.write('INFO', '[CHECKER] Objeto destruido.')

	def verifyConnections(self):
		while self.isActive:
			self.availableLan = self.verifyLanConnection()
			self.availableSms = self.verifySmsConnection()
			self.availableEmail = self.verifyEmailConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			time.sleep(TIME_REFRESH)
		logger.write('WARNING', '[CHECKER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def verifyLanConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Lan.
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
			if not self.lanInstance.isActive and not self.lanInstance.bindFailed:
				self.lanInstance.connect()
				self.lanInstance.isActive = True
				self.lanThread.start()
				logger.write('INFO','[LAN] Listo para usarse.')
			return True
		else:
			if self.lanInstance.isActive:
				self.lanInstance.isActive = False
			return False

	def verifySmsConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio comunicación SMS.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		self.modemSemaphore.acquire() # Para evitar que 'modemClass' use al mismo tiempo el dispositivo
		ttyUSBPattern = re.compile('ttyUSB[0-9]+')
		wvdialProcess = subprocess.Popen('wvdialconf', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		wvdialOutput, wvdialError = wvdialProcess.communicate()
		modemsList = ttyUSBPattern.findall(wvdialOutput)
		self.modemSemaphore.release() # Libera el modem
		if len(modemsList) > 0:
			if not self.smsInstance.isActive:
				self.smsInstance.connect('/dev/' + modemsList[0])
				self.smsInstance.isActive = True
				self.smsThread.start()
				logger.write('INFO','[SMS] Listo para usarse.')
			return True
		else:
			if self.smsInstance.isActive:
				self.smsInstance.isActive = False
			return False

	def verifyEmailConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación 
		a través Email.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		TEST_REMOTE_SERVER = 'www.google.com'
		try:
			remoteHost = socket.gethostbyname(TEST_REMOTE_SERVER)
			testSocket = socket.create_connection((remoteHost, 80), 2) # Se determina si es alcanzable
			if not self.emailInstance.isActive:
				self.emailInstance.connect()
				self.emailInstance.isActive = True
				self.emailThread.start()
				logger.write('INFO', '[EMAIL] Listo para usarse.')
			return True
		except:
			if self.emailInstance.isActive:
				self.emailInstance.isActive = False
			return False

	def verifyBluetoothConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Bluetooth.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		bluetoothDevices = os.popen('hcitool dev').readlines()
		bluetoothDevices.pop(0)
		if len(bluetoothDevices) > 0:
			if not self.bluetoothInstance.isActive:
				self.bluetoothInstance.connect()
				self.bluetoothInstance.isActive = True
				self.bluetoothThread.start()
				logger.write('INFO','[BLUETOOTH] Listo para usarse.')
			return True
		else:
			if self.bluetoothInstance.isActive:
				self.bluetoothInstance.isActive = False
			return False
