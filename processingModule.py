"""	Modulo central cuya funcion principal es procesar los mensajes de texto
	que el modem GSM recibe, como asi tambien los mensajes de correo electronico.
	Tiene la capacidad de procesar la cabecera del SMS o EMAIL para retornar el numero
	telefonico o direccion de correo electronico del usuario remitente, como asi tambien
	procesar el cuerpo del SMS o EMAIL que contiene el comando que el usuario solicita ejecutar.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Febrero de 2015 """

import frdmClass
import enums

import time

def cmdInput(dataType, dataReceived):
	""" Dependiendo de los parametros que reciba esta funcion, se procese a ejecutar
            la funcion que corresponda.
            @param dataType: tipo de datos a procesar (cabecera o cuerpo del SMS o EMAIL)
            @type dataType: str
            @param dataReceived: datos a procesar
            @type dataReceived: str
            @return: salida del procesamiento
            @rtype: str """
	return processingDictionary[dataType](dataReceived) # Busco cual procesamiento aplicar dependiendo el tipo de datos

def checkStempCommand(stempCommand):
	""" Verifica que el comando 'stemp' este bien formado, es decir, que el intervalo de
            temporizacion este presente y que sea un numero valido (un numero entero).
            @param stempCommand: comando 'stemp'
            @type stempCommand: str
            @return: salida de la verificacion
            @rtype: str """
	stempCommandList = stempCommand.split()
	# Ejemplo de stempCommandList[0]: stemp
	# Ejemplo de stempCommandList[1]: 50
	elementsAmount = len(stempCommandList)
	if elementsAmount == 1:
		# Se recibio solo el comando, sin el nuevo intervalo de temporizacion
		return time.ctime() + ' - ERROR: No ingreso un intervalo de temporizacion!'
	elif elementsAmount == 2 and not stempCommandList[1].isdigit():
		# Se recibio el comando acompanado de un elemento que no es un digito
		return time.ctime() + ' - ERROR: El intervalo ingresado es erroneo!'
	elif elementsAmount == 2 and stempCommandList[1].isdigit() and int(stempCommandList[1]) < 60:
                # Se recibio el comando acompanado de un intervalo no recomendado
		return time.ctime() + ' - ERROR: Intervalo incorrecto. Ingrese un numero entero mayor que 60!'
	else:
		# Devuelvo el comando junto con el nuevo valor del intervalo
		return stempCommand

def reportCommand():
	""" Envia al dispositivo Freescale, los comandos correspondientes que devolveran el estado
            de los pines GPIO.
            @return: lista con el estado de los pines GPIO
            @rtype: list """
        roomStatsList = list()
        roomStatsList.append(roomCommand(enums.specificCommands.ROOM01_STATS))
        roomStatsList.append(roomCommand(enums.specificCommands.ROOM02_STATS))
        roomStatsList.append(roomCommand(enums.specificCommands.BACKYARD_STATS))
        return roomStatsList

def roomCommand(roomCommand):
	""" Envia al dispositivo Freescale, el comando que el usuario solicita ejecutar.
            @param roomCommand: comando que se quiere enviar a la placa
            @type roomCommand: str
            @return: salida devuelta por la placa
            @rtype: str """
        microcontrollerInstance.sendCMD(roomCommand)
        microcontrollerInstance.sendCMD('@')
        time.sleep(1)
        # Una vez enviado el comando que el usuario solicito, enviamos automaticamente otro comando para saber en que estado quedo el pin GPIO...
        if roomCommand == enums.specificCommands.ROOM01_TOGGLE:
                microcontrollerInstance.sendCMD(enums.specificCommands.ROOM01_STATS)
        elif roomCommand == enums.specificCommands.ROOM02_TOGGLE:
                microcontrollerInstance.sendCMD(enums.specificCommands.ROOM02_STATS)
        microcontrollerInstance.sendCMD('@')
        return microcontrollerInstance.readOutput()

def initializeMicrocontroller():
	""" Crea una instancia del 'Microcontroller' de Freescale. """
        global microcontrollerInstance
        microcontrollerInstance = frdmClass.Microcontroller()

processingDictionary = dict()
commandsDictionary = dict()

microcontrollerInstance = frdmClass.Microcontroller

commandsDictionary = {enums.specificCommands.SET_TIMING_INTERVAL : checkStempCommand,
                        enums.specificCommands.ROOM01_TOGGLE	 : roomCommand,
                        enums.specificCommands.ROOM01_STATS	 : roomCommand,
                        enums.specificCommands.ROOM02_TOGGLE	 : roomCommand,
                        enums.specificCommands.ROOM02_STATS	 : roomCommand}
