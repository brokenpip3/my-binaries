# Task Sync Library

This is my personal, ugly yet functional "task sync" library.

While I respect the [bugwarrior](https://github.com/GothenburgBitFactory/bugwarrior) philosophy I want something different, a flow that will not only pull tasks from different sources but also keep them in sync.

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
- ENV variables (check `_logseq.py`):
- The following uda fields in taskwarrior:
```bash
logseq_id      string Logseq ID
logseq_page    string Logseq Page
logseq_uuid    string Logseq UUID
```
which can be added with the following config in taskrc:
```
uda.logseq_id.type=string
uda.logseq_uuid.type=string
uda.logseq_page.type=string
uda.logseq_id.label=Logseq ID
uda.logseq_uuid.label=Logseq UUID
uda.logseq_page.label=Logseq Page
```

### YouTrack

Features:

- Pull tasks from YouTrack api and register the issue id in taskwarrior, avoiding duplicates
- On modify hook to update a task in YouTrack while modifying a task in taskwarrior

Properties supported (both ways):

- Status (done, todo, doing)
- Card ID (Read only)
- Description
- Card raw id and state id (Read only, necessary for card updates)

Pre-requisites:

- A youtrack token
- ENV variables (check `youtrack.py`)
```
TASKSYNC_YOUTRACK_URL
TASKSYNC_YOUTRACK_TOKEN
TASKSYNC_YOUTRACK_INPROGRESS_STATES #Optional
TASKSYNC_YOUTRACK_DONE_STATES       #Optional
```
- The following uda fields in taskwarrior:
```bash
youtrack       string YouTrack ID
youtrack_rawid string YouTrack Raw ID
```
which can be added with the following config in taskrc:
```
uda.youtrack.type=string
uda.youtrack.label=YouTrack ID
uda.youtrack_rawid.type=string
uda.youtrack_rawid.label=YouTrack Raw ID
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
