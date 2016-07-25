 # coding=utf-8

import os
import re
import time
import socket
import inspect
import threading
import subprocess

import logger

gsmThreadName = 'gsmReceptor'
gprsThreadName = 'gprsReceptor'
wifiThreadName = 'wifiReceptor'
emailThreadName = 'emailReceptor'
ethernetThreadName = 'ethernetReceptor'
bluetoothThreadName = 'bluetoothReceptor'

threadNameList = [gsmThreadName, gprsThreadName, wifiThreadName, ethernetThreadName, bluetoothThreadName, emailThreadName]

class Controller(threading.Thread):

	availableGsm = False       # Indica si el modo GSM está disponible
	availableGprs = False      # Indica si el modo GPRS está disponible
	availableWifi = False      # Indica si el modo WIFI está disponible
	availableEthernet = False  # Indica si el modo ETHERNET está disponible
	availableBluetooth = False # Indica si el modo BLUTOOTH está disponible
	availableEmail = False     # Indica si el modo EMAIL está disponible

	gsmInstance = None
	gprsInstance = None
	wifiInstance = None
	ethernetInstance = None
	bluetoothInstance = None
	emailInstance = None

	isActive = False

	def __init__(self, _REFRESH_TIME):
		threading.Thread.__init__(self, name = 'ControllerThread')
		self.REFRESH_TIME = _REFRESH_TIME

	def __del__(self):
		self.gsmInstance.isActive = False
		self.gprsInstance.isActive = False
		self.wifiInstance.isActive = False
		self.ethernetInstance.isActive = False
		self.bluetoothInstance.isActive = False
		self.emailInstance.isActive = False
		# Esperamos que terminen los hilos receptores
		for receptorThread in threading.enumerate():
			if receptorThread.getName() in threadNameList and receptorThread.isAlive():
				receptorThread.join()
		logger.write('INFO', '[CONTROLLER] Objeto destruido.')

	def run(self):
		self.isActive = True
		while self.isActive:
			self.availableGsm = self.verifyGsmConnection()
			self.availableGprs = self.verifyGprsConnection()
			self.availableWifi = self.verifyWifiConnection()
			self.availableEthernet = self.verifyEthernetConnection()
			self.availableBluetooth = self.verifyBluetoothConnection()
			self.availableEmail = self.verifyEmailConnection()
			time.sleep(self.REFRESH_TIME)
		logger.write('WARNING', '[CONTROLLER] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def verifyGsmConnection(self):
		# Generamos la expresión regular
		ttyUSBPattern = re.compile('ttyUSB[0-9]+')
		lsDevProcess = subprocess.Popen(['ls', '/dev/'], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
		lsDevOutput, lsDevError = lsDevProcess.communicate()
		ttyUSBDevices = ttyUSBPattern.findall(lsDevOutput)
		# Se detectaron dispositivos USB conectados
		for ttyUSBx in reversed(ttyUSBDevices):
			# Si el puerto serie nunca fue establecido, entonces la instancia no esta siendo usada
			if self.gsmInstance.serialPort is None:
				# Si no se produce ningún error durante la configuración, ponemos al módem a recibir SMS y llamadas
				if self.gsmInstance.connect('/dev/' + ttyUSBx):
					gsmThread = threading.Thread(target = self.gsmInstance.receive, name = gsmThreadName)
					logger.write('INFO', '[GSM] Listo para usarse (' + ttyUSBx + ').')
					gsmThread.start()
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# Si el módem ya está en modo activo (funcionando), devolvemos 'True'
			elif self.gsmInstance.isActive:
				return True
			# Llegamos acá si se produce un error en el 'connect' del módem (y todavía está conectado)
			else:
				return False
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar el puerto
		if self.gsmInstance.serialPort is not None:
			self.gsmInstance.successfulConnection = None
			self.gsmInstance.serialPort = None
			self.gsmInstance.isActive = False
			self.gsmInstance.closePort()
		return False

	def verifyGprsConnection(self):
		# Generamos la expresión regular
		pppPattern = re.compile('ppp[0-9]+')
		for networkInterface in os.popen('ip link show').readlines():
			# Con 'pppPattern.search(networkInterface)' buscamos alguna coincidencia
			matchedPattern = pppPattern.search(networkInterface)
			# La interfaz actual coincide con un patrón 'ppp'
			if matchedPattern is not None and networkInterface.find("state UNKNOWN") > 0:
				# Esto se cumple cuando nunca se realizó un intento de configuración
				if self.gprsInstance.localInterface is None:
					# Obtenemos la interfaz que concide con el patrón
					self.gprsInstance.localInterface = matchedPattern.group()
					# Obtenemos la dirección IP local asignada estáticamente o por DHCP
					commandToExecute = 'ip addr show ' + self.gprsInstance.localInterface + ' | grep inet'
					localIPAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
					# Si no se produce ningún error durante la configuración, ponemos a la IP a escuchar
					if self.gprsInstance.connect(localIPAddress):
						gprsThread = threading.Thread(target = self.gprsInstance.receive, name = gprsThreadName)
						gprsInfo = self.gprsInstance.localInterface + ' - ' + self.gprsInstance.localIPAddress
						logger.write('INFO', '[GRPS] Listo para usarse (' + gprsInfo + ').')
						gprsThread.start()
						return True
					# Si se produce un error durante la configuración, devolvemos 'False'
					else:
						return False
				# El patrón coincidente es igual a la interfaz de la instancia
				elif matchedPattern.group() == self.gprsInstance.localInterface:
					# Si no se produjo ningún error durante la configuración, devolvemos 'True'
					if self.gprsInstance.successfulConnection:
						return True
					# Entonces significa que hubo un error, devolvemos 'False'
					else:
						return False
				# El patrón coincidente está siendo usado pero no es igual a la interfaz de la instancia
				else:
					continue
			# No se encontró coincidencia en la iteración actual, entonces seguimos buscando
			else:
				continue
		# Si entramos es porque había una conexión activa y se perdió
		if self.gprsInstance.localInterface is not None:
			# Limpiamos todos los campos del objeto NETWORK
			self.gprsInstance.successfulConnection = None
			self.gprsInstance.localInterface = None
			self.gprsInstance.localIPAddress = None
			self.gprsInstance.isActive = False
		return False

	def verifyWifiConnection(self):
		# Generamos la expresión regular
		wlanPattern = re.compile('wlan[0-9]+')
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		for networkInterface in os.popen('ip link show').readlines():
			# Con 'wlanPattern.search(networkInterface)' buscamos alguna coincidencia
			matchedPattern = wlanPattern.search(networkInterface)
			# La interfaz actual coincide con un patrón 'wlan'
			if matchedPattern is not None and networkInterface.find("state UP") > 0:
				# El patrón coincidente no está siendo usado y la instancia no está activa (habrá que habilitarla)
				if matchedPattern.group() not in activeInterfacesList and self.wifiInstance.localInterface is None:
					# Obtenemos la interfaz que concide con el patrón
					self.wifiInstance.localInterface = matchedPattern.group()
					# Escribimos en nuestro archivo la interfaz, para indicar que está ocupada
					activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
					activeInterfacesFile.write(self.wifiInstance.localInterface + '\n')
					activeInterfacesFile.close()
					# Obtenemos la dirección IP local asignada estáticamente o por DHCP
					commandToExecute = 'ip addr show ' + self.wifiInstance.localInterface + ' | grep inet'
					localIPAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
					# Si no se produce ningún error durante la configuración, ponemos a la IP a escuchar
					if self.wifiInstance.connect(localIPAddress):
						wifiThread = threading.Thread(target = self.wifiInstance.receive, name = wifiThreadName)
						wifiInfo = self.wifiInstance.localInterface + ' - ' + self.wifiInstance.localIPAddress
						logger.write('INFO', '[WIFI] Listo para usarse (' + wifiInfo + ').')
						wifiThread.start()
						return True
					# Si se produce un error durante la configuración, devolvemos 'False'
					else:
						return False
				# El patrón coincidente es igual a la interfaz de la instancia
				elif matchedPattern.group() == self.wifiInstance.localInterface:
					# Si no se produjo ningún error durante la configuración, devolvemos 'True'
					if self.wifiInstance.successfulConnection:
						return True
					# Entonces significa que hubo un error, devolvemos 'False'
					else:
						return False
				# El patrón coincidente está siendo usado pero no es igual a la interfaz de la instancia
				else:
					continue
			# No se encontró coincidencia en la iteración actual, entonces seguimos buscando
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la interfaz
		if self.wifiInstance.localInterface is not None:
			localInterface = self.wifiInstance.localInterface
			# Limpiamos todos los campos del objeto NETWORK
			self.wifiInstance.successfulConnection = None
			self.wifiInstance.localInterface = None
			self.wifiInstance.localIPAddress = None
			self.wifiInstance.isActive = False
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False

	def verifyEthernetConnection(self):
		# Generamos la expresión regular
		ethPattern = re.compile('eth[0-9]+')
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		for networkInterface in os.popen('ip link show').readlines():
			# Con 'ethPattern.search(networkInterface)' buscamos alguna coincidencia
			matchedPattern = ethPattern.search(networkInterface)
			# La interfaz actual coincide con un patrón 'eth'
			if matchedPattern is not None and networkInterface.find("state UP") > 0:
				# El patrón coincidente no está siendo usado y la instancia no está activa (habrá que habilitarla)
				if matchedPattern.group() not in activeInterfacesList and self.ethernetInstance.localInterface is None:
					# Obtenemos la interfaz que concide con el patrón
					self.ethernetInstance.localInterface = matchedPattern.group()
					# Escribimos en nuestro archivo la interfaz, para indicar que está ocupada
					activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
					activeInterfacesFile.write(self.ethernetInstance.localInterface + '\n')
					activeInterfacesFile.close()
					# Obtenemos la dirección IP local asignada estáticamente o por DHCP
					commandToExecute = 'ip addr show ' + self.ethernetInstance.localInterface + ' | grep inet'
					localIPAddress = os.popen(commandToExecute).readline().split()[1].split('/')[0]
					# Si no se produce ningún error durante la configuración, ponemos a la IP a escuchar
					if self.ethernetInstance.connect(localIPAddress):
						ethernetThread = threading.Thread(target = self.ethernetInstance.receive, name = ethernetThreadName)
						ethernetInfo = self.ethernetInstance.localInterface + ' - ' + self.ethernetInstance.localIPAddress
						logger.write('INFO', '[ETHERNET] Listo para usarse (' + ethernetInfo + ').')
						ethernetThread.start()
						return True
					# Si se produce un error durante la configuración, devolvemos 'False'
					else:
						return False
				# El patrón coincidente es igual a la interfaz de la instancia
				elif matchedPattern.group() == self.ethernetInstance.localInterface:
					# Si no se produjo ningún error durante la configuración, devolvemos 'True'
					if self.ethernetInstance.successfulConnection:
						return True
					# Entonces significa que hubo un error, devolvemos 'False'
					else:
						return False
				# El patrón coincidente está siendo usado pero no es igual a la interfaz de la instancia
				else:
					continue
			# No se encontró coincidencia en la iteración actual, entonces seguimos buscando
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la interfaz
		if self.ethernetInstance.localInterface is not None:
			localInterface = self.ethernetInstance.localInterface
			# Limpiamos todos los campos del objeto NETWORK
			self.ethernetInstance.successfulConnection = None
			self.ethernetInstance.localInterface = None
			self.ethernetInstance.localIPAddress = None
			self.ethernetInstance.isActive = False
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False

	def verifyBluetoothConnection(self):
		activeInterfacesList = open('/tmp/activeInterfaces', 'a+').read()
		# Ejemplo de bluetoothDevices: ['Devices:\n', '\thci0\t00:24:7E:64:7B:4A\n']
		bluetoothDevices = os.popen('hcitool dev').readlines()
		# Sacamos el primer elemento por izquierda ('Devices:\n')
		bluetoothDevices.pop(0)
		for btDevice in bluetoothDevices:
			# Ejemplo de btDevice: \thci0\t00:24:7E:64:7B:4A\n
			btInterface = btDevice.split('\t')[1]
			btAddress = btDevice.split('\t')[2].replace('\n', '')
			# La interfaz encontrada no está siendo usada y la instancia no está activa (habrá que habilitarla)
			if btInterface not in activeInterfacesList and self.bluetoothInstance.localInterface is None:
				# Obtenemos la interfaz encontrada
				self.bluetoothInstance.localInterface = btInterface
				# Escribimos en nuestro archivo la interfaz, para indicar que está ocupada
				activeInterfacesFile = open('/tmp/activeInterfaces', 'a+')
				activeInterfacesFile.write(btInterface + '\n')
				activeInterfacesFile.close()
				# Si no se produce ningún error durante la configuración, ponemos a la MAC a escuchar
				if self.bluetoothInstance.connect(btAddress):
					bluetoothThread = threading.Thread(target = self.bluetoothInstance.receive, name = bluetoothThreadName)
					bluetoothInfo = self.bluetoothInstance.localInterface + ' - ' + self.bluetoothInstance.localMACAddress
					logger.write('INFO', '[BLUETOOTH] Listo para usarse (' + bluetoothInfo + ').')
					bluetoothThread.start()
					return True
				# Si se produce un error durante la configuración, devolvemos 'False'
				else:
					return False
			# La interfaz encontrada es igual a la interfaz de la instancia
			elif btInterface == self.bluetoothInstance.localInterface:
				# Si no se produjo ningún error durante la configuración, devolvemos 'True'
				if self.bluetoothInstance.successfulConnection:
					return True
				# Entonces significa que hubo un error, devolvemos 'False'
				else:
					return False
			# La interfaz encontrada está siendo usado pero no es igual a la interfaz de la instancia
			else:
				continue
		# Si anteriormente hubo un intento de 'connect()' con o sin éxito, debemos limpiar la interfaz
		if self.bluetoothInstance.localInterface is not None:
			localInterface = self.bluetoothInstance.localInterface
			# Limpiamos todos los campos del objeto BLUETOOTH
			self.bluetoothInstance.successfulConnection = None
			self.bluetoothInstance.localMACAddress = None
			self.bluetoothInstance.localInterface = None
			self.bluetoothInstance.isActive = False
			# Eliminamos del archivo la interfaz de red usada
			dataToWrite = open('/tmp/activeInterfaces').read().replace(localInterface + '\n', '')
			activeInterfacesFile = open('/tmp/activeInterfaces', 'w')
			activeInterfacesFile.write(dataToWrite)
			activeInterfacesFile.close()
		return False

	def verifyEmailConnection(self):
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