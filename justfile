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

# Lint with ruff
lint:
    ruff check .
    ruff format .

# Install pre-commit hooks
pre-commit:
    pre-commit install

# Build category security
build-security:
    nix build -L .#util_pass_bitwarden
    nix build -L .#tartufi

# Build category privacy
build-privacy:
    nix build -L .#util_privacy_telegram_cleanup
    nix build -L .#util_privacy_gpg_encrypt

# Build category productivity
build-productivity:
    nix build -L .#task-sync-lib
    nix build -L .#home-manager-remote
    nix build -L .#util_nix_doc_module
    nix build -L .#util_run_xdotool
    nix build -L .#util_tmux_repo
    nix build -L .#util_run_all
    nix build -L .#util_ai_mcp_taskwarrior
    nix build -L .#util_ai_mcp_googlecalendar

# Build category system
build-system:
    nix build -L .#util_uuid_machineid
    nix build -L .#util_audio_bluez_profile
    nix build -L .#util_os_power

# Build category ci
build-ci:
    nix build -L .#util_ci_changedfiles

build-docker:
    #nix build -L .#dockerimg_util_ai_mcp_taskwarrior
    nix build -L .#dockerimg_util_ai_mcp_googlecalendar

# Build github-actions-hash
build-githubhash:
    nix build -L .#github-actions-hash

# Build all packages
build: build-security build-privacy build-productivity build-system build-githubhash build-ci build-docker
