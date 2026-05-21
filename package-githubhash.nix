{
  pkgs ? import <nixpkgs> { },
}:

pkgs.python3Packages.buildPythonApplication {
  pname = "github-actions-hash";
  version = "0.1.0";
  format = "pyproject";

  src = pkgs.fetchFromGitHub {
    owner = "brokenpip3";
    repo = "pre-commit-hooks";
    rev = "main";
    hash = "sha256-IdcUORdKVY6BgZydgQYumE0ch08aeQ4ahmQEQ/hVjzY=";
  };

  nativeBuildInputs = [
    pkgs.python3Packages.setuptools
  ];

  nativeCheckInputs = [ pkgs.python3Packages.pytest pkgs.python3Packages.pytest-cov ];

  postFixup = ''
    rm $out/nix-support/propagated-build-inputs
  '';

  checkPhase = ''
    pytest -s -v -k 'not test_process_files_no_workflows and not test_process_files_with_update'
  '';

  disabledTests = [
  "test_process_files_no_workflows"
  ];

  installPhase = ''
    mkdir -p $out/bin
    cp hooks/github_actions_hash.py $out/bin/util_ci_github_actions_hash
    chmod +x $out/bin/util_ci_github_actions_hash
  '';

  doCheck = true;
}
