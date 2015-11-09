# coding=utf-8

import os
import sys
import time
import termios

import contactList
import communicator

import messageClass
import exampleClass

def main():
	endMain = False
	os.system('clear')

	print '----------- MODULO DE COMUNICACION -----------\n'
	print '\t\t1 - Enviar mensaje/archivo'
	print '\t\t2 - Leer'
	print '\t\t3 - Conectar GPRS'
	print '\t\t4 - Desconectar GPRS'
	print '\t\t5 - Enviar mensaje simple preestablecido' # Pruebas más directas del módulo..
	print '\t\t6 - Enviar instancia mensaje preestablecido'
	print '\t\t7 - Enviar archivo simple preestablecido'
	print '\t\t8 - Enviar instancia archivo preestablecido'
	print '\t\t9 - Salir\n'

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
				communicator.send(messageToSend,receiver) # Envío de mensaje simple
			# Opcion 2 - Leer
			elif optionSelected is '2':
				messageRecived = communicator.receive()
				if messageRecived != None:
					if isinstance(messageRecived, messageClass.FileMessage):
						print 'Instancia de Archivo recibida: ' + str(messageRecived)
						print '\tEmisor del archivo: ' + messageRecived.sender
						print '\tPrioridad del archivo: ' + str(messageRecived.priority)
						print '\tNombre del archivo: ' + messageRecived.fileName
						if messageRecived.received:	# Comprobación de la recepción
							print '\tEste archivo se recibio correctamente' 
						else:
							print '\tEste archivo no se recibio' 
					elif isinstance(messageRecived, messageClass.Message):
						print 'Instancia de Mensaje recibida: ' + str(messageRecived)
						print '\tEmisor del mensaje: ' + messageRecived.sender
						print '\tPrioridad del mensaje: ' + str(messageRecived.priority)
						print '\tAtributo 1: ' + str(messageRecived.atribute1)
						print '\tAtributo 2: ' + messageRecived.atribute2
						messageRecived.setAtribute2('Se ha cambiado el atributo 2') # Prueba de un método
						print '\tAtributo 2: ' + messageRecived.atribute2
					elif messageRecived.startswith('ARCHIVO_RECIBIDO'):
						print 'El Archivo recibido es: ' + messageRecived.split()[1]
					else:
						print 'El mensaje recibido es: ' + messageRecived
			# Opcion 3 - Conectar GPRS
			elif optionSelected is '3':
				communicator.connectGprs()
			# Opcion 4 - Desconectar GPRS
			elif optionSelected is '4':
				communicator.disconnectGprs()
			# Opcion 5 - Mensaje de Prueba
			elif optionSelected is'5':
				communicator.send('Este es un mensaje de prueba.','client02','') # Prioridad por Bluetooth
			# Opcion 6 - Instancia de mensaje de prueba
			elif optionSelected is '6':
				messageInstance = exampleClass.ExampleMessage('client02', 'Comunicardor Emisor Alfa', 5, 35, 'SMS') # Prioridad por SMS
				messageInstance.setAtribute1(55555)
				messageInstance.setAtribute2('Este es el atributo 2 de una instancia mensaje')
				communicator.send(messageInstance)
			# Opción 7 - Envio de Archivo de prueba
			elif optionSelected is '7':
				communicator.send('imagen.jpg', 'client02') # Prioridad definida por configuración
			# Opción 8 - Instancia de archivo de prueba
			elif optionSelected is '8':
				fileInstance = messageClass.FileMessage('client02', 'Comunicardor Emisor Alfa', 10, 100, '', 'imagen.jpg') # Prioridad email
				communicator.send(fileInstance)
			# Opcion 9 - Salir
			elif optionSelected is '9':
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
