Como primer paso antes de la ejecución se debe ir al archivo correspondiente de agenda 
(contactList.py) en dicho archivo se debe agregar la cuenta y contraseña del "servidor", 
es decir del usuario del Modulo. Por otro lado se deben tener registrados los usuarios 
que se pretendan para la comunicación con su correspondiente cuenta respetando el formato
establecido.

En su aplicación se debe tener importado el modulo "import communicator.py". El uso del 
comunicador se basa en el llamado de 4 funciones:

	-communicator.open()
		Se realiza la apertura, inicialización de los componentes que se tengan disponibles.

	-communicator.send(contact, message)
		Se envia de modo "inteligente" un paquete de datos a un contacto previamente registrado
		el mensaje se envia por el medio mas óptimo encontrado.
		@param contact: Nombre de contacto previamente registrado
		@param message: Mensaje a ser enviado

	-recieve()
		Se obtiene de un buffer circular el mensaje recibido mas antiguo.
		@return Mensaje recibido

	-close()
		Se cierran los componentes del sistema, unicamente los abiertos previamente.

Para mayor entenimiento del módulo se deja un archivo de ejemplo "example.py".