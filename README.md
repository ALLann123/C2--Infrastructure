# Command and Control- APT features: Redirector

Building my own command and control server🏴‍☠️

# Server side(Kali Linux->Python)

- Python is an amazing scripting language. We will use it to interact with infected zombies
  
LOCATION: command_and_control/main.py

# Agent/Implant(Go Language🎉🎉)

- Golang is a cross-platform language allowing us to write code that can be compiled for different operating systems.
-  Go is fast like C/C++ with a syntax similar to Python.

LOCATION: agent/main.go
- Compiling for Windows on PowerShell
  
  `Ps> go build -o shell.exe main.go`
- Compiling for Linux on PowerShell
  
  `Ps> $env:GOOS = "linux";  go build -o shell main.go`

# WorkFlow

<img width="847" height="479" alt="Screenshot 2025-11-24 133726" src="https://github.com/user-attachments/assets/fdc8e355-953e-455d-b1ff-51bdf54d2883" />


# Getting Started:

<img width="1013" height="453" alt="Screenshot 2025-11-24 113718" src="https://github.com/user-attachments/assets/5e143c8f-3387-47ef-ae38-4a0d1c8e6562" />

# C2 Web SHell Redirector

Server- Python(server.py)

Agent(Implant)- C/C++(client.cpp)

NOTE: Added a Go implant; the advantage is cross-compile support. One code can be cross-compiled for different operating systems.🎆🎆🎆🥳

On PowerShell:

For Linux

`$env:GOOS = "linux"; $env:GOARCH = "amd64"; go build -o client_linux main.go`

For Windows

`$env:GOOS = "windows"; $env:GOARCH = "amd64"; go build -o client_windows.exe main.go`

For macOS

`$env:GOOS = "darwin"; $env:GOARCH = "amd64"; go build -o client_macos main.go`

<img width="854" height="537" alt="image" src="https://github.com/user-attachments/assets/28cb81df-712f-41a8-afbb-278b9e572033" />

