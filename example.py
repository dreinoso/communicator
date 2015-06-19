 # coding=utf-8

import communicator
import time

def main():
	print '--------------------------------------------' 
	print 'Ejemplo de aplicación del módulo Comunicador.'
	print '--------------------------------------------\n' 
	print 'Comandos disponibles:'
	print '    1) Enviar.'
	print '    2) Leer.'
	print '    3) Salir.\n'

	communicator.open()# Se abre el comunicador para detectar medios
	time.sleep(4) #Da tiempo a que se inicien los modulos del comunicador
	optionSelected = int(raw_input('Seleccione una de las opciones: '))
	while optionSelected != 3:
		if optionSelected == 1:
			messageSend = 'Este es el mensaje, lo envia el comunicador..'
			communicator.send('Client02', messageSend)
		elif optionSelected == 2:
			messageRecived = communicator.recieve()
			if messageRecived != None:
				print 'El mensaje leido es: ' + messageRecived
		else:
			print 'Opción inválida..'
		optionSelected = int(raw_input('Seleccione una de las opciones: '))

	communicator.close()# Se cierran las conexiones

if __name__ == '__main__':
	main() 
