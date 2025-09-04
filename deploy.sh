#!/bin/bash

# Soloist Backend Deployment Script
# This script helps deploy the application to different environments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_IMAGE="soloist-backend"
DOCKER_TAG=${DOCKER_TAG:-latest}
ENVIRONMENT=${ENVIRONMENT:-production}
PROJECT_NAME="soloist"

# Functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}           Soloist Backend Deployment           ${NC}"
    echo -e "${BLUE}================================================${NC}"
    echo ""
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check if .env.prod exists for production
    if [ "$ENVIRONMENT" = "production" ] && [ ! -f ".env.prod" ]; then
        log_error ".env.prod file not found. Please copy .env.prod.example and fill in values."
        exit 1
    fi
    
    log_info "All requirements satisfied ✓"
}

build_image() {
    log_info "Building Docker image..."
    
    docker build -t "${DOCKER_IMAGE}:${DOCKER_TAG}" .
    
    if [ $? -eq 0 ]; then
        log_info "Docker image built successfully ✓"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

run_tests() {
    log_info "Running tests..."
    
    # Build test image
    docker build -t "${DOCKER_IMAGE}:test" --target dependencies .
    
    # Run tests in container
    docker run --rm \
        -v "$(pwd):/app" \
        -w /app \
        "${DOCKER_IMAGE}:test" \
        python -m pytest tests/ -v
    
    if [ $? -eq 0 ]; then
        log_info "All tests passed ✓"
    else
        log_error "Tests failed"
        exit 1
    fi
}

deploy_development() {
    log_info "Deploying to development environment..."
    
    # Use regular docker-compose for development
    docker-compose down --remove-orphans
    docker-compose up -d --build
    
    log_info "Development deployment complete ✓"
    log_info "Application running at: http://localhost:8000"
    log_info "API Documentation: http://localhost:8000/docs"
}

deploy_production() {
    log_info "Deploying to production environment..."
    
    # Use production docker-compose
    docker-compose -f docker-compose.prod.yml down --remove-orphans
    docker-compose -f docker-compose.prod.yml up -d --build
    
    log_info "Production deployment complete ✓"
    log_info "Application running at: http://localhost:8000"
}

check_health() {
    log_info "Checking application health..."
    
    # Wait for app to start
    sleep 10
    
    # Check health endpoint
    for i in {1..30}; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            log_info "Application is healthy ✓"
            return 0
        fi
        
        log_info "Waiting for application to be ready... (attempt $i/30)"
        sleep 2
    done
    
    log_error "Application failed to become healthy"
    return 1
}

backup_database() {
    log_info "Creating database backup..."
    
    BACKUP_DIR="backups"
    BACKUP_FILE="${BACKUP_DIR}/backup_$(date +%Y%m%d_%H%M%S).sql"
    
    mkdir -p "$BACKUP_DIR"
    
    # This would need to be customized based on your database setup
    log_warn "Database backup functionality needs to be implemented for your specific setup"
}

rollback() {
    log_info "Rolling back deployment..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml down
    else
        docker-compose down
    fi
    
    log_info "Rollback complete ✓"
}

show_logs() {
    log_info "Showing application logs..."
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml logs -f app
    else
        docker-compose logs -f app
    fi
}

show_status() {
    log_info "Application status:"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        docker-compose -f docker-compose.prod.yml ps
    else
        docker-compose ps
    fi
}

show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  deploy     Deploy the application"
    echo "  build      Build Docker image only"
    echo "  test       Run tests"
    echo "  health     Check application health"
    echo "  logs       Show application logs"
    echo "  status     Show service status"
    echo "  backup     Create database backup"
    echo "  rollback   Rollback deployment"
    echo ""
    echo "Environment Variables:"
    echo "  ENVIRONMENT  Target environment (development|production) [default: production]"
    echo "  DOCKER_TAG   Docker image tag [default: latest]"
    echo ""
    echo "Examples:"
    echo "  $0 deploy                    # Deploy to production"
    echo "  ENVIRONMENT=development $0 deploy  # Deploy to development"
    echo "  $0 test                      # Run tests"
    echo "  $0 logs                      # Show logs"
}

# Main execution
print_header

case "${1:-}" in
    "deploy")
        check_requirements
        build_image
        
        if [ "${RUN_TESTS:-true}" = "true" ]; then
            run_tests
        fi
        
        if [ "$ENVIRONMENT" = "production" ]; then
            deploy_production
        else
            deploy_development
        fi
        
        check_health
        ;;
    "build")
        check_requirements
        build_image
        ;;
    "test")
        check_requirements
        run_tests
        ;;
    "health")
        check_health
        ;;
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "backup")
        backup_database
        ;;
    "rollback")
        rollback
        ;;
    "help"|"-h"|"--help")
        show_usage
        ;;
    *)
        log_error "Unknown command: ${1:-}"
        echo ""
        show_usage
        exit 1
        ;;
esac