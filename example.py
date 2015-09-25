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
	print '\t\t1 - Enviar mensaje/archivo'
	print '\t\t2 - Leer'
	print '\t\t3 - Salir\n'

	print 'Configurando el módulo de comunicación...'
	communicator.open() # Se abre el comunicador para detectar medios
	print 'El módulo de comunicación está listo para usarse!'

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
					else:
						print 'El cliente no existe. Operación abortada.'
						continue
				elif showClients is 'N' or showClients is 'n':
					messageToSend = raw_input('Mensaje/archivo a enviar: ')
				else:
					print 'Abortado.'
					continue
				# Los 'continue' anteriores se pusieron para que no llegue acá, en caso de error
				communicator.send(clientToSend, messageToSend)
			# Opcion 2 - Leer
			elif optionSelected is '2':
				messageRecived = communicator.recieve()
				if messageRecived != None:
					print 'El mensaje recibido es: ' + messageRecived
			# Opcion 3 - Salir
			elif optionSelected is '3':
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
