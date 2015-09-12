# coding=utf-8
"""	Modulo cuya finalidad es proporcionar funciones que se encarguen de la
	recepcion de paquetes de datos y mensajes en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """
import logger

import threading
import socket
import inspect
import os
import Queue

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024
TIMEOUT = 2

class UdpLanReceptor(threading.Thread):
	
	isActive = False
	receptionBuffer = Queue.Queue()
	udpConfiguration = ''
	udpConnectionPortList = []

	def __init__(self, _threadName, _receptionBuffer, _isActive, _udpConfiguration, _udpConnectionIp, _udpConnectionPortList):
		threading.Thread.__init__(self, name = _threadName)
		self.receptionBuffer = _receptionBuffer
		self.isActive = _isActive
		self.udpConfiguration = _udpConfiguration
		self.udpConnectionIp = _udpConnectionIp
		self.udpConnectionPortList = _udpConnectionPortList

	def run(self):
		"""Comienzo de la ejecución, en caso de ser TCP debe determinar si se 
		trata de un mensaje o un paquete, mientras que para UDP siempre se tratará
		de un paquete, ya que la recepción es inmediata. No requiere una conexión."""
		self.receiveUdpPacket() # No se pretende un hilo para recepción de mensajes UDP, no genera conexión ni retardo

	def receiveUdpPacket(self):
		"""Recepción de un paquete completo, debe crear el paquete con el nombre
		del archivo que haya indicado el emisor. Se basa para su funcionamiento
		en la recepción de mensajes de control para sincronizar la comunicación."""
		end = False
		try:
			udpConnectionPort = self.udpConnectionPortList.pop() # Se usa la lista para pasar el valor por referencia y modifcar desde el hilo
			receptionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			#if(configReader.CLOSE_PORT): # Para cerrar el puerto en caso de estar ocupado
			command = 'fuser -k -s ' + str(udpConnectionPort) + '/udp' # -k = kill;  -s: modo silecioso
			os.system(command + '\n' + command)			
			receptionSocket.settimeout(TIMEOUT) # En caso de no recibir el paquete salir y no dejar la espera indeterminada.
			receptionSocket.bind((self.udpConnectionIp, udpConnectionPort))
			transmissionSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			dataList = self.udpConfiguration.split(' ') # Se obtienen la dirección del remitente
			destinationIp = dataList[1]
			destinationUdpPort = int(dataList[2])
			logger.write('WARNING', dataList)
			transmissionSocket.sendto(str(udpConnectionPort), (destinationIp, destinationUdpPort))
			packetName, addr = receptionSocket.recvfrom(BUFFER_SIZE)
			logger.write('WARNING', 'Recibiendo.. ' + packetName)
			packet = open(packetName, "wb")
			transmissionSocket.sendto('ACK', (destinationIp, destinationUdpPort))
			while not end:
				data, addr = receptionSocket.recvfrom(BUFFER_SIZE)
				transmissionSocket.sendto('ACK', (destinationIp, destinationUdpPort))
				if data != 'END_OF_PACKET':
					packet.write(data)
				else:
					self.receptionBuffer.put('Paquete (' + packetName + ') recibido con exito.')
					end = True
			packet.close()
			transmissionSocket.close()
			receptionSocket.close()
			self.udpConnectionPortList.append(udpConnectionPort) # Se restaura el puerto UDP que se liberó
		except socket.timeout, errorMessage:
			pass
		except Exception, errorMessage:
			print errorMessage
			self.udpConnectionPortList.append(udpConnectionPort) # Se restaura el puerto UDP que se liberó
