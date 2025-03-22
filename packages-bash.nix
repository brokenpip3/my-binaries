{
  home-manager-remote = {
    pname = "home-manager-remote";
    version = "0.1.0";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "git"
      "jq"
    ];
    srcDir = "productivity/nix-specific/home-manager-remote";
    libs = [];
    scripts = [ "home-manager-remote.sh" ];
  };
}
