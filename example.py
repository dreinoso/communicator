import communicator
import time

def main():
	communicator.open()# Se abre el comunicador para detectar medios
	messageSend = 'Este es el mensaje, lo envia el comunicador..'
	communicator.send('Cliente1', messageSend)
	messageRecived = communicator.recieve()
	if messageRecived != None:
		print 'El mensaje leido es: ' + messageRecived
	else:
		print 'No hay mensajes nuevos'
	communicator.close()# Se cierran las conexiones

if __name__ == '__main__':
	main()
