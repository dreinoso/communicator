"""	Almacena el tipo de datos con el que va a trabajar el programa.
	Dependiendo del valor al que se haga referencia, se aplicara un
	determinado procesamiento. Tambien contiene aquellos comandos
	especificos creados en base a los requerimientos del proyecto, que
	tendran un tratamiento especial.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Febrero de 2015 """

def enum(**enums):
	return type('Enum', (), enums)

dataType = enum(SMS_HEADER   = 'smsHeader',
		SMS_BODY     = 'smsBody',
		EMAIL_HEADER = 'emailHeader',
		EMAIL_BODY   = 'emailBody')

specificCommands = enum(SET_TIMING_INTERVAL = 'stemp',
                        ROOM01_TOGGLE	    = 'room01_toggle',
                        ROOM01_STATS	    = 'room01_stats',
                        ROOM02_TOGGLE	    = 'room02_toggle',
                        ROOM02_STATS	    = 'room02_stats',
                        BACKYARD_STATS	    = 'backyard_stats')
