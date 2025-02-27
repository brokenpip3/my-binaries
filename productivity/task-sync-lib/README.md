# Task Sync Library

This is my personal, ugly yet functional task sync library.

While I respect the bugwarrior philosophy I want to have something that will pull but also keep in sync other systems with taskwarrior.

## Integrations

### Logseq

Features:

- Pull tasks from Logseq api and register the page, uid in taskwarrior, avoiding duplicates
- On add hook to create a task in Logseq while adding a task in taskwarrior
- On modify hook to update a task in Logseq while modifying a task in taskwarrior

Properties supported (both ways):

- Projects (with an hardcoded opinionatec `[[projects/xxx/yyy/zzz]]` format)
- Schedule and due dates
- Status (done, todo, doing)
- Tags
- Description
- Priority

Pre-requisites:

- Logseq API enabled and token created
- ENV variables (check `util_task_youtrack_sync.py`)
- The following uda fields in taskwarrior:
```bash
logseq_id      string Logseq ID
logseq_page    string Logseq Page
logseq_uuid    string Logseq UUID
```

### YouTrack

Features:

- Pull tasks from YouTrack api and register the issue id in taskwarrior, avoiding duplicates
- On modify hook to update a task in YouTrack while modifying a task in taskwarrior

Properties supported (both ways):

- Status (done, todo, doing)
- Card ID (Read only)
- Description
- Card raw id and state id (Read only, neeeed for updates)

Pre-requisites:

- A youtrack token
- ENV variables (check `youtrack.py`)
- The following uda fields in taskwarrior:
```bash
youtrack       string YouTrack ID
youtrack_rawid string YouTrack Raw ID
```

## home-manager integration

In order to allow these scripts to run we need to put them in the taskwarrior hooks directory.

Let's say you added this repo as `bin` and you task hooks directory is `~/.config/task/hooks`.

```nix
    # or xdg.configFile
    home.file.".config/task/hooks/on-add-logseq.py" = {
      source = "${bin.task-sync-lib}/bin/on-add-logseq.py";
    };
    home.file.".config/task/hooks/on-modify-logseq.py" = {
      source = "${bin.task-sync-lib}/bin/on-modify-logseq.py";
    };
    home.file.".config/task/hooks/on-modify-youtrack.py" = {
      source = "${bin.task-sync-lib}/bin/on-modify-youtrack.py";
    };
```
