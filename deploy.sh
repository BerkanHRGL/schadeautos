#!/bin/bash

# DigitalOcean Deployment Script for SchadeAutos
set -e

echo "🚀 Starting DigitalOcean deployment for SchadeAutos..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
echo "📋 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/schadeautos
cd /opt/schadeautos

# Clone or copy your application
echo "📥 Note: You'll need to upload your application files here"
echo "📍 Current directory: $(pwd)"

# Create data directory for SQLite
mkdir -p data

# Set permissions
sudo chown -R $USER:$USER /opt/schadeautos

echo "✅ Server setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Upload your application files to /opt/schadeautos"
echo "2. Update REACT_APP_API_URL in docker-compose.simple.yml with your server IP"
echo "3. Run: docker-compose -f docker-compose.simple.yml up -d --build"
echo ""
echo "🌐 Your app will be available at:"
echo "   Frontend: http://YOUR_SERVER_IP"
echo "   Backend API: http://YOUR_SERVER_IP:8000"