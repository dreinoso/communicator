import socket
def is_connected():
	REMOTE_SERVER = "mail.google.com"
	try:
		host = socket.gethostbyname(REMOTE_SERVER) # Obtiene el DNS
		s = socket.create_connection((host, 80), 2) # Se determina si es alcanzable
		return True
	except:
		pass
	return False

print is_connected()