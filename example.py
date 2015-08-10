 # coding=utf-8

import time
import communicator

def main():
	print '--------------------------------------' 
	print 'Ejemplo de aplicación del Comunicador'
	print '--------------------------------------\n' 
	print 'Comandos disponibles:'
	print '    1) Enviar.'
	print '    2) Leer.'
	print '    3) Salir.\n'

	communicator.open() # Se abre el comunicador para detectar medios
	time.sleep(5) # Da tiempo a que se inicien los modulos del comunicador

	optionSelected = int(raw_input())
	while optionSelected != 3:
		if optionSelected == 1:
			clientToSend = raw_input('Cliente a enviar: ')
			messageToSend = raw_input('Mensaje a enviar: ')
			communicator.send(clientToSend, messageToSend)
		elif optionSelected == 2:
			messageRecived = communicator.recieve()
			if messageRecived != None:
				print 'El mensaje recibido es: ' + messageRecived
		else:
			print 'Opción inválida..'
		optionSelected = int(raw_input())

	communicator.close() # Se cierran las conexiones

if __name__ == '__main__':
	main() 
