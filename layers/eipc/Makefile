.PHONY: build build-all build-linux build-darwin build-windows test clean fmt vet lint release-binaries

BINARY_SERVER = eipc-server
BINARY_CLIENT = eipc-client
VERSION       ?= 0.2.0
LDFLAGS       = -s -w
BUILD_DIR     = bin

# Default: build for current platform
build:
	go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER) ./cmd/eipc-server
	go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT) ./cmd/eipc-client

# Cross-compile for all major platforms
build-all: build-linux build-darwin build-windows

build-linux:
	GOOS=linux GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-linux-amd64       ./cmd/eipc-server
	GOOS=linux GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-linux-amd64       ./cmd/eipc-client
	GOOS=linux GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-linux-arm64       ./cmd/eipc-server
	GOOS=linux GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-linux-arm64       ./cmd/eipc-client
	GOOS=linux GOARCH=arm   GOARM=7 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-linux-armv7 ./cmd/eipc-server
	GOOS=linux GOARCH=arm   GOARM=7 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-linux-armv7 ./cmd/eipc-client

build-darwin:
	GOOS=darwin GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-darwin-amd64 ./cmd/eipc-server
	GOOS=darwin GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-darwin-amd64 ./cmd/eipc-client
	GOOS=darwin GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-darwin-arm64 ./cmd/eipc-server
	GOOS=darwin GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-darwin-arm64 ./cmd/eipc-client

build-windows:
	GOOS=windows GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-windows-amd64.exe ./cmd/eipc-server
	GOOS=windows GOARCH=amd64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-windows-amd64.exe ./cmd/eipc-client
	GOOS=windows GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_SERVER)-windows-arm64.exe ./cmd/eipc-server
	GOOS=windows GOARCH=arm64 go build -ldflags "$(LDFLAGS)" -o $(BUILD_DIR)/$(BINARY_CLIENT)-windows-arm64.exe ./cmd/eipc-client

test:
	go test -race -v ./...

clean:
	go clean ./...
	rm -rf $(BUILD_DIR)/

fmt:
	gofmt -w .

vet:
	go vet ./...

lint: vet
	@echo "Lint checks passed"

# Package release archives per platform
release-binaries: build-all
	@mkdir -p $(BUILD_DIR)/release
	@cd $(BUILD_DIR) && tar czf release/eipc-$(VERSION)-linux-amd64.tar.gz   $(BINARY_SERVER)-linux-amd64   $(BINARY_CLIENT)-linux-amd64
	@cd $(BUILD_DIR) && tar czf release/eipc-$(VERSION)-linux-arm64.tar.gz   $(BINARY_SERVER)-linux-arm64   $(BINARY_CLIENT)-linux-arm64
	@cd $(BUILD_DIR) && tar czf release/eipc-$(VERSION)-linux-armv7.tar.gz   $(BINARY_SERVER)-linux-armv7   $(BINARY_CLIENT)-linux-armv7
	@cd $(BUILD_DIR) && tar czf release/eipc-$(VERSION)-darwin-amd64.tar.gz  $(BINARY_SERVER)-darwin-amd64  $(BINARY_CLIENT)-darwin-amd64
	@cd $(BUILD_DIR) && tar czf release/eipc-$(VERSION)-darwin-arm64.tar.gz  $(BINARY_SERVER)-darwin-arm64  $(BINARY_CLIENT)-darwin-arm64
	@cd $(BUILD_DIR) && zip -q  release/eipc-$(VERSION)-windows-amd64.zip    $(BINARY_SERVER)-windows-amd64.exe $(BINARY_CLIENT)-windows-amd64.exe
	@cd $(BUILD_DIR) && zip -q  release/eipc-$(VERSION)-windows-arm64.zip    $(BINARY_SERVER)-windows-arm64.exe $(BINARY_CLIENT)-windows-arm64.exe
	@echo "Release archives created in $(BUILD_DIR)/release/"
