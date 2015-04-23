"""	Permite crear una instancia que se encargara de generar 'interrupciones' al
	dispositivo cada un determinado lapso de tiempo, que podra ser configurable.
	Es decir, el objeto se encargara de medir tiempo. Cuando ese intervalo de
	tiempo sea alcanzado, enviara una senial al modem o al modulo de manejo de
	email para notificarle que se produjo ese evento y que proceda a ejecutar
	lo que sea necesario. Ocurrido el suceso, el temporizador se reinicia y la
	cuenta comienza nuevamente.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Febrero de 2015 """

import threading

class Timer(threading.Thread):
	""" Clase 'Timer'. Permite la creacion de instancias de temporizacion
            en forma de hilos. """
	def __init__(self, timerName):
		""" Constructor de la clase 'Timer'.
                    @param timerName: nombre de la instancia
                    @type timerName: str """
		threading.Thread.__init__(self, name = timerName)
		self.daemon = True
		self.timingInterval = 60
		self.redefineInterval_flag = False
		self.timeExceeded_flag = False
		self.endTimer = False
		self.timerThread = threading.Timer(self.timingInterval, self.resetTimer)
		
	def run(self):
		""" Metodo 'run' del hilo. Se encarga de lanzar un sub hilo cuyo modo de
                    operacion sera el de medir tiempo y ejecutar la funcion 'resetTimer'
                    cuando este sea alcanzado. Ademas, tiene la posibilidad de redefinir
                    el intervalo de tiempo que se desea medir. """
		self.timerThread.start()
		while not self.endTimer:
			if self.redefineInterval_flag:
				print self.getName() + ': Intervalo cambiado a ' + str(self.timingInterval)
				self.redefineInterval_flag = False
		print self.getName() + ' finalizado.'
		
	def resetTimer(self):
		""" Indica al modem que el intervalo de tiempo fue alcanzado estableciendo
                    una bandera. Se crea nuevamente otro sub hilo y se lo pone en ejecucion
                    para realizar de nuevo la cuenta. """
		self.timeExceeded_flag = True
		self.timerThread = threading.Timer(self.timingInterval, self.resetTimer)
		self.timerThread.start()
	
	def getTimeExceeded_flag(self):
                """ Devuelve el estado de la bandera que indica tiempo excedido.
                    @return: estado de la bandera de tiempo excedido
                    @rtype: bool """
		return self.timeExceeded_flag
	
	def clearTimeExceeded_flag(self):
                """ Limpia la bandera de tiempo excedido. """
		self.timeExceeded_flag = False
