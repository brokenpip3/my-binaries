{
  util_pass_bitwarden = {
    pname = "util_pass_bitwarden";
    version = "0.3.0";
    propagatedBuildInputs = [
      "bitwarden-cli"
    ];
    srcDir = "security/pass-bitwarden-sync";
    libs = [ ];
    scripts = [ "util_pass_bitwarden.py" ];
  };

  util_privacy_telegram_cleanup = {
    pname = "util_privacy_telegram_cleanup";
    version = "0.3.0";
    propagatedBuildInputs = [
      "telethon"
    ];
    srcDir = "privacy/telegram-cleanup";
    libs = [ ];
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

  util_task_open = {
    pname = "util_task_open";
    version = "0.1.0";
    propagatedBuildInputs = [
      "fzf"
    ];
    srcDir = "productivity/task-open";
    libs = [ ];
    scripts = [
      "util_task_open.py"
    ];
  };

  tartufi = {
    pname = "tartufi";
    version = "0.1.0";
    propagatedBuildInputs = [
      "requests"
    ];
    libs = [ ];
    srcDir = "security/tartufi";
    scripts = [ "tartufi.py" ];
  };

  util_nix_doc_module = {
    pname = "util_nix_doc_module";
    version = "0.1.0";
    propagatedBuildInputs = [ ];
    srcDir = "productivity/nix-specific/util-nix-doc-module";
    libs = [ ];
    scripts = [ "util_nix_doc_module.py" ];
  };

  util_ci_changedfiles = {
    pname = "util_ci_changedfiles";
    version = "0.0.1";
    propagatedBuildInputs = [
      "gitpython"
    ];
    srcDir = "ci/changed-files";
    libs = [ ];
    scripts = [ "util_ci_changedfiles.py" ];
  };

  util_ai_mcp_taskwarrior = {
    pname = "util_ai_mcp_taskwarrior";
    version = "0.1.3";
    propagatedBuildInputs = [
      "mcp"
      "pytest"
    ];
    srcDir = "productivity/ai/mcp-servers/taskwarrior";
    libs = [ ];
    scripts = [ "mcp_server_taskwarrior.py" ];
    useUnstable = true;
    docker = true;
  };

  util_ai_mcp_googlecalendar = {
    pname = "util_ai_mcp_googlecalendar";
    version = "0.1.3";
    propagatedBuildInputs = [
      "mcp"
      "pytest"
      "google-api-python-client"
      "google-auth"
    ];
    srcDir = "productivity/ai/mcp-servers/google-calendar";
    libs = [ ];
    scripts = [ "mcp_server_google_calendar.py" ];
    useUnstable = true;
    docker = true;
  };

  util_ai_mcp_github = {
    pname = "util_ai_mcp_github";
    version = "0.1.1";
    propagatedBuildInputs = [
      "mcp"
      "httpx"
      "pytest"
    ];
    srcDir = "productivity/ai/mcp-servers/github";
    libs = [ ];
    scripts = [ "mcp_server_github.py" ];
    useUnstable = true;
    docker = true;
  };
}
