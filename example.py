# coding=utf-8

import os
import sys
import time
import termios

import contactList
import communicator

def main():
	endMain = False
	os.system('clear')

	print '----------- MODULO DE COMUNICACION -----------\n'
	print '\t\t1 - Enviar mensaje'
	print '\t\t2 - Enviar paquete'
	print '\t\t3 - Leer'
	print '\t\t4 - Salir\n'

	communicator.open() # Se abre el comunicador para detectar medios
	#time.sleep(5) # Da tiempo a que se inicien los modulos del comunicador
	#print 'Los módulos fueron configurados!'

	while not endMain:
		try:
			termios.tcflush(sys.stdin, termios.TCIOFLUSH) # Limpiamos el stdin
			optionSelected = raw_input()
			# Opcion 1 - Enviar mensaje
			if optionSelected is '1':
				showClients = raw_input('¿Desea enviar un mensaje a un cliente registrado? [S/n] ')
				if showClients is 'S' or showClients is 's' or len(showClients) is 0:
					print contactList.allowedNumbers.keys()
					clientToSend = raw_input('Nombre del cliente: ')
					if contactList.allowedNumbers.has_key(clientToSend):
						messageToSend = raw_input('Mensaje/archivo a enviar: ')
						#messageToSend = 'Bluetooth/DLXCompilerEclipse_v23NewStable.tar.gz'
						#messageToSend = 'Bluetooth/ATD.pdf'
					else:
						print 'El cliente no existe. Operación abortada.'
						continue
				elif showClients is 'N' or showClients is 'n':
					messageToSend = raw_input('Mensaje de texto: ')
				else:
					print 'Abortado.'
					continue
				# Los 'continue' anteriores se pusieron para que no llegue acá, en caso de error
				communicator.send(clientToSend, messageToSend, False)
			# Opcion 2 - Enviar paquete
			elif optionSelected is '2':
				clientToSend = 'client02'#raw_input('Cliente a enviar: ')
				packetName = 'video.mp4'#raw_input('Nombre del Paquete: ')
				communicator.send(clientToSend, packetName, True)
			# Opcion 3 - Leer
			elif optionSelected is '3':
				messageRecived = communicator.recieve()
				if messageRecived != None:
					print 'El mensaje recibido es: ' + messageRecived
			# Opcion 4 - Salir
			elif optionSelected is '4':
				endMain = True
			# Opcion inválida
			else:
				print 'Opción inválida!'
		except KeyboardInterrupt:
			endMain = True

	print 'Cerrando la aplicación...'
	communicator.close() # Se cierran las conexiones
	print '\n---------------- UNC - Fcefyn ----------------'
	print '---------- Ingeniería en Computación ---------'

if __name__ == '__main__':
	main() 
