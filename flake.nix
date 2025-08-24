{
  description = "My binaries";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  };

  outputs =
    { ... }@inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = inputs.nixpkgs.legacyPackages.${system};
        unstable = inputs.nixpkgs-unstable.legacyPackages.${system};

        pythonVersion = "python312";
        pyPkgs = pkgs.${pythonVersion}.pkgs;
        unstabPyPkgs = unstable.${pythonVersion}.pkgs;

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
                  echo "no ${config.pname}.bats file found - skipping tests"
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
          let
            resolve =
              name:
              let
                stable = pyPkgs.${name} or null;
                unstab = unstabPyPkgs.${name} or null;
              in
              if config.useUnstable or false then unstab else stable;

            pyWorld = if config.useUnstable or false then unstabPyPkgs else pyPkgs;
          in
          pyWorld.buildPythonApplication {
            inherit (config) pname version;
            src = pkgs.lib.cleanSource ./${config.srcDir};
            format = "other";
            propagatedBuildInputs = map resolve config.propagatedBuildInputs;
            nativeCheckInputs = [
              pyWorld.pytest
              pyWorld.pytest-asyncio
              pyWorld.pytest-cov
            ];
            postFixup = ''rm $out/nix-support/propagated-build-inputs'';
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
        pythonPackages = pkgs.lib.mapAttrs (
          _: config: pythonScriptGenPackage config pkgs unstable
        ) pkgConfigPython;

        pythonDockerImages = pkgs.lib.mapAttrs' (
          name: config:
          if config.docker or false then
            pkgs.lib.nameValuePair "dockerimg_${name}" (
              pkgs.dockerTools.buildImage {
                name = "ghcr.io/brokenpip3/${name}";
                tag = config.version;
                created = "now";
                copyToRoot = pythonPackages.${name};
                config = {
                  Labels = {
                    maintainer = "brokenpip3";
                    description = "docker image for ${name}";
                    version = config.version;
                    "org.opencontainers.image.authors" = "brokenpip3 <brokenpip3@gmail.com>";
                    "org.opencontainers.image.title" = name;
                    "org.opencontainers.image.description" = "generated python app image";
                    "org.opencontainers.image.url" = "ghcr.io/brokenpip3/${name}";
                    "org.opencontainers.image.source" = "https://github.com/brokenpip3/${name}";
                  };
                };
              }
            )
          else
            pkgs.lib.nameValuePair "dockerimg_${name}" null
        ) pkgConfigPython;

        perPackageDevShells =
          let
            mkDevShell =
              name: config:
              let
                resolve =
                  name:
                  let
                    stable = pyPkgs.${name} or null;
                    unstab = unstabPyPkgs.${name} or null;
                  in
                  if config.useUnstable or false then unstab else stable;

                isPyPkg = name: pyPkgs ? "${name}" || unstabPyPkgs ? "${name}";

                pythonPkgs = map resolve (builtins.filter isPyPkg config.propagatedBuildInputs);
                otherPkgs = map resolve (builtins.filter (pkg: !(isPyPkg pkg)) config.propagatedBuildInputs);
                pythonEnv =
                  if config.useUnstable or false then
                    unstable.${pythonVersion}.withPackages (_: pythonPkgs)
                  else
                    pkgs.${pythonVersion}.withPackages (_: pythonPkgs);
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
          // (pkgs.lib.filterAttrs (_: v: v != null) pythonDockerImages)
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
