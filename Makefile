# Makefile for Ansible MCP Servers

# Default values for environment variables
QUAY_ORG ?=
ANSIBLE_MCP_VERSION ?=
CONTAINER_RUNTIME ?= docker
MCP_GATEWAY_PORT ?= 8003
MCP_CONTROLLER_PORT ?= 8004
MCP_LIGHTSPEED_PORT ?= 8005

# Colors for terminal output
RED := \033[0;31m
NC := \033[0m # No Color

.PHONY: help build-all build-gateway build-controller run-gateway run-controller tag-and-push

.EXPORT_ALL_VARIABLES:

help:
	@echo "Makefile for Ansible MCP Servers"
	@echo "Available targets:"
	@echo "  help                 - Show this help message"
	@echo "  build-all            - Build the Ansible MCP Server images"
	@echo "  build-gateway        - Build the Ansible MCP Gateway Server image"
	@echo "  build-controller     - Build the Ansible MCP Controller Server image"
	@echo "  build-lightspeed     - Build the Ansible MCP Lightspeed Server image"
	@echo "  run-gateway          - Run an Ansible MCP Gateway Server container"
	@echo "  run-controller       - Run an Ansible MCP Controller Server container"
	@echo "  run-lightspeed       - Run an Ansible MCP Lightspeed Server container"
	@echo "  tag-and-push         - Tag and push the container image to quay.io"
	@echo ""
	@echo "Required Environment variables:"
	@echo "  ANSIBLE_MCP_VERSION             - Version tag for the image (default: $(ANSIBLE_MCP_VERSION))"
	@echo "  AAP_GATEWAY_URL                 - URL for an AAP Gateway instance"
	@echo "  AAP_CONTROLLER_SERVICE_URL      - URL for an AAP Controller instance"
	@echo "  AAP_LIGHTSPEED_SERVICE_URL      - URL for an AAP Lightspeed instance"
	@echo "  QUAY_ORG                        - Quay organization name (default: $(QUAY_ORG))"

build-all: build-gateway build-controller build-lightspeed

build-gateway:
	@echo "Building Ansible Gateway MCP Server image..."
	${CONTAINER_RUNTIME} build --build-arg PORT=${MCP_GATEWAY_PORT} -f ./aap_gateway_api_2_5/Containerfile -t ansible-mcp-gateway .
	@echo "Image $(RED)ansible-mcp-gateway$(NC) built successfully."

build-controller:
	@echo "Building Ansible Controller MCP Server image..."
	${CONTAINER_RUNTIME} build --build-arg PORT=${MCP_CONTROLLER_PORT} -f ./aap_controller_api_2_5/Containerfile -t ansible-mcp-controller .
	@echo "Image $(RED)ansible-mcp-controller$(NC) built successfully."

build-lightspeed:
	@echo "Building Ansible Lightspeed MCP Server image..."
	${CONTAINER_RUNTIME} build --build-arg PORT=${MCP_LIGHTSPEED_PORT} -f ./aap_lightspeed_api_1_0/Containerfile -t ansible-mcp-lightspeed .
	@echo "Image $(RED)ansible-mcp-lightspeed$(NC) built successfully."

# Pre-check for required environment variables
check-env-gateway-url:
	@if [ -z "$(AAP_GATEWAY_URL)" ]; then \
		echo "$(RED)Error: AAP_GATEWAY_URL is required but not set$(NC)"; \
		exit 1; \
	fi

check-env-controller-service-url:
	@if [ -z "$(AAP_CONTROLLER_SERVICE_URL)" ]; then \
		echo "$(RED)Error: AAP_CONTROLLER_SERVICE_URL is required but not set$(NC)"; \
		exit 1; \
	fi

check-env-lightspeed-service-url:
	@if [ -z "$(AAP_LIGHTSPEED_SERVICE_URL)" ]; then \
		echo "$(RED)Error: AAP_LIGHTSPEED_SERVICE_URL is required but not set$(NC)"; \
		exit 1; \
	fi

run-gateway: check-env-gateway-url
	@echo "Running Ansible Gateway MCP Server container..."
	@echo "Using AAP_GATEWAY_URL: $(AAP_GATEWAY_URL)"
	${CONTAINER_RUNTIME} run \
		-p ${MCP_GATEWAY_PORT}:${MCP_GATEWAY_PORT} \
		--env AAP_GATEWAY_URL=${AAP_GATEWAY_URL} \
		--env HOST=0.0.0.0 \
		--env PORT=${MCP_GATEWAY_PORT} \
		ansible-mcp-gateway

run-controller: check-env-gateway-url check-env-controller-service-url
	@echo "Running Ansible Controller MCP Server container..."
	@echo "Using AAP_GATEWAY_URL: $(AAP_GATEWAY_URL)"
	@echo "Using AAP_CONTROLLER_SERVICE_URL: $(AAP_CONTROLLER_SERVICE_URL)"
	${CONTAINER_RUNTIME} run \
		-p ${MCP_CONTROLLER_PORT}:${MCP_CONTROLLER_PORT} \
		--env AAP_GATEWAY_URL=${AAP_GATEWAY_URL} \
		--env AAP_SERVICE_URL=${AAP_CONTROLLER_SERVICE_URL} \
		--env HOST=0.0.0.0 \
		--env PORT=${MCP_CONTROLLER_PORT} \
		ansible-mcp-controller

run-lightspeed: check-env-gateway-url check-env-lightspeed-service-url
	@echo "Running Ansible Lightspeed MCP Server container..."
	@echo "Using AAP_GATEWAY_URL: $(AAP_GATEWAY_URL)"
	@echo "Using AAP_LIGHTSPEED_SERVICE_URL: $(AAP_LIGHTSPEED_SERVICE_URL)"
	${CONTAINER_RUNTIME} run \
		-p ${MCP_LIGHTSPEED_PORT}:${MCP_LIGHTSPEED_PORT} \
		--env AAP_GATEWAY_URL=${AAP_GATEWAY_URL} \
		--env AAP_SERVICE_URL=${AAP_LIGHTSPEED_SERVICE_URL} \
		--env HOST=0.0.0.0 \
		--env PORT=${MCP_LIGHTSPEED_PORT} \
		ansible-mcp-lightspeed

clean:
	@echo "Cleaning up..."
	@echo "Removing ansible-mcp-gateway images..."
	${CONTAINER_RUNTIME} rmi -f $$(${CONTAINER_RUNTIME} images -a -q --filter reference=ansible-mcp-gateway) || true
	@echo "Removing ansible-mcp-controller images..."
	${CONTAINER_RUNTIME} rmi -f $$(${CONTAINER_RUNTIME} images -a -q --filter reference=ansible-mcp-controller) || true
	@echo "Removing ansible-mcp-lightspeed images..."
	${CONTAINER_RUNTIME} rmi -f $$(${CONTAINER_RUNTIME} images -a -q --filter reference=ansible-mcp-lightspeed) || true
	@echo "Clean-up complete."

# Pre-check required environment variables for tag-and-push
check-env-tag-and-push:
	@if [ -z "$(QUAY_ORG)" ]; then \
		echo "$(RED)Error: QUAY_ORG is required but not set$(NC)"; \
		exit 1; \
	fi
	@if [ -z "$(ANSIBLE_MCP_VERSION)" ]; then \
		echo "$(RED)Error: ANSIBLE_MCP_VERSION is required but not set$(NC)"; \
		exit 1; \
	fi

tag-and-push: check-env-tag-and-push
	@echo "Logging in to quay.io..."
	@echo "Please enter your quay.io credentials when prompted"
	${CONTAINER_RUNTIME} login quay.io

	@echo "Tagging image ansible-mcp-gateway:$(ANSIBLE_MCP_VERSION)"
	${CONTAINER_RUNTIME} tag ansible-mcp-gateway:latest quay.io/$(QUAY_ORG)/ansible-mcp-gateway:$(ANSIBLE_MCP_VERSION)
	@echo "Pushing image to quay.io..."
	${CONTAINER_RUNTIME} push quay.io/$(QUAY_ORG)/ansible-mcp-gateway:$(ANSIBLE_MCP_VERSION)
	@echo "Image successfully pushed to quay.io/$(QUAY_ORG)/ansible-mcp-gateway:$(ANSIBLE_MCP_VERSION)"

	@echo "Tagging image ansible-mcp-controller:$(ANSIBLE_MCP_VERSION)"
	${CONTAINER_RUNTIME} tag ansible-mcp-controller:latest quay.io/$(QUAY_ORG)/ansible-mcp-controller:$(ANSIBLE_MCP_VERSION)
	@echo "Pushing image to quay.io..."
	${CONTAINER_RUNTIME} push quay.io/$(QUAY_ORG)/ansible-mcp-controller:$(ANSIBLE_MCP_VERSION)
	@echo "Image successfully pushed to quay.io/$(QUAY_ORG)/ansible-mcp-controller:$(ANSIBLE_MCP_VERSION)"

	@echo "Tagging image ansible-mcp-lightspeed:$(ANSIBLE_MCP_VERSION)"
	${CONTAINER_RUNTIME} tag ansible-mcp-lightspeed:latest quay.io/$(QUAY_ORG)/ansible-mcp-lightspeed:$(ANSIBLE_MCP_VERSION)
	@echo "Pushing image to quay.io..."
	${CONTAINER_RUNTIME} push quay.io/$(QUAY_ORG)/ansible-mcp-lightspeed:$(ANSIBLE_MCP_VERSION)
	@echo "Image successfully pushed to quay.io/$(QUAY_ORG)/ansible-mcp-lightspeed:$(ANSIBLE_MCP_VERSION)"
