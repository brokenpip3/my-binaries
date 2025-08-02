{
  description = "My binaries";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-25.05";
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
            buildInputs = map (pkg: pkgs.${pkg}) config.propagatedBuildInputs ++ [ pkgs.makeWrapper ];
            nativeCheckInputs = [
              (pkgs.bats.withLibraries (p: [
                p.bats-support
                p.bats-assert
              ]))
            ];
            patchPhase = ''
              patchShebangs .
            '';
            doCheck = true;
            checkPhase = ''
              runHook preCheck
                if [ -f "${config.pname}.bats" ]; then
                  bats -F tap --verbose-run "${config.pname}.bats"
                else
                  echo "No ${config.pname}.bats file found - skipping tests"
                fi
              ${pkgs.lib.concatMapStrings (script: ''
                ${pkgs.shellcheck-minimal}/bin/shellcheck ${builtins.baseNameOf script}
              '') config.scripts}
              runHook postCheck
            '';
            installPhase = ''
              runHook preInstall
              mkdir -p $out/bin
              ${pkgs.lib.concatMapStrings (script: ''
                target=$out/bin/$(basename ${script})
                install -Dm755 ${script} $target
                wrapProgram $target --prefix PATH : ${
                  pkgs.lib.makeBinPath (map (pkg: pkgs.${pkg}) config.propagatedBuildInputs)
                }
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
            propagatedBuildInputs = [
              pkgs.python3
            ] ++ map (pkg: pkgs.${pkg} or pkgs.python3Packages.${pkg}) config.propagatedBuildInputs;

            nativeCheckInputs = [
              pkgs.python3Packages.pytest
              pkgs.python3Packages.pytest-asyncio
              pkgs.python3Packages.pytest-cov
            ];
            postFixup = ''
              rm $out/nix-support/propagated-build-inputs
            '';
            checkPhase = ''
              runHook preCheck
              pytest -s -v; pytest --cov=. --cov-report=term-missing
              runHook postCheck
            '';
            installPhase = ''
              runHook preInstall
              mkdir -p $out/bin
              ${pkgs.lib.concatMapStrings (lib: ''
                install -Dm644 ${lib} $out/bin/${builtins.baseNameOf lib}
              '') config.libs}
              ${pkgs.lib.concatMapStrings (script: ''
                base_name=$(basename ${script} .py)
                install -Dm755 ${script} $out/bin/$base_name
              '') config.scripts}
              runHook postInstall
            '';
          };

        bashPackages = pkgs.lib.mapAttrs (_: config: bashScriptGenPackage config pkgs) pkgConfigBash;
        pythonPackages = pkgs.lib.mapAttrs (_: config: pythonScriptGenPackage config pkgs) pkgConfigPython;

        perPackageDevShells =
         let
           mkDevShell =
             name: config:
             let
               isPyPkg = pkg: pkgs.python3Packages ? "${pkg}";
               pythonPkgs = map (pkg: pkgs.python3Packages.${pkg})
                 (builtins.filter isPyPkg config.propagatedBuildInputs);
               otherPkgs = map (pkg: pkgs.${pkg})
                 (builtins.filter (pkg: !(isPyPkg pkg)) config.propagatedBuildInputs);
               pythonEnv = pkgs.python3.withPackages (_: pythonPkgs);
             in
             pkgs.mkShell {
               inherit name;
               packages = [ pythonEnv ] ++ otherPkgs;
             };
         in
         pkgs.lib.mapAttrs mkDevShell pkgConfigPython;
      in
      {
        formatter = pkgs.nixfmt-rfc-style;

        packages =
          bashPackages
          // pythonPackages
          // {
            github-actions-hash = (import ./package-githubhash.nix { inherit pkgs; });
          };

        devShells = perPackageDevShells // {
          default = pkgs.mkShell {
            packages = with pkgs; [
              pre-commit
              ruff
              just
              deadnix
              shellcheck-minimal
              (bats.withLibraries (p: [
                p.bats-support
                p.bats-assert
              ]))
            ];
          };
        };
      }
    );
}
