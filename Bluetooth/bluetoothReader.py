import threading
import bluetooth

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024

class BluetoothReader(threading.Thread):

	killReaderThread = False

	def __init__(self, threadName, remoteSocket):
		threading.Thread.__init__(self, name = threadName)
		self.remoteSocket = remoteSocket

	def run(self):
		while not self.killReaderThread:
			try:
				''' Operacion bloqueante, que espera recibir al menos un byte o hasta que el extremo remoto este cerrado.
					Cuando el otro extremo este desconectado y todos los caracteres hayan sido leidos, la funcion retorna
					una cadena vacia. '''
				dataReceived = self.remoteSocket.recv(BUFFER_SIZE)
				if dataReceived == 'FIN':
					self.killReaderThread = True
				else:
					print self.getName() + ': %s' % dataReceived
			except bluetooth.BluetoothError:
				pass
		# Cierra la conexion del socket cliente
		self.remoteSocket.close()
		print '\'' + self.getName() + '\' terminado y cliente desconectado.'
