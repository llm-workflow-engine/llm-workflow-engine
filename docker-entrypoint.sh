#!/usr/bin/env bash

echo "----- Please follow these steps -----"
echo '1) Run command `docker exec -it lwe-container /bin/bash -c \"lwe\"`'
echo '2) Follow the instructions to create the first user'
echo '3) Have a nice chat'

# Keep a process running in the foreground
exec /bin/bash -c "trap : TERM INT; sleep infinity & wait"
