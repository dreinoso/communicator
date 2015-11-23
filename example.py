# coding=utf-8

import os
import sys
import time
import termios

import contactList
import communicator
import messageClass

def main():
	endMain = False
	os.system('clear')

	print '----------- MODULO DE COMUNICACION -----------\n'
	print '\t\t1 - Enviar mensaje/archivo'
	print '\t\t2 - Leer'
	print '\t\t3 - Conectar GPRS'
	print '\t\t4 - Desconectar GPRS'
	print '\t\t5 - Enviar instancia mensaje preestablecido'
	print '\t\t6 - Enviar instancia archivo preestablecido'
	print '\t\t7 - Salir'
	print '\t\tc - DEBUG: Cerrar Comunicador'
	print '\t\ta - DEBUG: Abrir Comunicador\n'


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
					receiver = raw_input('Nombre del cliente: ')
					if contactList.allowedNumbers.has_key(receiver):
						messageToSend = raw_input('Mensaje/archivo a enviar: ')
					else:
						print 'El cliente no existe. Operación abortada.'
						continue
				elif showClients is 'N' or showClients is 'n':
					receiver = raw_input('Cliente a enviar: ')
					messageToSend = raw_input('Mensaje/archivo a enviar: ')
				else:
					print 'Abortado.'
					continue
				# Los 'continue' anteriores se pusieron para que no realice el envio, en caso de error
				communicator.send(messageToSend, receiver) # Envío de mensaje simple
			# Opcion 2 - Leer
			elif optionSelected is '2':
				messageReceived = communicator.receive()
				if messageReceived != None:
					if isinstance(messageReceived, messageClass.Message):
						print 'Instancia de mensaje recibida: ' + str(messageReceived)
						print '\tEmisor: ' + messageReceived.sender
						print '\tPrioridad: ' + str(messageReceived.priority)
						if isinstance(messageReceived, messageClass.SimpleMessage):
							print '\tMensaje de texto: ' + str(messageReceived.plainText)
						elif isinstance(messageReceived, messageClass.FileMessage):
							print '\tNombre del archivo: ' + messageReceived.fileName
					else:
						print 'Mensaje recibido: %s' % messageReceived
			# Opcion 3 - Conectar GPRS
			elif optionSelected is '3':
				communicator.connectGprs()
			# Opcion 4 - Desconectar GPRS
			elif optionSelected is '4':
				communicator.disconnectGprs()
			# Opcion 5 - Instancia de mensaje de prueba
			elif optionSelected is '5':
				simpleMessage = messageClass.SimpleMessage('Datalogger01', 'client02', 'Este es un mensaje de prueba.', 'NETWORK')
				communicator.send(simpleMessage)
			# Opción 6 - Instancia de archivo de prueba
			elif optionSelected is '6':
				fileInstance = messageClass.FileMessage('Datalogger01', 'client02', 'ASD.pdf')
				communicator.send(fileInstance)
			# Opcion 7 - Salir
			elif optionSelected is '7':
				endMain = True
			elif optionSelected is 'c':
				communicator.close()
			elif optionSelected is 'a':
				communicator.open()
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
