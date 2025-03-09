{
  util_pass_bitwarden = {
    pname = "util_pass_bitwarden";
    version = "0.3.0";
    propagatedBuildInputs = [
      "python3"
      "bitwarden-cli"
    ];
    srcDir = "security/pass-bitwarden-sync";
    libs = [];
    scripts = [ "util_privacy_telegram_cleanup.py" ];
  };

  util_privacy_telegram_cleanup = {
    pname = "util_privacy_telegram_cleanup";
    version = "0.3.0";
    propagatedBuildInputs = [
      "python3"
      "telethon"
    ];
    srcDir = "privacy/telegram-cleanup";
    libs = [];
    scripts = [ "telegram_cleanup.py" ];
  };

  task-sync-lib = {
    pname = "task-sync-lib";
    version = "0.3.1";
    propagatedBuildInputs = [
      "python3"
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
      "python3"
      "requests"
    ];
    srcDir = "security/tartufi";
    libs = [];
    scripts = [ "tartufi.py" ];
  };
}
