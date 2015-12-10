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

class Checker(threading.Thread):

	smsThreadName = 'smsReceptor'
	emailThreadName = 'emailReceptor'
	networkThreadName = 'networkReceptor'
	gprsThreadName = 'gprsVerifyConnection'
	bluetoothThreadName = 'bluetoothReceptor'

	availableSms = False       # Indica si el modo SMS está disponible
	availableEmail = False     # Indica si el modo EMAIL está disponible
	availableNetwork = False   # Indica si el modo NETWORK está disponible
	availableBluetooth = False # Indica si el modo BLUTOOTH está disponible

	threadNameList = [networkThreadName, smsThreadName, emailThreadName, gprsThreadName, bluetoothThreadName]

	isActive = False

	def __init__(self, _modemSemaphore, _networkInstance, _gprsInstance, _emailInstance, _smsInstance, _bluetoothInstance):
		threading.Thread.__init__(self, name = 'CheckerThread')
		self.modemSemaphore = _modemSemaphore
		self.smsInstance = _smsInstance
		self.gprsInstance = _gprsInstance
		self.emailInstance = _emailInstance
		self.networkInstance = _networkInstance
		self.bluetoothInstance = _bluetoothInstance

	def __del__(self):
		self.smsInstance.isActive = False
		self.gprsInstance.isActive = False
		self.emailInstance.isActive = False
		self.networkInstance.isActive = False
		self.bluetoothInstance.isActive = False
		# Esperamos que terminen los hilos receptores networkzados
		for receptorThread in threading.enumerate():
			if receptorThread.getName() in self.threadNameList and receptorThread.isAlive():
				receptorThread.join()
		logger.write('INFO', '[CHECKER] Objeto destruido.')

	def run(self):
		self.isActive = True
		while self.isActive:
			self.availableSms = self.verifySmsConnection()
			self.availableEmail = self.verifyEmailConnection()
			self.availableNetwork = self.verifyNetworkConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			time.sleep(TIME_REFRESH)
		logger.write('WARNING', '[CHECKER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

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
						smsThread = threading.Thread(target = self.smsInstance.receive, name = self.smsThreadName)
						smsThread.start()
						logger.write('INFO', '[SMS] Listo para usarse (' + gsmSerialPort + ').')
						return True
					else:
						self.smsInstance.closePort()
						return False
			# Si el módem ya está en modo activo (funcionando), devolvemos 'True'
			elif self.smsInstance.isActive:
				return True
			# Llegamos acá si se produjo un error en el 'connect' del módem (y todavía está conectado)
			else:
				return False
		else:
			if self.smsInstance.isActive:
				self.smsInstance.closePort()
				self.smsInstance.isActive = False
			self.smsInstance.serialPort = None
			return False

	def verifyNetworkConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Lan.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		interfacesPattern = re.compile('wlan[0-9]+' '|' 'eth[0-9]+') # Se buscan interfaces de 0 a 100
		activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
		networkInterfaces = os.popen('ip link show').readlines()
		patternMatched = None
		stateUP = False
		for interface in networkInterfaces:
			# Buscamos a lo largo de la cadena si hay alguna coincidencia de una RE
			patternMatched = interfacesPattern.search(interface)
			if patternMatched is not None and interface.find("state UP") > 0:
				stateUP = True
				# 'patternMatched.group()' devuelve la cadena (interfaz) que coincide con la RE
				if (patternMatched.group() + '\n') not in activeInterfacesFile.read():
					# Como la interfazlocalInterface encontrada no está siendo usada, la ponemos a escuchar si no está activa
					if not self.networkInstance.isActive:
						# Escribimos en nuestro archivo la interfaz a usar, para indicar que está ocupada
						activeInterfacesFile.write(patternMatched.group() + '\n')
						self.networkInstance.connect(patternMatched.group())
						activeInterfacesFile.close()
						networkThread = threading.Thread(target = self.networkInstance.receive, name = self.networkThreadName)
						networkThread.start()
						networkInfo = patternMatched.group() + ' - ' + self.networkInstance.localAddress
						logger.write('INFO', '[NETWORK] Listo para usarse (' + networkInfo + ').')
						return True
				# Si la interfaz ya está en modo activo (funcionando), devolvemos 'True'
				elif self.networkInstance.isActive:
					return True
		# Si ya no se encontró ninguna interfaz UP y ya estabamos escuchando, dejamos de hacerlo
		if stateUP is False and self.networkInstance.isActive:
			self.networkInstance.isActive = False
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(self.networkInstance.localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
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
			if not self.emailInstance.isActive and not self.emailInstance.failedConnection:
				self.emailInstance.connect()
				emailThread = threading.Thread(target = self.emailInstance.receive, name = self.emailThreadName)
				emailThread.start()
				logger.write('INFO', '[EMAIL] Listo para usarse (' + self.emailInstance.emailAccount + ').')
				return True
			# Si el email ya está en modo activo (funcionando), devolvemos 'True'
			elif self.emailInstance.isActive:
				return True
			# Entonces significa que hubo un error en la conexión (función 'connect()')
			else:
				return False
		# No hay conexión a Internet, por lo que se debe hacer reintentos
		except socket.error as DNSError:
			if self.emailInstance.isActive:
				self.emailInstance.isActive = False
			return False
		# Error con los servidores SMTP e IMAP (probablemente estén mal escritos o el puerto sea incorrecto)
		except Exception as errorMessage:
			logger.write('ERROR', '[EMAIL] Error al intentar conectar con los servidores SMTP e IMAP')
			if not self.emailInstance.failedConnection:
				self.emailInstance.failedConnection = True

	def verifyBluetoothConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Bluetooth.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
		# Ejemplo de bluetoothDevices: ['Devices:\n', '\thci0\t00:24:7E:64:7B:4A\n']
		bluetoothDevices = os.popen('hcitool dev').readlines()
		# Sacamos el primer elemento por izquierda ('Devices:\n')
		bluetoothDevices.pop(0)
		if len(bluetoothDevices) > 0:
			btDeviceList = list()
			for btDevice in bluetoothDevices:
				btDevice = btDevice.split('\t')[2].replace('\n', '')
				btDeviceList.append(btDevice)
				if btDevice not in activeInterfacesFile.read():
					# Como la MAC encontrada no está siendo usada, la ponemos a escuchar si no está activa
					if not self.bluetoothInstance.isActive:
						# Escribimos en nuestro archivo la MAC a usar, para indicar que está ocupada
						activeInterfacesFile.write(btDevice + '\n')
						self.bluetoothInstance.connect(btDevice)
						bluetoothThread = threading.Thread(target = self.bluetoothInstance.receive, name = self.bluetoothThreadName)
						bluetoothThread.start()
						logger.write('INFO', '[BLUETOOTH] Listo para usarse (' + btDevice + ').')
						return True
			# Si llegamos acá, es porque el archivo contiene una MAC que quizás fue desconectada y debemos borrarla
			if self.bluetoothInstance.isActive and self.bluetoothInstance.localMACAddress not in btDeviceList:
				self.bluetoothInstance.isActive = False
				# Eliminamos del archivo la MAC usada
				dataToWrite = open('/tmp/activeInterfaces').read().replace(self.bluetoothInstance.localMACAddress + '\n', '')
				activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
				activeInterfacesFile.write(dataToWrite)
				activeInterfacesFile.close()
				return False
			# Si la MAC ya está en modo activo (funcionando), devolvemos 'True'
			else:
				return True
		else:
			if self.bluetoothInstance.isActive:
				self.bluetoothInstance.isActive = False
				# Eliminamos del archivo la MAC usada
				dataToWrite = open('/tmp/activeInterfaces').read().replace(self.bluetoothInstance.localMACAddress + '\n', '')
				activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
				activeInterfacesFile.write(dataToWrite)
				activeInterfacesFile.close()
			return False
