#!/bin/bash
sudo docker compose down
sudo docker compose up -d --build

echo "Going to sleep for 20 seconds Good night~"
sleep 20
echo "Good morning!"
sleep 2
sudo docker logs -f governance-agent
