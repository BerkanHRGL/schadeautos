#!/bin/bash

# Car Damage Finder - Setup Script
# This script helps you set up the Car Damage Finder application

set -e

echo "🚗 Car Damage Finder - Setup Script"
echo "======================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating environment file from template..."
    cp .env.example .env
    echo "✅ Environment file created at .env"
    echo "⚠️  Please edit .env file with your configuration before running the application"
else
    echo "✅ Environment file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs backup

# Generate a random secret key if not set
if ! grep -q "SECRET_KEY=your-super-secret-key-here" .env; then
    echo "🔑 Generating secure secret key..."
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/SECRET_KEY=your-super-secret-key-here/SECRET_KEY=$SECRET_KEY/" .env
    rm .env.bak
    echo "✅ Secret key generated and updated in .env"
fi

# Ask user for setup type
echo ""
echo "🛠️  Setup Options:"
echo "1) Development setup (with hot reloading)"
echo "2) Production setup (optimized)"
echo "3) Just create environment file (manual setup)"
echo ""
read -p "Choose an option (1-3): " setup_choice

case $setup_choice in
    1)
        echo "🚀 Setting up development environment..."
        docker-compose pull
        docker-compose build
        echo "✅ Development setup complete!"
        echo ""
        echo "To start the application:"
        echo "  docker-compose up -d"
        echo ""
        echo "Access the application at:"
        echo "  Frontend: http://localhost:3000"
        echo "  Backend API: http://localhost:8000"
        echo "  API Docs: http://localhost:8000/docs"
        ;;
    2)
        echo "🚀 Setting up production environment..."

        # Check if .env.prod exists, create from template if not
        if [ ! -f .env.prod ]; then
            cp .env.example .env.prod
            echo "📝 Created production environment file at .env.prod"
            echo "⚠️  Please edit .env.prod with production configuration"
        fi

        docker-compose -f docker-compose.prod.yml pull
        docker-compose -f docker-compose.prod.yml build
        echo "✅ Production setup complete!"
        echo ""
        echo "To start the application:"
        echo "  docker-compose -f docker-compose.prod.yml up -d"
        echo ""
        echo "Remember to:"
        echo "  1. Configure your domain in nginx-prod.conf"
        echo "  2. Set up SSL certificates"
        echo "  3. Update .env.prod with production settings"
        ;;
    3)
        echo "✅ Environment setup complete!"
        echo "Please configure .env file and run setup manually"
        ;;
    *)
        echo "❌ Invalid option selected"
        exit 1
        ;;
esac

echo ""
echo "📚 Next Steps:"
echo "1. Edit the .env file with your configuration"
echo "2. Start the application using docker-compose"
echo "3. Visit the frontend to create your account"
echo "4. Configure your car preferences in Settings"
echo ""
echo "📖 For detailed instructions, see README.md"
echo "🆘 For help, check the troubleshooting section in README.md"
echo ""
echo "🎉 Setup complete! Happy car hunting!"