 # coding=utf-8

import time
import communicator

def main():
	print '--------------------------------------' 
	print 'Ejemplo de aplicación del Comunicador'
	print '--------------------------------------\n' 
	print 'Comandos disponibles:'
	print '    1) Enviar Mensaje.'
 	print '    2) Enviar Paquete.'
	print '    3) Leer.'
	print '    4) Salir.\n'

	communicator.open() # Se abre el comunicador para detectar medios
	time.sleep(5) # Da tiempo a que se inicien los modulos del comunicador

	optionSelected = int(raw_input())
	while optionSelected != 4:
		if optionSelected == 1:
			clientToSend = 'client02' #raw_input('Cliente a enviar: ')
			messageToSend = 'Hola' #raw_input('Mensaje a enviar: ')
			communicator.send(clientToSend, messageToSend, False)
		elif optionSelected == 2:
			clientToSend = 'client02'#raw_input('Cliente a enviar: ')
			packetName = 'video.mp4'#raw_input('Nombre del Paquete: ')
			communicator.send(clientToSend, packetName, True)
		elif optionSelected == 3:
			messageRecived = communicator.recieve()
			if messageRecived != None:
				print 'El mensaje recibido es: ' + messageRecived
		else:
			print 'Opción inválida..'
		optionSelected = int(raw_input('Opción: '))
	communicator.close() # Se cierran las conexiones

if __name__ == '__main__':
	main() 
