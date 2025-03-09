# Nix show flake
default:
    nix flake show

# Check the flake
check:
    nix flake check

# Start a Nix REPL
repl:
    nix repl -f flake:nixpkgs

# Update all flake inputs
up-all:
    @echo "> updating all flake inputs"
    nix flake update

# Update a specific flake input
up-one INPUT:
    @echo "> updating flake input {{INPUT}}"
    nix flake lock --update-input {{INPUT}}

# Clean git reflog
clean-git:
    git reflog expire --verbose --expire-unreachable=now --all
    git gc --prune=now


# Install pre-commit hooks
pre-commit:
    pre-commit install

# Build category security
build-security:
    nix build -L .#util_pass_bitwarden
    nix build -L .#tartufi

build-privacy:
    nix build -L .#util_privacy_telegram_cleanup

build-productivity:
    nix build -L .#task-sync-lib

# Build all packages
build: build-security build-privacy build-productivity

# Lint with ruff
lint:
    ruff check .
    ruff format .
