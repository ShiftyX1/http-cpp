#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <fstream>
#include <sstream>

using std::cout;
using std::cin;

struct HttpResponseStartLine {
    std::string version;
    int statusCode;
    std::string statusMessage;
};

struct HttpResponse {
    HttpResponseStartLine startLine;
    std::string headers;
    std::string body;
};

struct HttpRequestStartLine {
    std::string method;
    std::string path;
    std::string version;
};

struct HttpRequest {
    HttpRequestStartLine startLine;
    std::string headers;
    std::string body;
};

int getLineCount(const std::istringstream& requestStream) {
    int lineCount = 0;
    std::string line;
    std::istringstream tempStream(requestStream.str());
    while (std::getline(tempStream, line)) {
        lineCount++;
    }
    return lineCount;
}

std::string generateHttpResponseFromRequest(const HttpRequest& request) {
    std::ostringstream responseStream;
    HttpResponse response;

    response.startLine.version = "HTTP/1.1";
    response.startLine.statusCode = 200;
    response.startLine.statusMessage = "OK";

    response.headers = "Content-Type: text/plain\r\nContent-Length: " + std::to_string(request.body.size()) + "\r\n";
    response.body = "Echo: " + request.body;

    responseStream << response.startLine.version << " " << response.startLine.statusCode << " " << response.startLine.statusMessage << "\r\n";
    responseStream << response.headers << "\r\n";
    responseStream << response.body;

    return responseStream.str();
}

void parseHttpRequest(const std::string& request) {
    std::istringstream requestStream(request);
    std::string line;
    int lineCount = getLineCount(requestStream);
    cout << "Total Lines in Request: " << lineCount << "\n";
    bool firstLine = true;
    while (std::getline(requestStream, line) && line != "\r") {
        if (firstLine) {
            std::istringstream lineStream(line);
            HttpRequestStartLine startLine;
            lineStream >> startLine.method >> startLine.path >> startLine.version;
            cout << "Method: " << startLine.method << ", Path: " << startLine.path << ", Version: " << startLine.version << "\n";
            firstLine = false;
            continue;
        }
        cout << "Header Line: " << line << "\n";
    }
}

int startServer(int port) {
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    sockaddr_in serverAddress;
    serverAddress.sin_family = AF_INET;
    serverAddress.sin_port = htons(port);
    serverAddress.sin_addr.s_addr = INADDR_ANY;

    bind(serverSocket, (struct sockaddr*)&serverAddress, sizeof(serverAddress));
    listen(serverSocket, 5);

    cout << "Server is listening on port " << ntohs(serverAddress.sin_port) << "...\n";

    while (true) {
        int clientSocket = accept(serverSocket, nullptr, nullptr);
        char buffer[1024] {0};
        recv(clientSocket, buffer, sizeof(buffer), 0);

        HttpRequest request;
        request.body = buffer;

        std::string response = generateHttpResponseFromRequest(request);

        ssize_t bytesSent = send(clientSocket, response.c_str(), response.size(), 0);
        if (bytesSent < 0) {
            perror("Failed to send response to client.\n");
        } else {
            cout << "Sent " << bytesSent << " bytes back to client.\n";
        }

        buffer[0] = '\0';
        close(clientSocket);
    }
    close(serverSocket);
    return 0;
}

int main(int argc, char* argv[]) {
    int port = 8080;
    if (argc > 1) {
        port = std::stoi(argv[1]);
    }
    return startServer(port);
}

