{
  description = "My binaries";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-24.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { ... }@inputs:
    inputs.flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = inputs.nixpkgs.legacyPackages.${system};
        pkgConfig = import ./packages-python.nix;

        pythonScriptGenPackage = config: pkgs: pkgs.python3Packages.buildPythonApplication {
          inherit (config) pname version;
          src = pkgs.lib.cleanSource ./${config.srcDir};
          format = "other";
          propagatedBuildInputs = map
            (pkg:
              pkgs.${pkg}
                or pkgs.python3Packages.${pkg}
            )
            config.propagatedBuildInputs;
          nativeCheckInputs = [ pkgs.python3Packages.pytest pkgs.python3Packages.pytest-asyncio pkgs.python3Packages.pytest-cov ];
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
          util_pass_bitwarden = pythonScriptGenPackage pkgConfig.util_pass_bitwarden pkgs;
          util_privacy_telegram_cleanup = pythonScriptGenPackage pkgConfig.util_privacy_telegram_cleanup pkgs;
          task-sync-lib = pythonScriptGenPackage pkgConfig.task-sync-lib pkgs;
          tartufi = pythonScriptGenPackage pkgConfig.tartufi pkgs;
          github-actions-hash = (import ./package-githubhash.nix { inherit pkgs; });
        };

        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            pre-commit
            ruff
            just
            deadnix
          ];
        };
      });
}
