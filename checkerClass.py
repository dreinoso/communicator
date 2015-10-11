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

	networkThreadName = 'networkReceptor'
	smsThreadName = 'smsReceptor'
	emailThreadName = 'emailReceptor'
	gprsThreadName = 'gprsVerifyConnection'
	bluetoothThreadName = 'bluetoothReceptor'

	availableNetwork = False       # Indica si el modo NETWORK está disponible
	availableSms = False       # Indica si el modo SMS está disponible
	availableEmail = False     # Indica si el modo EMAIL está disponible
	availableBluetooth = False # Indica si el modo BLUTOOTH está disponible

	threadNameList = [networkThreadName, smsThreadName, emailThreadName, gprsThreadName, bluetoothThreadName]

	isActive = False

	def __init__(self, _modemSemaphore, _networkInstance, _gprsInstance, _emailInstance, _smsInstance, _bluetoothInstance):
		self.modemSemaphore = _modemSemaphore
		self.networkInstance = _networkInstance
		self.smsInstance = _smsInstance
		self.gprsInstance = _gprsInstance
		self.emailInstance = _emailInstance
		self.bluetoothInstance = _bluetoothInstance

	def __del__(self):
		self.networkInstance.isActive = False
		self.smsInstance.isActive = False
		self.gprsInstance.isActive = False
		self.emailInstance.isActive = False
		self.bluetoothInstance.isActive = False
		# Esperamos que terminen los hilos receptores networkzados
		for receptorThread in threading.enumerate():
			if receptorThread.getName() in self.threadNameList and receptorThread.isAlive():
				receptorThread.join()
		logger.write('INFO', '[CHECKER] Objeto destruido.')

	def verifyConnections(self):
		while self.isActive:
			self.availableNetwork = self.verifyNetworkConnection()
			self.availableSms = self.verifySmsConnection()
			self.availableEmail = self.verifyEmailConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			time.sleep(TIME_REFRESH)
		logger.write('WARNING', '[CHECKER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def verifyNetworkConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Lan.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		interfacesPattern = re.compile('wlan[0-9]+' '|' 'eth[0-9]+') # Se buscan interfaces de 0 a 100
		networkInterfaces = os.popen('ip link show').readlines()
		patternMatched = None
		stateUP = False
		for interface in networkInterfaces:
			# Buscamos a lo largo de la cadena si hay alguna coincidencia de una RE
			patternMatched = interfacesPattern.search(interface)
			if patternMatched is not None and interface.find("state UP") > 0:
				activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
				stateUP = True
				# 'patternMatched.group()' devuelve la cadena (interfaz) que coincide con la RE
				if (patternMatched.group() + '\n') not in activeInterfacesFile.read():
					# Como la interfaz encontrada no está siendo usada, la ponemos a escuchar si no está activa
					if not self.networkInstance.isActive:
						# Escribimos en nuestro archivo la interfaz a usar, para indicar que está ocupada
						activeInterfacesFile.write(patternMatched.group() + '\n')
						self.networkInstance.connect(patternMatched.group())
						self.networkInstance.isActive = True
						activeInterfacesFile.close()
						networkThread = threading.Thread(target = self.networkInstance.receive, name = self.networkThreadName)
						networkThread.start()
						networkInfo = patternMatched.group() + ' - ' + self.networkInstance.localAddress
						logger.write('INFO','[NETWORK] Listo para usarse (' + networkInfo + ').')
						return True
				# Si la interfaz ya está en modo activo (funcionando), devolvemos True
				elif self.networkInstance.isActive:
					return True
		# Si ya no se encontró ninguna interfaz UP y ya estabamos escuchando, dejamos de hacerlo
		if stateUP is False and self.networkInstance.isActive:
			self.networkInstance.isActive = False
			# Eliminamos del archivo la interfaz usada en esta misma instancia
			activeInterfacesFile = open('/tmp/activeInterfaces').read()
			deletedActiveInterface = activeInterfacesFile.replace(self.networkInstance.localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(deletedActiveInterface)
			activeInterfacesFile.close()
			return False

	def verifySmsConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio comunicación SMS.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		ttyUSBPattern = re.compile('ttyUSB[0-9]+')
		lsDevProcess = subprocess.Popen(['ls', '/dev/'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		lsDevOutput, lsDevError = lsDevProcess.communicate()
		ttyUSBDevices = ttyUSBPattern.findall(lsDevOutput)
		# Se detectaron dispositivos USB conectados
		if len(ttyUSBDevices) > 0:
			if self.smsInstance.serialPort not in ttyUSBDevices:
				wvdialProcess = subprocess.Popen('wvdialconf', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
				wvdialOutput, wvdialError = wvdialProcess.communicate()
				ttyUSBPattern = re.compile('ttyUSB[0-9]+<Info>')
				modemsList = ttyUSBPattern.findall(wvdialError)
				# Se detectaron dispositivos USB que responden como módems
				if len(modemsList) > 0:
					gsmSerialPort = modemsList[1].replace('<Info>','')
					# Si no se produjo ningún error durante la configuración, ponemos al módem a recibir SMS
					if self.smsInstance.connect(gsmSerialPort):
						self.smsInstance.isActive = True
						smsThread = threading.Thread(target = self.smsInstance.receive, name = self.smsThreadName)
						smsThread.start()
						smsInfo = gsmSerialPort + ' - ' + str(self.smsInstance.telephoneNumber)
						logger.write('INFO','[SMS] Listo para usarse (' + smsInfo + ').')
						return True
					else:
						self.smsInstance.closePort()
						return False
			# Si el módem ya está en modo activo (funcionando), devolvemos 'True'
			elif self.smsInstance.isActive:
				return True
		else:
			if self.smsInstance.isActive:
				self.smsInstance.closePort()
				self.smsInstance.isActive = False
				self.smsInstance.serialPort = None
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
				time.sleep(3.0)
				self.emailInstance.connect()
				self.emailInstance.isActive = True
				emailThread = threading.Thread(target = self.emailInstance.receive, name = self.emailThreadName)
				emailThread.start()
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
		# Ejemplo de bluetoothDevices: ['Devices:\n', '\thci0\t00:24:7E:64:7B:4A\n']
		bluetoothDevices = os.popen('hcitool dev').readlines()
		# Sacamos el primer elemento por izquierda ('Devices:\n')
		bluetoothDevices.pop(0)
		if len(bluetoothDevices) > 0:
			if not self.bluetoothInstance.isActive:
				self.bluetoothInstance.connect()
				self.bluetoothInstance.isActive = True
				bluetoothThread = threading.Thread(target = self.bluetoothInstance.receive, name = self.bluetoothThreadName)
				bluetoothThread.start()
				logger.write('INFO','[BLUETOOTH] Listo para usarse.')
			return True
		else:
			if self.bluetoothInstance.isActive:
				self.bluetoothInstance.isActive = False
			return False
