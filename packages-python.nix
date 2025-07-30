{
  util_pass_bitwarden = {
    pname = "util_pass_bitwarden";
    version = "0.3.0";
    propagatedBuildInputs = [
      "bitwarden-cli"
    ];
    srcDir = "security/pass-bitwarden-sync";
    libs = [];
    scripts = [ "util_pass_bitwarden.py" ];
  };

  util_privacy_telegram_cleanup = {
    pname = "util_privacy_telegram_cleanup";
    version = "0.3.0";
    propagatedBuildInputs = [
      "telethon"
    ];
    srcDir = "privacy/telegram-cleanup";
    libs = [];
    scripts = [ "util_privacy_telegram_cleanup.py" ];
  };

  task-sync-lib = {
    pname = "task-sync-lib";
    version = "0.3.1";
    propagatedBuildInputs = [
      "requests"
    ];
    srcDir = "productivity/task-sync-lib";
    libs = [
      "_logseq.py"
      "_tasklib.py"
      "_youtrack.py"
    ];
    scripts = [
      "util_task_logseq_sync.py"
      "util_task_youtrack_sync.py"
      "on-add-logseq.py"
      "on-modify-logseq.py"
      "on-modify-youtrack.py"
    ];
  };

  tartufi = {
    pname = "tartufi";
    version = "0.1.0";
    propagatedBuildInputs = [
      "requests"
    ];
    srcDir = "security/tartufi";
    libs = [];
    scripts = [ "tartufi.py" ];
  };

  util_nix_doc_module = {
    pname = "util_nix_doc_module";
    version = "0.1.0";
    propagatedBuildInputs = [
    ];
    srcDir = "productivity/nix-specific/util-nix-doc-module";
    libs = [];
    scripts = [ "util_nix_doc_module.py" ];
  };

  tiny_mcp_server_taskwarrior = {
    pname = "tiny_mcp_server_taskwarrior";
    version = "0.1.0";
    propagatedBuildInputs = [
      "mcp"
    ];
    srcDir = "productivity/ai/mcp-servers";
    libs = [];
    scripts = [ "taskwarrior.py" ];
  };
}
