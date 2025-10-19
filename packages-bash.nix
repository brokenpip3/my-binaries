{
  home-manager-remote = {
    pname = "home-manager-remote";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "git"
      "jq"
    ];
    srcDir = "productivity/nix-specific/home-manager-remote";
    libs = [ ];
    scripts = [ "home-manager-remote.sh" ];
  };

  util_uuid_machineid = {
    pname = "util_uuid_machineid";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
    ];
    srcDir = "system";
    libs = [ ];
    scripts = [ "util_uuid_machineid.sh" ];
  };

  util_audio_bluez_profile = {
    pname = "util_audio_bluez_profile";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "pulseaudio"
      "fzf"
    ];
    srcDir = "system";
    libs = [ ];
    scripts = [ "util_audio_bluez_profile.sh" ];
  };

  util_os_power = {
    pname = "util_os_power";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "rofi"
      "fzf"
    ];
    srcDir = "system";
    libs = [ ];
    scripts = [ "util_os_power.sh" ];
  };

  util_tmux_repo = {
    pname = "util_tmux_repo";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "tmux"
      "fzf"
    ];
    srcDir = "productivity";
    libs = [ ];
    scripts = [ "util_tmux_repo.sh" ];
  };

  util_run_xdotool = {
    pname = "util_run_xdotool";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "xdotool"
    ];
    srcDir = "productivity";
    libs = [ ];
    scripts = [ "util_run_xdotool.sh" ];
  };

  util_privacy_gpg_encrypt = {
    pname = "util_privacy_gpg_encrypt";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "gnupg"
    ];
    srcDir = "privacy";
    libs = [ ];
    scripts = [ "util_privacy_gpg_encrypt.sh" ];
  };

  util_run_all = {
    pname = "util_run_all";
    version = "0.1.1";
    propagatedBuildInputs = [
      "bash"
      "coreutils"
      "fzf"
    ];
    srcDir = "productivity";
    libs = [ ];
    scripts = [ "util_run_all.sh" ];
  };
}
