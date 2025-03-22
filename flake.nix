{
  description = "My binaries";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { ... }@inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = inputs.nixpkgs.legacyPackages.${system};
        pkgConfigPython = import ./packages-python.nix;
        pkgConfigBash = import ./packages-bash.nix;

        bashScriptGenPackage =
          config: pkgs:
          pkgs.stdenv.mkDerivation {
            inherit (config) pname version;
            src = pkgs.lib.cleanSource ./${config.srcDir};
            buildInputs = map (pkg: pkgs.${pkg}) config.propagatedBuildInputs;
            nativeCheckInputs = [
              (pkgs.bats.withLibraries (p: [
                p.bats-support
                p.bats-assert
                p.bats-file
                p.bats-detik
              ]))
            ];
            doCheck = true;
            checkPhase = ''
              bats -F tap --verbose-run .
            '';
            installPhase = ''
            runHook preInstall
              mkdir -p $out/bin
              ${pkgs.lib.concatMapStrings (script: ''
                install -Dm755 ${script} $out/bin/${builtins.baseNameOf script}
              '') config.scripts}
            runHook postInstall
            '';
          };

        pythonScriptGenPackage =
          config: pkgs:
          pkgs.python3Packages.buildPythonApplication {
            inherit (config) pname version;
            src = pkgs.lib.cleanSource ./${config.srcDir};
            format = "other";
            propagatedBuildInputs = map (
              pkg: pkgs.${pkg} or pkgs.python3Packages.${pkg}
            ) config.propagatedBuildInputs;
            nativeCheckInputs = [
              pkgs.python3Packages.pytest
              pkgs.python3Packages.pytest-asyncio
              pkgs.python3Packages.pytest-cov
            ];
            postFixup = ''
              rm $out/nix-support/propagated-build-inputs
            '';
            checkPhase = ''
              pytest -s -v; pytest --cov=. --cov-report=term-missing
            '';
            installPhase = ''
              mkdir -p $out/bin
              ${pkgs.lib.concatMapStrings (lib: ''
                install -Dm644 ${lib} $out/bin/${builtins.baseNameOf lib}
              '') config.libs}
              ${pkgs.lib.concatMapStrings (script: ''
                base_name=$(basename ${script} .py)
                install -Dm755 ${script} $out/bin/$base_name
              '') config.scripts}
            '';
          };

      in

      {
        formatter = pkgs.nixfmt-rfc-style;

        packages = {
          github-actions-hash = (import ./package-githubhash.nix { inherit pkgs; });
          home-manager-remote = bashScriptGenPackage pkgConfigBash.home-manager-remote pkgs;
          tartufi = pythonScriptGenPackage pkgConfigPython.tartufi pkgs;
          task-sync-lib = pythonScriptGenPackage pkgConfigPython.task-sync-lib pkgs;
          util_pass_bitwarden = pythonScriptGenPackage pkgConfigPython.util_pass_bitwarden pkgs;
          util_privacy_telegram_cleanup = pythonScriptGenPackage pkgConfigPython.util_privacy_telegram_cleanup pkgs;
          util_nix_doc_module = pythonScriptGenPackage pkgConfigPython.util_nix_doc_module pkgs;
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            pre-commit
            ruff
            just
            deadnix
          ];
        };
      }
    );
}
