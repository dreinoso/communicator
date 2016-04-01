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

smsThreadName = 'smsReceptor'
emailThreadName = 'emailReceptor'
networkThreadName = 'networkReceptor'
bluetoothThreadName = 'bluetoothReceptor'

threadNameList = [networkThreadName, smsThreadName, emailThreadName, bluetoothThreadName]

class Controller(threading.Thread):

	availableSms = False       # Indica si el modo SMS está disponible
	availableGprs = False      # Indica si el modo GPRS está disponible
	availableEmail = False     # Indica si el modo EMAIL está disponible
	availableNetwork = False   # Indica si el modo NETWORK está disponible
	availableBluetooth = False # Indica si el modo BLUTOOTH está disponible

	isActive = False

	def __init__(self, _REFRESH_TIME, _smsInstance, _gprsInstance, _emailInstance, _networkInstance, _bluetoothInstance):
		threading.Thread.__init__(self, name = 'ControllerThread')
		self.REFRESH_TIME = _REFRESH_TIME
		# Obtenemos las instancias de los medios
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
		# Esperamos que terminen los hilos receptores
		for receptorThread in threading.enumerate():
			if receptorThread.getName() in threadNameList and receptorThread.isAlive():
				receptorThread.join()
		logger.write('INFO', '[CONTROLLER] Objeto destruido.')

	def run(self):
		self.isActive = True
		while self.isActive:
			self.availableSms = self.verifySmsConnection()
			self.availableGprs = self.verifyGprsConnection()
			self.availableEmail = self.verifyEmailConnection()
			self.availableNetwork = self.verifyNetworkConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			time.sleep(self.REFRESH_TIME)
		logger.write('WARNING', '[CONTROLLER] Funcion \'%s\' terminada.' % inspect.stack()[0][3])

	def verifySmsConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio comunicación SMS.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		# Generamos la expresión regular
		ttyUSBPattern = re.compile('ttyUSB[0-9]+')
		lsDevProcess = subprocess.Popen(['ls', '/dev/'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		lsDevOutput, lsDevError = lsDevProcess.communicate()
		ttyUSBDevices = ttyUSBPattern.findall(lsDevOutput)
		# Se detectaron dispositivos USB conectados
		for ttyUSBx in reversed(ttyUSBDevices):
			# Si el puerto serie nunca fue establecido, entonces la instancia no esta siendo usada
			if self.smsInstance.serialPort is None:
				# Si no se produce ningún error durante la configuración, ponemos al módem a recibir SMS
				if self.smsInstance.connect('/dev/' + ttyUSBx):
					smsThread = threading.Thread(target = self.smsInstance.receive, name = smsThreadName)
					logger.write('INFO', '[SMS] Listo para usarse (' + ttyUSBx + ').')
					smsThread.start()
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# Si el módem ya está en modo activo (funcionando), devolvemos 'True'
			elif self.smsInstance.isActive:
				return True
			# Llegamos acá si se produce un error en el 'connect' del módem (y todavía está conectado)
			else:
				return False
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar el puerto
		if self.smsInstance.serialPort is not None:
			self.smsInstance.successfulConnection = None
			self.smsInstance.serialPort = None
			self.smsInstance.isActive = False
			self.smsInstance.closePort()
		return False

	def verifyGprsConnection(self):
		# Generamos la expresión regular
		pppPattern = re.compile('ppp[0-9]+')
		for networkInterface in os.popen('ip link show').readlines():
			# Con 'pppPattern.search(networkInterface)' buscamos alguna coincidencia
			patternMatched = pppPattern.search(networkInterface)
			if patternMatched is not None and networkInterface.find("state UNKNOWN") > 0:
				# Con 'patternMatched.group()' obtenemos la interfaz que concide con la RE
				if self.gprsInstance.pppInterface is None:
					time.sleep(1)
					self.gprsInstance.pppInterface = patternMatched.group()
					logger.write('INFO', '[GRPS] Listo para usarse (' + patternMatched.group() + ').')
					return True
				# Si el módem ya está en modo activo (funcionando), devolvemos 'True'
				else:
					return True
			# No se encontró coincidencia en la iteración actual, entonces seguimos buscando
			else:
				continue
		# Si entramos es porque había una conexión activa y se perdió
		if self.gprsInstance.pppInterface is not None:
			# Limpiamos todos los campos del objeto
			self.gprsInstance.isActive = False
			self.gprsInstance.pppInterface = None
			self.gprsInstance.local_IP_Address = None
			self.gprsInstance.remote_IP_Address = None
			self.gprsInstance.primary_DNS_Address = None
			self.gprsInstance.secondary_DNS_Address = None
		return False

	def verifyNetworkConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Lan.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		# Generamos la expresión regular
		interfacesPattern = re.compile('wlan[0-9]+' '|' 'eth[0-9]+')
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		for networkInterface in os.popen('ip link show').readlines():
			# Con 'interfacesPattern.search(networkInterface)' buscamos alguna coincidencia
			patternMatched = interfacesPattern.search(networkInterface)
			if patternMatched is not None and networkInterface.find("state UP") > 0:
				# Con 'patternMatched.group()' obtenemos la interfaz que concide con la RE
				# La interfaz actual no esté siendo usada y la instancia no está activa (habrá que habilitarla)
				if patternMatched.group() not in activeInterfacesList and self.networkInstance.localInterface is None:
					# Escribimos en nuestro archivo la interfaz a usar, para indicar que está ocupada
					activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
					activeInterfacesFile.write(patternMatched.group() + '\n')
					activeInterfacesFile.close()
					# Si no se produce ningún error durante la configuración, ponemos a la interfaz a escuchar
					if self.networkInstance.connect(patternMatched.group()):
						networkThread = threading.Thread(target = self.networkInstance.receive, name = networkThreadName)
						networkThread.start()
						networkInfo = patternMatched.group() + ' - ' + self.networkInstance.localAddress
						logger.write('INFO', '[NETWORK] Listo para usarse (' + networkInfo + ').')
						return True
					# Si se produce un error durante la configuración, devolvemos 'False'
					else:
						return False
				# La interfaz actual coincide con la interfaz de la instancia
				elif patternMatched.group() == self.networkInstance.localInterface:
					# Si no se produjo ningún error durante la configuración, devolvemos 'True'
					if self.networkInstance.successfulConnection:
						return True
					# Entonces significa que hubo un error, devolvemos 'False'
					else:
						return False
				# La interfaz actual está siendo usada pero no coincide con la interfaz de la instancia
				else:
					continue
			# No se encontró coincidencia en la iteración actual, entonces seguimos buscando
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la interfaz
		if self.networkInstance.localInterface is not None:
			localInterface = self.networkInstance.localInterface
			self.networkInstance.successfulConnection = None
			self.networkInstance.localInterface = None
			self.networkInstance.isActive = False
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False

	def verifyEmailConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación 
		a través Email.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		TEST_REMOTE_SERVER = 'www.gmail.com'
		try:
			remoteHost = socket.gethostbyname(TEST_REMOTE_SERVER)
			testSocket = socket.create_connection((remoteHost, 80), 2) # Se determina si es alcanzable
			# Comprobamos si aún no intentamos conectarnos con los servidores de GMAIL (por eso el 'None')
			if self.emailInstance.successfulConnection is None:
				# Si no se produce ningún error durante la configuración, ponemos a recibir EMAILs
				if self.emailInstance.connect():
					emailThread = threading.Thread(target = self.emailInstance.receive, name = emailThreadName)
					emailThread.start()
					logger.write('INFO', '[EMAIL] Listo para usarse (' + self.emailInstance.emailAccount + ').')
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# Si EMAIL ya está en modo activo (funcionando), devolvemos 'True'
			elif self.emailInstance.isActive:
				return True
			# Llegamos acá si se produce un error en el 'connect' (servidores o puertos mal configurados)
			else:
				return False
		# No hay conexión a Internet (TEST_REMOTE_SERVER no es alcanzable), por lo que se vuelve a intentar
		except socket.error as DNSError:
			if self.emailInstance.isActive:
				self.emailInstance.successfulConnection = None
				self.emailInstance.emailAccount = None
				self.emailInstance.isActive = False
			return False

	def verifyBluetoothConnection(self):
		"""Se determina la disponibilidad de la comunicación por medio de comunicación Bluetooth.
		@return: Se determina si la comunicación por este medio se puede realizar.
		@rtype: bool"""
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		# Ejemplo de bluetoothDevices: ['Devices:\n', '\thci0\t00:24:7E:64:7B:4A\n']
		bluetoothDevices = os.popen('hcitool dev').readlines()
		# Sacamos el primer elemento por izquierda ('Devices:\n')
		bluetoothDevices.pop(0)
		for btDevice in bluetoothDevices:
			# Ejemplo de btDevice: \thci0\t00:24:7E:64:7B:4A\n
			btDevice = btDevice.split('\t')[2].replace('\n', '')
			# La MAC actual no esté siendo usada y la instancia no está activa (habrá que habilitarla)
			if btDevice not in activeInterfacesList and self.bluetoothInstance.localMACAddress is None:
				# Escribimos en nuestro archivo la MAC a usar, para indicar que está ocupada
				activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
				activeInterfacesFile.write(btDevice + '\n')
				activeInterfacesFile.close()
				# Si no se produce ningún error durante la configuración, ponemos a la MAC a escuchar
				if self.bluetoothInstance.connect(btDevice):
					bluetoothThread = threading.Thread(target = self.bluetoothInstance.receive, name = bluetoothThreadName)
					bluetoothThread.start()
					logger.write('INFO', '[BLUETOOTH] Listo para usarse (' + btDevice + ').')
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# La MAC actual coincide con la MAC de la instancia
			elif btDevice == self.bluetoothInstance.localMACAddress:
				# Si no se produjo ningún error durante la configuración, devolvemos 'True'
				if self.bluetoothInstance.successfulConnection:
					return True
				# Entonces significa que hubo un error, devolvemos 'False'
				else:
					return False
			# La MAC actual está siendo usada pero no coincide con la MAC de la instancia
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la MAC
		if self.bluetoothInstance.localMACAddress is not None:
			localMACAddress = self.bluetoothInstance.localMACAddress
			self.bluetoothInstance.successfulConnection = None
			self.bluetoothInstance.localMACAddress = None
			self.bluetoothInstance.isActive = False
			# Eliminamos del archivo la MAC usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localMACAddress + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False