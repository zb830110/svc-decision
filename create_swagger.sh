#!/bin/bash
PORT=5000

# Start service
echo "Starting service"
cd ./src || exit
python3 fastapp.py &
SERVER_PID=$!

# Wait for server to start up
echo "Waiting for service to start up"
sleep 5

# Download OpenAPI
cd ./../swagger_generator || exit
echo "Downloading openapi.json"
curl -X GET http://localhost:$PORT/openapi.json --output openapi.json
echo "Shutting down server"
kill $SERVER_PID

# Create docker for building swagger
echo "Building docker image for swagger generator"
docker build -t swagger-generator .

echo "Removing existing swagger.json"
rm -f ../swagger.json

# Create swagger.json
echo "Generating swagger.json"
docker run -it -v "$(pwd)":/input swagger-generator > ../swagger.json

echo "Clean up"
rm -f openapi.json

# Return to directory
cd .. || exit
echo "Finished"
