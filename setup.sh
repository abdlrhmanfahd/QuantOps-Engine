#!/bin/bash

set -e 

echo " -- Update the system package -- "
sudo dnf update -y

echo " -- Checking if Docker exitst & Try to install it -- "

if ! command -v docker &> /dev/null; then 
	echo " Docker is not installed, in progress to install it through dnf.. "
	sudo dnf install docker -y
	sudo systemctl start docker
	sudo systemctl enable docker
else
	echo " Docker is already installed "
fi

if ! command -v docker-compose &> /dev/null; then
	echo " In progress to install Docker Compose "
	sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/bin/docker-compose
	sudo chmod -x /usr/local/bin/docker-compose
fi

echo "-- Verifying the .env --"
if [ ! -f .env ]; then
	echo ".env file isn't exists, please make it and feed it with the necessary keys before excuting"
	exit 1
fi

echo "-- Running the IaC --"
sudo docker-compose down -remove-orphans
sudo docker-compose up -d --build

echo "-- Deployment Done! --"
sudo docker-compose ps
