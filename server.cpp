#include <iostream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <fstream>
#include <sstream>
#include <cstring>
#include <algorithm>
#include <cctype>

using std::cout;
using std::cin;


int startServer(int port, int backlog) {
    int serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    if (setsockopt(serverSocket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        close(serverSocket);
        return 1;
    }

    sockaddr_in serverAddress;
    std::memset(&serverAddress, 0, sizeof(serverAddress));
    serverAddress.sin_family = AF_INET;
    serverAddress.sin_port = htons(port);
    serverAddress.sin_addr.s_addr = INADDR_ANY;

    if (bind(serverSocket, (struct sockaddr*)&serverAddress, sizeof(serverAddress)) < 0) {
        perror("bind");
        close(serverSocket);
        return 1;
    }

    if (listen(serverSocket, backlog) < 0) {
        perror("listen");
        close(serverSocket);
        return 1;
    }

    cout << "Server is listening on port " << port << "...\n";

    while (true) {
        int clientSocket = accept(serverSocket, nullptr, nullptr);
        if (clientSocket < 0) {
            perror("accept");
            continue;
        }

        std::string request;
        char buf[4096];
        ssize_t n;
        size_t headerEnd = std::string::npos;
        int contentLength = 0;

        while ((n = recv(clientSocket, buf, sizeof(buf), 0)) > 0) {
            request.append(buf, (size_t)n);
            if (headerEnd == std::string::npos) {
                headerEnd = request.find("\r\n\r\n");
                if (headerEnd != std::string::npos) {
                    std::string headers = request.substr(0, headerEnd);
                    std::string lower = headers;
                    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
                    size_t pos = lower.find("content-length:");
                    if (pos != std::string::npos) {
                        pos += strlen("content-length:");
                        while (pos < lower.size() && isspace((unsigned char)lower[pos])) ++pos;
                        size_t endpos = pos;
                        while (endpos < lower.size() && isdigit((unsigned char)lower[endpos])) ++endpos;
                        if (endpos > pos) {
                            contentLength = std::stoi(lower.substr(pos, endpos - pos));
                        }
                    }
                }
            }
            if (headerEnd != std::string::npos) {
                size_t totalNeeded = headerEnd + 4 + (size_t)contentLength;
                if (request.size() >= totalNeeded) break;
            }
        }

        if (n < 0) {
            perror("recv");
            close(clientSocket);
            continue;
        }

        size_t firstLineEnd = request.find("\r\n");
        if (firstLineEnd == std::string::npos) {
            firstLineEnd = request.find("\n");
        }
        std::string requestLine = request.substr(0, firstLineEnd);
        
        std::istringstream iss(requestLine);
        std::string method, path, version;
        iss >> method >> path >> version;
        
        cout << "Request: " << method << " " << path << " " << version << "\n";

        std::string body;
        if (headerEnd != std::string::npos) {
            size_t bodyStart = headerEnd + 4;
            if (bodyStart < request.size()) {
                body = request.substr(bodyStart, contentLength);
            }
        }

        std::string responseBody = "Echo: " + body;
        std::ostringstream resp;
        resp << "HTTP/1.1 200 OK\r\n";
        resp << "Content-Type: text/plain\r\n";
        resp << "Content-Length: " << responseBody.size() << "\r\n";
        resp << "Connection: close\r\n";
        resp << "\r\n";
        resp << responseBody;
        std::string response = resp.str();

        ssize_t totalSent = 0;
        ssize_t toSend = (ssize_t)response.size();
        const char* sendPtr = response.c_str();
        while (totalSent < toSend) {
            ssize_t sent = send(clientSocket, sendPtr + totalSent, toSend - totalSent, 0);
            if (sent < 0) {
                perror("send");
                break;
            }
            totalSent += sent;
        }
        cout << "Sent " << totalSent << " bytes back to client.\n";

        close(clientSocket);
    }
    close(serverSocket);
    return 0;
}

int main(int argc, char* argv[]) {
    int port = 8080;
    int backlog = 5;

    if (argc > 1) {
        port = std::stoi(argv[1]);
        if (argc > 2) {
            backlog = std::stoi(argv[2]);
        }
    }

    return startServer(port, backlog);
}

