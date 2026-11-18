# Export a workspace to CSV

Use `tool export` to write a workspace's data to CSV files you can open in a spreadsheet. This page is for anyone with access to the workspace. At the end you will have one CSV file per table.

## Before you start

- An API token. Create one under **Settings**, **Security**, **API tokens**.
- The command-line tool, logged in: run `tool login` and paste the token.

## Export the workspace

1. Run the export, naming the workspace.

   ```bash
   tool export my-workspace
   ```

   The tool prints one line per table and writes the files to the current directory.

2. If the workspace is large, add `--compress` to write `.csv.gz` files.
3. If the export stops partway, run the same command with `--resume`. It continues from the last finished table.

## Confirm it worked

The last line reads `Export complete: N tables`. The output directory holds one file per table.

## Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--output PATH` | current directory | where to write the files |
| `--from DATE`, `--to DATE` | all dates | export only rows in the range |
| `--compress` | off | write gzip-compressed files |
| `--resume` | off | continue an interrupted export |

## Related

- [Export file format reference](https://example.com/docs/export-format): the columns in each CSV file.

![Terminal output of a finished export, ending with the line "Export complete: 14 tables"](export-screenshot.png)
