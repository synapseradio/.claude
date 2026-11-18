# Overview

## Introduction

#### Background:

The export feature was introduced because customers asked for a way to get their data out of the system and into spreadsheets, and after several rounds of discussion it was decided that CSV would be the first supported format, with the option to add others later, and so the export command was added to the command-line tool, which you can run from any directory as long as you have logged in first using the login command, which requires an API token that you can get from the settings page under the security tab, and once you have done that you should run the export command with the name of the workspace you want to export and optionally a date range, and the output will be written to the current directory unless you pass the output flag, in which case it will be written to the path you specify, and you should be aware that exports of large workspaces can produce very large files so you may want to pass the compress flag as well, and note that if the export fails partway through you can resume it with the resume flag rather than starting again from the beginning which would waste a lot of effort for large workspaces.

For more information click [here](https://example.com/docs/export) or see ![](export-screenshot.png).

## Introduction

```
tool export my-workspace --output ./out --compress
```

1. Flags
   - Output
     - Path
     - Format
